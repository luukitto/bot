from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

import database as db

router = Router()


class Registration(StatesGroup):
    full_name = State()
    email = State()
    phone = State()
    country = State()


def is_profile_complete(user: dict | None) -> bool:
    if not user:
        return False
    return bool(
        user.get("full_name")
        and user.get("email")
        and user.get("phone")
        and user.get("country")
    )


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Share phone number", request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def welcome_text(first_name: str, balance: float) -> str:
    return (
        f"Welcome back, {first_name}!\n\n"
        f"Your balance: ${balance:.2f}\n\n"
        "Use /signals to get trading signals\n"
        "Use /topup to add funds\n"
        "Use /balance to check your balance\n"
        "Use /web to login to the website"
    )


async def get_or_create_user(message: Message) -> dict:
    user = await db.get_user(message.from_user.id)
    if user:
        return user

    return await db.create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )


async def ask_next_missing_field(message: Message, user: dict):
    if not user.get("full_name"):
        await message.answer(
            "Please enter your full name (first name and last name).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if not user.get("email"):
        await message.answer("Thank you. What is your email address?")
        return

    if not user.get("phone"):
        await message.answer(
            "Please share your phone number using the button below.",
            reply_markup=phone_keyboard(),
        )
        return

    if not user.get("country"):
        await message.answer(
            "Great. What country are you from?",
            reply_markup=ReplyKeyboardRemove(),
        )


async def start_registration(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Registration.full_name)
    await message.answer(
        "Welcome! Before we create your trading account, please complete registration.\n\n"
        "Please enter your full name (first name and last name).",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)

    if user and is_profile_complete(user):
        await message.answer(
            welcome_text(message.from_user.first_name, user["balance"]),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if not user:
        user = await get_or_create_user(message)

    await start_registration(message, state)


@router.message(F.text.casefold() == "start")
async def text_start(message: Message, state: FSMContext):
    await cmd_start(message, state)


@router.message(Registration.full_name, F.text)
async def registration_full_name(message: Message, state: FSMContext):
    full_name = " ".join(message.text.split())
    if len(full_name) < 3 or len(full_name.split()) < 2:
        await message.answer("Please enter your full name, for example: John Smith")
        return

    user = await get_or_create_user(message)
    await db.update_user_crm_fields(user["id"], {"full_name": full_name})
    await state.update_data(full_name=full_name)
    await state.set_state(Registration.email)
    await message.answer("Thank you. What is your email address?")


@router.message(Registration.email, F.text)
async def registration_email(message: Message, state: FSMContext):
    email = message.text.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        await message.answer("Please enter a valid email address.")
        return

    user = await get_or_create_user(message)
    await db.update_user_crm_fields(user["id"], {"email": email})
    await state.update_data(email=email)
    await state.set_state(Registration.phone)
    await message.answer(
        "Please share your phone number using the button below.",
        reply_markup=phone_keyboard(),
    )


@router.message(Registration.phone, F.contact)
async def registration_phone_contact(message: Message, state: FSMContext):
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer("Please share your own phone number.")
        return

    user = await get_or_create_user(message)
    await db.update_user_crm_fields(user["id"], {"phone": message.contact.phone_number})
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(Registration.country)
    await message.answer(
        "Great. What country are you from?",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Registration.phone, F.text)
async def registration_phone_text(message: Message):
    await message.answer(
        "Please use the button to share your phone number.",
        reply_markup=phone_keyboard(),
    )


@router.message(Registration.country, F.text)
async def registration_country(message: Message, state: FSMContext):
    country = message.text.strip()
    if len(country) < 2:
        await message.answer("Please enter your country.")
        return

    user = await get_or_create_user(message)

    await db.update_user_crm_fields(
        user["id"],
        {
            "country": country,
            "status": "active",
        },
    )
    await db.log_user_activity(user["id"], "bot", "registration_completed")
    await state.clear()

    updated_user = await db.get_user(message.from_user.id)
    await message.answer(
        "Registration completed. Your account is ready.\n\n"
        "Here is what you can do:\n"
        "/signals - Get trading signals (crypto & stocks)\n"
        "/topup - Top up your balance\n"
        "/balance - Check your balance\n"
        "/web - Login to the website",
        reply_markup=ReplyKeyboardRemove(),
    )

    if updated_user:
        await message.answer(welcome_text(message.from_user.first_name, updated_user["balance"]))


@router.message(F.contact)
async def continue_incomplete_registration_contact(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user or is_profile_complete(user) or user.get("phone"):
        raise SkipHandler()

    await registration_phone_contact(message, state)


@router.message(F.text & ~F.text.startswith("/"))
async def continue_incomplete_registration(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user or is_profile_complete(user):
        raise SkipHandler()

    current_state = await state.get_state()
    if current_state:
        raise SkipHandler()

    if not user.get("full_name"):
        await registration_full_name(message, state)
        return

    if not user.get("email"):
        await registration_email(message, state)
        return

    if not user.get("phone"):
        await registration_phone_text(message)
        return

    if not user.get("country"):
        await registration_country(message, state)
        return

    await ask_next_missing_field(message, user)


@router.message(Command("web"))
async def cmd_web_login(message: Message):
    user = await db.get_user(message.from_user.id)

    if not user:
        await message.answer("You need to /start first to create an account.")
        return

    if not is_profile_complete(user):
        await message.answer("Please complete registration first by sending /start.")
        return

    code = await db.create_telegram_link_code(user["id"])
    await message.answer(
        "Use this one-time website login code:\n\n"
        f"<code>{code}</code>\n\n"
        "It expires in 10 minutes. Open the website login page and paste this code."
    )


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
