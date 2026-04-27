import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

import database as db
from config import CRYPTO_LIST, STOCK_LIST
from services.signals_service import (
    fetch_crypto_data,
    fetch_stock_data,
    generate_signal,
    format_signal_message,
)

router = Router()


def build_asset_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Crypto", callback_data="signal_type:crypto"),
            InlineKeyboardButton(text="Stocks", callback_data="signal_type:stock"),
        ]
    ])


def build_crypto_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for symbol in CRYPTO_LIST:
        row.append(InlineKeyboardButton(text=symbol, callback_data=f"signal_crypto:{symbol}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Back", callback_data="signal_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_stock_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for symbol in STOCK_LIST:
        row.append(InlineKeyboardButton(text=symbol, callback_data=f"signal_stock:{symbol}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Back", callback_data="signal_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("signals"))
async def cmd_signals(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("You need to /start first to create an account.")
        return

    await message.answer(
        "What kind of trading signal are you looking for?",
        reply_markup=build_asset_type_keyboard(),
    )


@router.callback_query(F.data == "signal_type:crypto")
async def on_crypto_selected(callback: CallbackQuery):
    await callback.message.edit_text(
        "Select a cryptocurrency:",
        reply_markup=build_crypto_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "signal_type:stock")
async def on_stock_selected(callback: CallbackQuery):
    await callback.message.edit_text(
        "Select a stock:",
        reply_markup=build_stock_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "signal_back")
async def on_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "What kind of trading signal are you looking for?",
        reply_markup=build_asset_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("signal_crypto:"))
async def on_crypto_asset(callback: CallbackQuery):
    symbol = callback.data.split(":")[1]
    coin_id = CRYPTO_LIST.get(symbol)
    if not coin_id:
        await callback.answer("Unknown crypto.", show_alert=True)
        return

    await callback.message.edit_text(f"Fetching {symbol} data...")
    await callback.answer()

    data = await fetch_crypto_data(coin_id)
    if not data:
        await callback.message.edit_text(
            f"Could not fetch data for {symbol}. Try again later.",
            reply_markup=build_crypto_keyboard(),
        )
        return

    signal = generate_signal(data)
    text = format_signal_message(data, signal, "crypto")

    user = await db.get_user(callback.from_user.id)
    if user:
        await db.save_signal(user["id"], "crypto", symbol, signal["signal"])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Refresh", callback_data=f"signal_crypto:{symbol}")],
        [InlineKeyboardButton(text="Back to Crypto", callback_data="signal_type:crypto")],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("signal_stock:"))
async def on_stock_asset(callback: CallbackQuery):
    symbol = callback.data.split(":")[1]
    if symbol not in STOCK_LIST:
        await callback.answer("Unknown stock.", show_alert=True)
        return

    await callback.message.edit_text(f"Fetching {symbol} data...")
    await callback.answer()

    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, fetch_stock_data, symbol)
    if not data:
        await callback.message.edit_text(
            f"Could not fetch data for {symbol}. Try again later.",
            reply_markup=build_stock_keyboard(),
        )
        return

    signal = generate_signal(data)
    text = format_signal_message(data, signal, "stock")

    user = await db.get_user(callback.from_user.id)
    if user:
        await db.save_signal(user["id"], "stock", symbol, signal["signal"])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Refresh", callback_data=f"signal_stock:{symbol}")],
        [InlineKeyboardButton(text="Back to Stocks", callback_data="signal_type:stock")],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)
