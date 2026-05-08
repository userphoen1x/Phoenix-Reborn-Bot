import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Импорт роутера из папки handlers
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

    # Подключаем роутер
    dp.include_router(reg_router)

    logging.info("🚀 Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Остановлено")