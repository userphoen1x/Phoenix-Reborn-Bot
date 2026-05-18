import os
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.database import unlink_user_tag, get_user_data, set_user_role, ROLE_SYMBOLS

router = Router()

@router.message(Command("unlink"))
async def cmd_unlink_tag(message: Message, bot: Bot):
    founder_id = os.getenv("FOUNDER_ID")
    if not founder_id or message.from_user.id != int(founder_id):
        return

    parts = message.text.split()
    target_name = None

    if len(parts) > 1 and parts[1].startswith("@"):
        target_name = parts[1]
    elif message.reply_to_message:
        u = message.reply_to_message.from_user
        target_name = f"@{u.username}" if u.username else u.full_name

    if not target_name:
        await message.answer("Укажите @username или ответьте на сообщение пользователя.")
        return

    success = await unlink_user_tag(target_name)
    if success:
        await message.answer(f"Тег успешно отвязан от {target_name}. Аккаунт удален из базы бота.")
    else:
        await message.answer(f"Пользователь {target_name} не найден в базе.")

@router.callback_query(F.data.startswith("role_approve:"))
async def approve_role(callback: CallbackQuery, bot: Bot):
    founder_id = os.getenv("FOUNDER_ID")
    if not founder_id or callback.from_user.id != int(founder_id):
        await callback.answer("Нет прав", show_alert=True)
        return

    _, uid_str, role_eng = callback.data.split(":")
    user_id = int(uid_str)

    role_map = {"president": "Президент", "vicePresident": "Вице-президент"}
    role_ru = role_map.get(role_eng, "Участник")

    user_data = await get_user_data(user_id)
    if not user_data:
        await callback.message.edit_text("Ошибка: Пользователь больше не найден в базе.")
        return

    game_name = user_data[0]

    try:
        target_chat = os.getenv("TARGET_CHAT_ID")
        await bot.promote_chat_member(
            chat_id=target_chat,
            user_id=user_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True
        )
        custom_title = f"{ROLE_SYMBOLS.get(role_ru, '○')} {game_name}"
        await bot.set_chat_administrator_custom_title(
            chat_id=target_chat,
            user_id=user_id,
            custom_title=custom_title[:16]
        )

        await set_user_role(user_id, role_ru, "Одобрен")
        await callback.message.edit_text(f"Права {role_ru} успешно выданы пользователю (ID: {user_id}).")

    except Exception as e:
        await callback.message.edit_text(f"Ошибка выдачи прав Telegram: {e}")

@router.callback_query(F.data.startswith("role_reject:"))
async def reject_role(callback: CallbackQuery):
    founder_id = os.getenv("FOUNDER_ID")
    if not founder_id or callback.from_user.id != int(founder_id):
        await callback.answer("Нет прав", show_alert=True)
        return

    _, uid_str = callback.data.split(":")
    user_id = int(uid_str)

    await set_user_role(user_id, "Участник", "Отклонен")
    await callback.message.edit_text(f"Запрос на выдачу прав (ID: {user_id}) отклонен.")

@router.message(Command("force_roles"))
async def cmd_force_roles(message: Message, bot: Bot):
    founder_id = os.getenv("FOUNDER_ID")
    if not founder_id or message.from_user.id != int(founder_id):
        return
    await message.answer("Запускаю ручную проверку ролей. Ждите...")
    from utils.scheduler import check_roles
    await check_roles(bot)
    await message.answer("Проверка завершена.")