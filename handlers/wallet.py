from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

import database as db
from config import WALLET_ADDRESSES

router = Router()


def build_crypto_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="BTC", callback_data="topup:BTC"),
            InlineKeyboardButton(text="ETH", callback_data="topup:ETH"),
            InlineKeyboardButton(text="USDT", callback_data="topup:USDT"),
        ]
    ])


@router.message(Command("topup"))
async def cmd_topup(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("You need to /start first to create an account.")
        return

    await message.answer(
        "Choose the cryptocurrency you want to deposit:",
        reply_markup=build_crypto_choice_keyboard(),
    )


@router.callback_query(F.data.startswith("topup:"))
async def on_crypto_choice(callback: CallbackQuery):
    crypto = callback.data.split(":")[1]
    address = WALLET_ADDRESSES.get(crypto)

    if not address:
        await callback.answer("Invalid selection.", show_alert=True)
        return

    network_info = {
        "BTC": "Bitcoin network",
        "ETH": "Ethereum network (ERC-20)",
        "USDT": "Ethereum network (ERC-20)",
    }

    await callback.message.edit_text(
        f"Send your {crypto} to the following address:\n\n"
        f"<code>{address}</code>\n\n"
        f"Network: {network_info.get(crypto, 'N/A')}\n\n"
        "After sending, use /confirm to notify us of your deposit.\n"
        "An admin will verify and credit your balance."
    )
    await callback.answer()


@router.message(Command("confirm"))
async def cmd_confirm(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("You need to /start first to create an account.")
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(
            "How much did you deposit?\n\n"
            "Use: /confirm amount\n"
            "Example: /confirm 100"
        )
        return

    try:
        amount = float(parts[1])
    except ValueError:
        await message.answer("Invalid amount. Example: /confirm 100")
        return

    if amount <= 0:
        await message.answer("Amount must be positive.")
        return

    await message.answer(
        "Which crypto did you deposit?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="BTC", callback_data=f"confirm:BTC:{amount}"),
                InlineKeyboardButton(text="ETH", callback_data=f"confirm:ETH:{amount}"),
                InlineKeyboardButton(text="USDT", callback_data=f"confirm:USDT:{amount}"),
            ]
        ]),
    )


@router.callback_query(F.data.startswith("confirm:"))
async def on_confirm_crypto(callback: CallbackQuery):
    _, crypto, amount_text = callback.data.split(":")
    amount = float(amount_text)

    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Account not found.", show_alert=True)
        return

    deposit_id = await db.create_deposit(user["id"], crypto, amount)

    await callback.message.edit_text(
        f"Deposit #{deposit_id} created!\n\n"
        f"Crypto: {crypto}\n"
        f"Amount reported: ${amount:.2f}\n"
        f"Status: Pending\n\n"
        "An admin will review and approve your deposit shortly. "
        "You will receive a notification once it is confirmed."
    )
    await callback.answer()
