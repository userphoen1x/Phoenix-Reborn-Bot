from datetime import datetime, timedelta
from aiogram.types import Message
from core.globals import global_scheduler

async def _delete_msg(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass

def schedule_delete(message: Message, delay: int = 10800):
    if delay <= 0:
        return
    run_date = datetime.now() + timedelta(seconds=delay)
    global_scheduler.add_job(
        _delete_msg,
        'date',
        run_date=run_date,
        args=[message.bot, message.chat.id, message.message_id]
    )