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
    chat_id = event.chat.id

    if not target_chat or str(chat_id) != str(target_chat):
        return

    admin_log = f"📝 <b>Лог входа:</b>\nЮзер: {user.full_name} (@{user.username}, ID: {user_id})\n"

    if event.invite_link:
        link_url = event.invite_link.invite_link
        link_creator = event.invite_link.creator

        if link_creator.id == bot.id:
            original_requester_id = await get_link_owner(link_url)

            if original_requester_id and original_requester_id != user_id:
                await event.chat.ban(user_id)
                await event.chat.unban(user_id)
                await bot.send_message(chat_id, "Пользователь хотел зайти зайчиком в группу. Я его удалил.")

                if admin_log_chat:
                    admin_log += f"⚠️ <b>ПОПЫТКА ЗАЙЦА!</b>\nИспользовал ссылку, которую запросил ID: {original_requester_id}\nСтатус: Удален."
                    await bot.send_message(admin_log_chat, admin_log)
                return

            user_data = await get_user_data(user_id)
            if user_data:
                name, club, _ = user_data
                welcome_msg = f"Приветствуем новенького в чате! Это <b>{name}</b> из клуба <b>{club}</b>."
                await bot.send_message(chat_id, welcome_msg)
                admin_log += f"✅ Зашел по своей ссылке.\nИгрок: {name}\nКлуб: {club}"
            else:
                await event.chat.ban(user_id)
                await event.chat.unban(user_id)
                await bot.send_message(chat_id,
                                       "Пользователь хотел зайти зайчиком в группу (нет в базе). Я его удалил.")
                admin_log += "❌ Нет в базе данных. Удален."

        else:
            admin_log += f"🛡 Зашел по ссылке админа (@{link_creator.username})"
    else:
        admin_log += "🛡 Добавлен админом напрямую."

    if admin_log_chat:
        await bot.send_message(admin_log_chat, admin_log)


@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_leave(event: ChatMemberUpdated, bot: Bot):
    admin_log_chat = os.getenv("ADMIN_ID")
    target_chat = os.getenv("TARGET_CHAT_ID")
    chat_id = event.chat.id

    if not target_chat or str(chat_id) != str(target_chat):
        return

    if admin_log_chat:
        user_id = event.old_chat_member.user.id
        user_data = await get_user_data(user_id)

        if user_data:
            name, club, _ = user_data
            leave_msg = f"Игрок <b>{name}</b> из клуба <b>{club}</b> вышел с чата"
        else:
            leave_msg = "Незарегестриванный в боте пользователь вышел из чата."

        await bot.send_message(admin_log_chat, f"🚪 <b>Выход из группы:</b>\n{leave_msg}")