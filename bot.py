import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import BOT_TOKEN, PORT, WEBHOOK_SECRET, WEBHOOK_URL
from database import init_db
from handlers import auth, signals, wallet, admin


async def healthcheck(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN is not set. Create a .env file with your bot token.")
        print("See .env.example for reference.")
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    await init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(auth.router)
    dp.include_router(signals.router)
    dp.include_router(wallet.router)
    dp.include_router(admin.router)

    @dp.message(F.text & ~F.text.startswith("/"))
    async def unknown_message(message: Message):
        logging.info(
            "Unhandled message from %s: %r",
            message.from_user.id if message.from_user else "unknown",
            message.text,
        )
        await message.answer("I received your message. Try /start or /balance.")

    if WEBHOOK_URL:
        webhook_path = "/webhook"
        webhook_url = f"{WEBHOOK_URL}{webhook_path}"

        app = web.Application()
        app.router.add_get("/", healthcheck)
        app.router.add_get("/health", healthcheck)

        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=WEBHOOK_SECRET or None,
        ).register(app, path=webhook_path)
        setup_application(app, dp, bot=bot)

        await bot.set_webhook(
            webhook_url,
            secret_token=WEBHOOK_SECRET or None,
            drop_pending_updates=True,
        )

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()

        logging.info("Bot webhook is running on port %s", PORT)
        await asyncio.Event().wait()
    else:
        logging.info("Bot polling is starting...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        print("Starting bot...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
