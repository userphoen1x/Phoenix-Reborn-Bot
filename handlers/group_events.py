import os
import asyncio
from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from utils.database import get_user_data, get_link_owner, get_eco_data
from utils.scheduler import check_roles

router = Router()


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated, bot: Bot):
    target_chat = os.getenv("TARGET_CHAT_ID")
    admin_log_chat = os.getenv("ADMIN_ID")
    user = event.new_chat_member.user
    user_id = user.id
    if not target_chat or str(event.chat.id) != str(target_chat): return

    u_name = f"@{user.username}" if user.username else user.full_name
    log = ""

    if event.invite_link:
        link_url = event.invite_link.invite_link
        creator = event.invite_link.creator
        if creator.id == bot.id:
            owner_id = await get_link_owner(link_url)
            if owner_id and owner_id != user_id:
                await event.chat.ban(user_id)
                await event.chat.unban(user_id)
                await bot.send_message(event.chat.id, f"{u_name} хотел зайти в группу зайчиком. Я его удалил.")

                owner_str = f"{owner_id}"
                owner_data = await get_user_data(owner_id)
                if owner_data:
                    owner_str += f" (Ник: {owner_data[0]})"
                log = f"Попытка входа по чужой ссылке от ID: {owner_str}. Нарушитель: {u_name} ({user_id})."
                if admin_log_chat: await bot.send_message(admin_log_chat, log)
                return

            data = await get_user_data(user_id)
            eco = await get_eco_data(user_id)
            if data and eco:
                tag = eco.get("bs_tag", "Неизвестно")
                await bot.send_message(event.chat.id, f"Привет, <b>{data[0]}</b> из <b>{data[1]}</b>!")
                log = f"Лог входа: {u_name} ({user_id}) зашел с тега игрока {tag} ({data[0]}). Убедитесь, что это он."
                asyncio.create_task(check_roles(bot))
            else:
                await event.chat.ban(user_id)
                await event.chat.unban(user_id)
                await bot.send_message(event.chat.id, "Заяц (нет в базе) удален.")
                log = f"Лог входа: {u_name} ({user_id}) попытался зайти без базы. Удален."
        else:
            c_name = f"@{creator.username}" if creator.username else creator.full_name
            data = await get_user_data(user_id)
            eco = await get_eco_data(user_id)
            if data and eco:
                tag = eco.get("bs_tag", "Неизвестно")
                log = f"Лог входа: {u_name} ({user_id}) зашел с тега игрока {tag} ({data[0]}) [создатель ссылки: {c_name}]."
                asyncio.create_task(check_roles(bot))
            else:
                log = f"Лог входа: {u_name} ({user_id}) зашел по ссылке {c_name}, но он не зарегистрирован."
    else:
        data = await get_user_data(user_id)
        eco = await get_eco_data(user_id)
        if data and eco:
            tag = eco.get("bs_tag", "Неизвестно")
            log = f"Лог входа: {u_name} ({user_id}) зашел с тега игрока {tag} ({data[0]}) [напрямую]."
            asyncio.create_task(check_roles(bot))
        else:
            log = f"Лог входа: {u_name} ({user_id}) зашел напрямую без регистрации."

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
        eco = await get_eco_data(user_id)
        u_name = f"@{user.username}" if user.username else user.full_name

        if data and eco:
            tag = eco.get("bs_tag", "Неизвестно")
            player_info = f"с тега игрока {tag} ({data[0]})"
        else:
            player_info = "без привязанного тега"

        if event.new_chat_member.status == "kicked":
            a_name = f"@{actor.username}" if actor.username else actor.full_name
            msg = f"Лог выхода: {u_name} ({user_id}) {player_info} был забанен/кикнут Админом {a_name}."
        else:
            msg = f"Лог выхода: {u_name} ({user_id}) {player_info} вышел из чата."

        await bot.send_message(admin_log_chat, msg)