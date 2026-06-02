import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.config import settings
from database.connection import init_db
from scheduler.setup import start_scheduler
from tg_bot.middlewares.db_middleware import ServicesMiddleware
from utils.admin_logger import send_log
from tg_bot.middlewares.antispam import AntiSpamMiddleware
from tg_bot.handlers import registration, group_events, group_commands, founder, profile, economy, casino, ai_chat, tops

async def main():
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(levelname)s - %(message)s",
        force=True
    )

    if not settings.BOT_TOKEN:
        logging.error("BOT_TOKEN не найден!")
        return

    await init_db()

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(ServicesMiddleware(db_path=settings.DB_PATH))
    dp.message.middleware(AntiSpamMiddleware())

    @dp.errors()
    async def global_error_handler(event, data):
        logging.error(f"Error: {event.exception}")
        await send_log(bot, "TOPIC_SESSION", f"🔥 <b>Критический сбой бота:</b>\n<code>{event.exception}</code>")
        return True

    start_scheduler(bot)

    dp.include_router(founder.router)
    dp.include_router(profile.router)
    dp.include_router(economy.router)
    dp.include_router(casino.router)
    dp.include_router(registration.router)
    dp.include_router(group_events.router)
    dp.include_router(group_commands.router)
    dp.include_router(tops.router)
    dp.include_router(ai_chat.router)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.ipify.org") as resp:
                if resp.status == 200:
                    ip = await resp.text()
                    logging.info(f"🌐 Текущий IP-адрес сервера: {ip}")
                    print(f"🌐 Текущий IP-адрес сервера: {ip}")
                else:
                    logging.warning(f"Не удалось получить IP, статус: {resp.status}")
    except Exception as e:
        logging.warning(f"Ошибка при получении IP: {e}")

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
