from aiogram import Router, F, Bot
from aiogram.types import Message
from database.repositories.user_repo import UserRepository
from core.garbage_collector import schedule_delete

router = Router()


@router.message(F.new_chat_members)
async def on_user_join_message(message: Message, bot: Bot, user_repo: UserRepository):
    for new_user in message.new_chat_members:
        if new_user.id == bot.id: continue

        is_reg = await user_repo.is_registered(new_user.id)
        if not is_reg:
            try:
                await bot.ban_chat_member(message.chat.id, new_user.id)
                await bot.unban_chat_member(message.chat.id, new_user.id)
                sent = await message.answer(
                    f"🚫 <b>ЗАЙЧИК КИКНУТ</b>\n\nПользователь <a href='tg://user?id={new_user.id}'>{new_user.full_name}</a> попытался войти без регистрации.\n\nПройдите регистрацию в личных сообщениях со мной!",
                    parse_mode="HTML")
                schedule_delete(sent, 30)
            except:
                pass
        else:
            sent = await message.answer(
                f"👋 Добро пожаловать, <a href='tg://user?id={new_user.id}'>{new_user.full_name}</a>!",
                parse_mode="HTML")
            schedule_delete(sent, 60)
    try:
        await message.delete()
    except:
        pass


@router.message(F.left_chat_member)
async def on_user_leave_message(message: Message):
    try:
        await message.delete()
    except:
        pass