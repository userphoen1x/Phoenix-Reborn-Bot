import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from handlers.private_reg import router as reg_router
from handlers.group_events import router as group_router
from handlers.group_commands import router as group_cmds_router
from utils.database import init_db


async def main():
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    token = os.getenv("BOT_TOKEN")
    if not token:
        return

    await init_db()

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(reg_router)
    dp.include_router(group_router)
    dp.include_router(group_cmds_router)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.ipify.org") as resp:
                ip = await resp.text()
                logging.info(f"IP: {ip}")
    except Exception:
        pass

    logging.info("START")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass