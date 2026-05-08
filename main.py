import asyncio
from aiogram import Bot, Dispatcher
from handlers.private_reg import router as reg_router

async def main():
    bot = Bot(token="7776059491:AAG7l61ci67m4gryiTaE2Qbhg-nVUT36UOw")
    dp = Dispatcher()

    # Подключаем наш роутер с регистрацией
    dp.include_router(reg_router)

    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())