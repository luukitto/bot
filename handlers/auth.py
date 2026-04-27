from aiogram import F, Router
from aiogram.types import Message
from aiogram.filters import Command

import database as db

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    user = await db.get_user(message.from_user.id)

    if user:
        await message.answer(
            f"Welcome back, {message.from_user.first_name}!\n\n"
            f"Your balance: ${user['balance']:.2f}\n\n"
            "Use /signals to get trading signals\n"
            "Use /topup to add funds\n"
            "Use /balance to check your balance"
        )
    else:
        await db.create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )
        await message.answer(
            f"Welcome, {message.from_user.first_name}! "
            "Your account has been created.\n\n"
            "Here\'s what you can do:\n"
            "/signals - Get trading signals (crypto & stocks)\n"
            "/topup - Top up your balance\n"
            "/balance - Check your balance\n\n"
            "Let\'s get started!"
        )


@router.message(F.text.casefold() == "start")
async def text_start(message: Message):
    await cmd_start(message)


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    user = await db.get_user(message.from_user.id)

    if not user:
        await message.answer("You need to /start first to create an account.")
        return

    deposits = await db.get_user_deposits(message.from_user.id, limit=5)

    text = f"Your balance: ${user['balance']:.2f}\n"

    if deposits:
        text += "\nRecent deposits:\n"
        for d in deposits:
            status_icon = {"pending": "\u23f3", "confirmed": "\u2705", "rejected": "\u274c"}.get(
                d["status"], "\u2753"
            )
            amount_str = f"${d['amount']:.2f}" if d["amount"] else "pending"
            text += f"  {status_icon} #{d['id']} | {d['crypto']} | {amount_str} | {d['status']}\n"
    else:
        text += "\nNo deposits yet. Use /topup to add funds."

    await message.answer(text)
