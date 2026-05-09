import asyncio
import logging
import os
import aiohttp  # <-- ДОБАВИЛИ ЭТУ СТРОКУ
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from handlers.private_reg import router as reg_router


async def main():
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.error("❌ BOT_TOKEN не найден!")
        return

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(reg_router)

    # --- ДОБАВИЛИ ЭТОТ БЛОК ДЛЯ ПОИСКА IP ---
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.ipify.org") as resp:
                ip = await resp.text()
                logging.info(f"🌍 МОЙ IP АДРЕС НА ХОСТИНГЕ: {ip}")
    except Exception as e:
        logging.error(f"Не удалось получить IP: {e}")
    # ----------------------------------------

    logging.info("🚀 Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Остановлено")