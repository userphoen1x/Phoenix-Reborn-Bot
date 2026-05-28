import os
import logging
from aiogram import Bot

async def send_log(bot: Bot, topic_env_var: str, text: str):
    admin_chat = os.getenv("ADMIN_CHAT_ID")
    topic_id = os.getenv(topic_env_var)
    if not admin_chat or not topic_id:
        return
    try:
        await bot.send_message(
            chat_id=int(admin_chat),
            message_thread_id=int(topic_id),
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(e)