import os
from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from utils.database import is_user_approved

router = Router()


@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated, bot: Bot):
    target_chat = os.getenv("TARGET_CHAT_ID")
    user_id = event.new_chat_member.user.id
    chat_id = event.chat.id

    print(f"👀 СОБЫТИЕ: Пользователь {user_id} зашел в чат {chat_id}")

    if not target_chat or str(chat_id) != str(target_chat):
        return

    print(f"✅ Вход в целевую группу. Проверяем способ входа...")

    if event.invite_link:
        link_creator_id = event.invite_link.creator.id
        print(f"🔗 Вход по ссылке. Создатель ссылки: {link_creator_id}, ID бота: {bot.id}")

        if link_creator_id == bot.id:
            is_approved = await is_user_approved(user_id)

            if not is_approved:
                print(f"🚫 В БАЗЕ НЕТ! Кикаем мошенника {user_id}...")
                try:
                    await event.chat.ban(user_id)
                    await event.chat.unban(user_id)
                    print(f"💀 Мошенник {user_id} успешно выгнан!")
                except Exception as e:
                    print(f"❌ ОШИБКА КИКА: Не хватает прав? Текст ошибки: {e}")
            else:
                print(f"🤝 Свой зашел! ID: {user_id} есть в базе.")

        else:
            print(f"🛡️ Ссылку создал администратор (ID: {link_creator_id}). Пропускаем без проверок.")

    else:
        print(f"🛡️ Человека добавили напрямую или по публичному юзернейму. Пропускаем.")