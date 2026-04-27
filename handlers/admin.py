from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command

import database as db
from config import ADMIN_IDS

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_denied_text(user_id: int) -> str:
    return (
        "You don't have permission to use this command.\n\n"
        f"Your Telegram ID is: {user_id}\n"
        "Add this ID to ADMIN_IDS in your .env or Render environment variables."
    )


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(f"Your Telegram ID is: {message.from_user.id}")


@router.message(Command("users"))
async def cmd_users(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(admin_denied_text(message.from_user.id))
        return

    users = await db.list_users(limit=25)
    if not users:
        await message.answer("No users found yet.")
        return

    lines = ["Users:\n"]
    for user in users:
        username = user["username"] or "N/A"
        lines.append(
            f"#{user['id']} | @{username} | Telegram ID: {user['telegram_id']}\n"
            f"Balance: ${user['balance']:.2f} | Created: {user['created_at']}\n"
        )

    lines.append("\nAdd balance: /addbalance telegram_id amount")
    lines.append("Remove balance: /addbalance telegram_id -amount")
    await message.answer("\n".join(lines))


@router.message(Command("addbalance"))
async def cmd_add_balance(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(admin_denied_text(message.from_user.id))
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer(
            "Usage: /addbalance telegram_id amount\n"
            "Example: /addbalance 123456789 100"
        )
        return

    try:
        telegram_id = int(parts[1])
        amount = float(parts[2])
    except ValueError:
        await message.answer("Invalid Telegram ID or amount. Use numbers only.")
        return

    if amount == 0:
        await message.answer("Amount cannot be zero.")
        return

    user = await db.get_user(telegram_id)
    if not user:
        await message.answer(f"User with Telegram ID {telegram_id} not found.")
        return

    await db.update_balance(user["id"], amount)
    updated_user = await db.get_user(telegram_id)

    await message.answer(
        f"Balance updated for @{user['username'] or 'N/A'}.\n"
        f"Change: ${amount:.2f}\n"
        f"New balance: ${updated_user['balance']:.2f}"
    )


@router.message(Command("pending"))
async def cmd_pending(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(admin_denied_text(message.from_user.id))
        return

    deposits = await db.get_pending_deposits()

    if not deposits:
        await message.answer("No pending deposits.")
        return

    lines = ["Pending Deposits:\n"]
    for d in deposits:
        username = d["username"] or "N/A"
        amount = f"${d['amount']:.2f}" if d["amount"] else "not provided"
        lines.append(
            f"  #{d['id']} | @{username} (ID: {d['telegram_id']})\n"
            f"    Crypto: {d['crypto']} | Reported amount: {amount}\n"
            f"    Created: {d['created_at']}\n"
        )

    lines.append("\nTo approve: /approve deposit_id amount")
    lines.append("To reject:  /reject deposit_id")

    await message.answer("\n".join(lines))


@router.message(Command("approve"))
async def cmd_approve(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer(admin_denied_text(message.from_user.id))
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Usage: /approve deposit_id amount\nExample: /approve 5 100.00")
        return

    try:
        deposit_id = int(parts[1])
        amount = float(parts[2])
    except ValueError:
        await message.answer("Invalid deposit ID or amount. Use numbers only.")
        return

    if amount <= 0:
        await message.answer("Amount must be positive.")
        return

    deposit = await db.get_deposit(deposit_id)
    if not deposit:
        await message.answer(f"Deposit #{deposit_id} not found.")
        return

    if deposit["status"] != "pending":
        await message.answer(f"Deposit #{deposit_id} is already {deposit['status']}.")
        return

    await db.update_deposit_status(deposit_id, "confirmed", amount)
    await db.update_balance(deposit["user_id"], amount)

    await message.answer(
        f"Deposit #{deposit_id} approved!\n"
        f"Amount: ${amount:.2f}\n"
        f"User: @{deposit['username'] or 'N/A'}"
    )

    try:
        await bot.send_message(
            deposit["telegram_id"],
            f"Your deposit #{deposit_id} has been approved!\n"
            f"Amount credited: ${amount:.2f}\n"
            f"Use /balance to check your updated balance.",
        )
    except Exception:
        await message.answer("(Could not notify the user.)")


@router.message(Command("reject"))
async def cmd_reject(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer(admin_denied_text(message.from_user.id))
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /reject deposit_id\nExample: /reject 5")
        return

    try:
        deposit_id = int(parts[1])
    except ValueError:
        await message.answer("Invalid deposit ID.")
        return

    deposit = await db.get_deposit(deposit_id)
    if not deposit:
        await message.answer(f"Deposit #{deposit_id} not found.")
        return

    if deposit["status"] != "pending":
        await message.answer(f"Deposit #{deposit_id} is already {deposit['status']}.")
        return

    await db.update_deposit_status(deposit_id, "rejected")

    await message.answer(
        f"Deposit #{deposit_id} rejected.\n"
        f"User: @{deposit['username'] or 'N/A'}"
    )

    try:
        await bot.send_message(
            deposit["telegram_id"],
            f"Your deposit #{deposit_id} has been rejected.\n"
            "If you believe this is an error, please contact support.",
        )
    except Exception:
        await message.answer("(Could not notify the user.)")
