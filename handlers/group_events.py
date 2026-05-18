import os
import asyncio
from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from utils.database import get_user_data, get_link_owner
from utils.scheduler import check_roles

router = Router()


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated, bot: Bot):
    target_chat = os.getenv("TARGET_CHAT_ID")
    admin_log_chat = os.getenv("ADMIN_ID")
    user = event.new_chat_member.user
    user_id = user.id
    if not target_chat or str(event.chat.id) != str(target_chat): return

    u_name = f"@{user.username}" if user.username else "без_юз"
    log = f"Лог входа: Пользователь: {user.full_name} ({u_name}, ID: {user_id})\n"

    if event.invite_link:
        link_url = event.invite_link.invite_link
        creator = event.invite_link.creator
        if creator.id == bot.id:
            owner_id = await get_link_owner(link_url)
            if owner_id and owner_id != user_id:
                await event.chat.ban(user_id)
                await event.chat.unban(user_id)
                user_mention = f"@{user.username}" if user.username else user.full_name
                await bot.send_message(event.chat.id, f"{user_mention} хотел зайти в группу зайчиком. Я его удалил.")
                owner_str = f"{owner_id}"
                owner_data = await get_user_data(owner_id)
                if owner_data:
                    owner_str += f" ({owner_data[0]} из {owner_data[1]})"
                log += f"Попытка входа по чужой ссылке от ID: {owner_str}"
                if admin_log_chat: await bot.send_message(admin_log_chat, log)
                return
            data = await get_user_data(user_id)
            if data:
                await bot.send_message(event.chat.id, f"Привет, <b>{data[0]}</b> из <b>{data[1]}</b>!")
                log += f"Зашел по своей ссылке. Игрок: {data[0]} из {data[1]}"

                # Мгновенная проверка ролей для вошедшего
                asyncio.create_task(check_roles(bot))
            else:
                await event.chat.ban(user_id)
                await event.chat.unban(user_id)
                await bot.send_message(event.chat.id, "Заяц (нет в базе) удален.")
                log += "Нет в базе."
        else:
            c_name = f"@{creator.username}" if creator.username else creator.full_name
            log += f"зашел в группу по Админ-ссылке ({c_name})"
            data = await get_user_data(user_id)
            if data:
                asyncio.create_task(check_roles(bot))
    else:
        log += "Напрямую."
        data = await get_user_data(user_id)
        if data:
            asyncio.create_task(check_roles(bot))

    if admin_log_chat: await bot.send_message(admin_log_chat, log)


@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_leave(event: ChatMemberUpdated, bot: Bot):
    admin_log_chat = os.getenv("ADMIN_ID")
    target_chat = os.getenv("TARGET_CHAT_ID")
    if not target_chat or str(event.chat.id) != str(target_chat): return
    if admin_log_chat:
        user = event.old_chat_member.user
        user_id = user.id
        actor = event.from_user
        data = await get_user_data(user_id)
        u_name = f"@{user.username}" if user.username else "без_юз"
        user_str = f"Пользователь: {user.full_name} ({u_name}, ID: {user.id})"

        if event.new_chat_member.status == "kicked":
            a_name = f"@{actor.username}" if actor.username else actor.full_name
            if data:
                msg = f"Игрок <b>{data[0]}</b> из ({data[1]}) был забанен Админом {a_name}"
            else:
                msg = f"{user_str} был забанен Админом {a_name}. Данных о игровом аккаунте нет."
        else:
            if data:
                msg = f"Выход: Игрок <b>{data[0]}</b> из ({data[1]}) вышел"
            else:
                msg = f"{user_str} вышел. Данных о игровом аккаунте нет."
        await bot.send_message(admin_log_chat, msg)