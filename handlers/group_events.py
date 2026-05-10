import os
from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from utils.database import get_user_data, get_link_owner

router = Router()

@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated, bot: Bot):
    target_chat = os.getenv("TARGET_CHAT_ID")
    admin_log_chat = os.getenv("ADMIN_ID")
    user = event.new_chat_member.user
    user_id = user.id
    if not target_chat or str(event.chat.id) != str(target_chat): return
    log = f"Лог входа:\nЮзер: {user.full_name} (@{user.username}, ID: {user_id})\n"
    if event.invite_link:
        link_url = event.invite_link.invite_link
        creator = event.invite_link.creator
        if creator.id == bot.id:
            owner_id = await get_link_owner(link_url)
            if owner_id and owner_id != user_id:
                await event.chat.ban(user_id)
                await event.chat.unban(user_id)
                await bot.send_message(event.chat.id, "Заяц удален.")
                if admin_log_chat: await bot.send_message(admin_log_chat, log + f"Попытка входа по чужой ссылке от ID: {owner_id}")
                return
            data = await get_user_data(user_id)
            if data:
                await bot.send_message(event.chat.id, f"Привет, <b>{data[0]}</b> из <b>{data[1]}</b>!")
                log += f"Зашел сам. Игрок: {data[0]}"
            else:
                await event.chat.ban(user_id)
                await event.chat.unban(user_id)
                await bot.send_message(event.chat.id, "Заяц (нет в базе) удален.")
                log += "Нет в базе."
        else: log += f"Админ-ссылка (@{creator.username})"
    else: log += "Напрямую."
    if admin_log_chat: await bot.send_message(admin_log_chat, log)

@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_leave(event: ChatMemberUpdated, bot: Bot):
    admin_log_chat = os.getenv("ADMIN_ID")
    target_chat = os.getenv("TARGET_CHAT_ID")
    if not target_chat or str(event.chat.id) != str(target_chat): return
    if admin_log_chat:
        user_id = event.old_chat_member.user.id
        data = await get_user_data(user_id)
        msg = f"Игрок <b>{data[0]}</b> ({data[1]}) вышел" if data else "Неизвестный вышел"
        await bot.send_message(admin_log_chat, f"Выход:\n{msg}")