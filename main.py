import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.config import settings
from core.globals import global_scheduler
from database.connection import init_db
from scheduler.setup import start_scheduler
from tg_bot.middlewares.db_middleware import DBMiddleware
from utils.admin_logger import send_log
from tg_bot.middlewares.antispam import AntiSpamMiddleware
from tg_bot.handlers import setup_routers

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", force=True)

    if not settings.BOT_TOKEN:
        logging.error("BOT_TOKEN не найден!")
        return

    await init_db()

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DBMiddleware(db_path=settings.DB_PATH))
    dp.message.middleware(AntiSpamMiddleware())

    @dp.errors()
    async def global_error_handler(event, **kwargs):
        logging.error(f"Error: {event.exception}")
        try:
            await send_log(bot, "TOPIC_SESSION", f"🔥 <b>Критический сбой бота:</b>\n<code>{event.exception}</code>")
        except Exception:
            pass
        return True

    global_scheduler.start()
    start_scheduler(bot)

    setup_routers(dp)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.ipify.org") as resp:
                if resp.status == 200:
                    ip = await resp.text()
                    logging.info(f"🌐 Текущий IP-адрес сервера: {ip}")
                    print(f"🌐 Текущий IP-адрес сервера: {ip}")
    except Exception:
        pass

    logging.info("🚀 БОТ УСПЕШНО ЗАПУЩЕН")
    print("🚀 БОТ УСПЕШНО ЗАПУЩЕН")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Бот остановлен.")
        print("🛑 Бот остановлен.")