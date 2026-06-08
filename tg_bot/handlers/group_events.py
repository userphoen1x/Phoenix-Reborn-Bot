from aiogram import Router, F, Bot
from aiogram.types import Message
from dishka import inject
from dishka.integrations.aiogram import FromDishka

from database.repositories.user_repo import UserRepository
from core.garbage_collector import schedule_delete
from core.lexicon import LEXICON
from core.constants import DELAYS

router = Router()


@router.message(F.new_chat_members)
@inject
async def on_user_join_message(message: Message, bot: Bot, user_repo: FromDishka[UserRepository]):
    for new_user in message.new_chat_members:
        if new_user.id == bot.id: continue

        is_reg = await user_repo.is_registered(new_user.id)
        if not is_reg:
            try:
                await bot.ban_chat_member(message.chat.id, new_user.id)
                await bot.unban_chat_member(message.chat.id, new_user.id)
                sent = await message.answer(
                    LEXICON["event_kick_unreg"].format(user_id=new_user.id, name=new_user.full_name), parse_mode="HTML")
                schedule_delete(sent, DELAYS["short"])
            except:
                pass
        else:
            sent = await message.answer(LEXICON["event_welcome"].format(user_id=new_user.id, name=new_user.full_name),
                                        parse_mode="HTML")
            schedule_delete(sent, DELAYS["default"])
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