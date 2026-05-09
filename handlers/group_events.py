import os
from aiogram import Router, F
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from utils.database import is_user_approved

router = Router()


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated):
    target_chat = os.getenv("TARGET_CHAT_ID")

    # Реагируем только если событие произошло в нашей целевой закрытой группе
    if target_chat and str(event.chat.id) == str(target_chat):
        user_id = event.new_chat_member.user.id

        # Проверяем, есть ли человек в нашей базе данных
        is_approved = await is_user_approved(user_id)

        if not is_approved:
            # Если это чужак (мошенник), баним его и сразу разбаниваем (чтобы просто выгнать)
            await event.chat.ban(user_id)
            await event.chat.unban(user_id)
            print(f"🚫 Мошенник кикнут! ID: {user_id} пытался зайти по чужой ссылке.")
        else:
            print(f"✅ Свой зашел! ID: {user_id} успешно пропущен.")