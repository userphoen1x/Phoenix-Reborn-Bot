import os
import asyncio
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from database.repositories.user_repo import UserRepository
from external.brawl_api import BrawlAPIClient
from core.config import settings

router = Router()

def is_tech_admin(user_id: int) -> bool:
    return str(user_id) == settings.FOUNDER_ID or str(user_id) in settings.DEVELOPER_IDS

ROLE_SYMBOLS = {"Главарь": "👑", "Программист": "🧑🏻‍💻", "Президент": "🌟", "Вице-президент": "⭐", "Ветеран": "🎖", "Участник": "👤", "Гость": "🗣️"}

@router.message(Command("unlink"))
async def cmd_unlink_tag(message: Message, user_repo: UserRepository):
    if not is_tech_admin(message.from_user.id): return
    parts = message.text.split()
    target_name = None
    if len(parts) > 1 and parts[1].startswith("@"): target_name = parts[1]
    elif message.reply_to_message:
        u = message.reply_to_message.from_user
        target_name = f"@{u.username}" if u.username else u.full_name
    if not target_name:
        await message.answer("Укажите @username или ответьте на сообщение пользователя.")
        return
    res = await user_repo.unlink_user_tag(target_name)
    if res: await message.answer(f"✅ Тег успешно отвязан от профиля {target_name}, пользователь переведен в Гости.")
    else: await message.answer(f"❌ Пользователь {target_name} не найден в базе.")

@router.message(Command("set_key"))
async def cmd_set_key(message: Message, brawl_client: BrawlAPIClient):
    if not is_tech_admin(message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("❌ Укажите новый ключ. Пример:\n<code>/set_key eyJhbGciOi...</code>", parse_mode="HTML")
    new_key = parts[1].strip()
    settings.BS_API_KEY = new_key
    wait_msg = await message.answer("⏳ Проверяю новый ключ и IP-адрес...")
    is_valid, status_msg = await brawl_client.check_api_connection()
    if is_valid: await wait_msg.edit_text("✅ <b>API ключ успешно обновлен!</b>\nСвязь с серверами Brawl Stars установлена (200 OK).", parse_mode="HTML")
    else: await wait_msg.edit_text(f"⚠️ <b>Ключ сохранен, но API недоступно!</b>\nВозможно, вы не добавили новый IP в белый список Supercell.\nОшибка: <code>{status_msg}</code>", parse_mode="HTML")
    try: await message.delete()
    except: pass

@router.message(Command("ping"))
async def admin_ping(message: Message, brawl_client: BrawlAPIClient):
    if not is_tech_admin(message.from_user.id): return
    wait_msg = await message.answer("⏳ Проверяю связь с серверами Supercell...")
    ok, text = await brawl_client.check_api_connection()
    await wait_msg.edit_text(f"Статус API:\n{text}")

@router.message(Command("get_db"))
async def admin_get_db(message: Message):
    if not is_tech_admin(message.from_user.id): return
    if os.path.exists(settings.DB_PATH):
        await message.answer_document(document=FSInputFile(settings.DB_PATH), caption="🗄 База данных")
    else: await message.answer("❌ Файл не найден")

@router.message(Command("force_roles"))
async def cmd_force_roles(message: Message, bot: Bot):
    if not is_tech_admin(message.from_user.id): return
    await message.answer("Запускаю ручную проверку ролей. Ждите...")
    from scheduler.jobs import check_roles
    await check_roles(bot)
    await message.answer("✅ Проверка завершена.")

@router.callback_query(F.data.startswith("role_approve:"))
async def approve_role(callback: CallbackQuery, bot: Bot, user_repo: UserRepository):
    if str(callback.from_user.id) != settings.FOUNDER_ID: return await callback.answer("Нет прав", show_alert=True)
    _, uid_str, role_eng = callback.data.split(":")
    user_id = int(uid_str)
    role_ru = {"president": "Президент", "vicePresident": "Вице-президент"}.get(role_eng, "Участник")
    user_data = await user_repo.get_user_data(user_id)
    if not user_data: return await callback.message.edit_text("Ошибка: Пользователь больше не найден в базе.")
    game_name = user_data[0]
    try:
        if settings.TARGET_CHAT_ID:
            await bot.promote_chat_member(chat_id=settings.TARGET_CHAT_ID, user_id=user_id, can_manage_chat=True, can_delete_messages=True, can_restrict_members=True, can_invite_users=True)
            custom_title = f"{ROLE_SYMBOLS.get(role_ru, '○')} {game_name}"
            await bot.set_chat_administrator_custom_title(chat_id=settings.TARGET_CHAT_ID, user_id=user_id, custom_title=custom_title[:16])
        await user_repo.set_user_role(user_id, role_ru, "Одобрен")
        await callback.message.edit_text(f"Права {role_ru} успешно выданы пользователю (ID: {user_id}).")
    except Exception as e:
        await callback.message.edit_text(f"Ошибка выдачи прав Telegram: {e}")

@router.callback_query(F.data.startswith("role_reject:"))
async def reject_role(callback: CallbackQuery, user_repo: UserRepository):
    if str(callback.from_user.id) != settings.FOUNDER_ID: return await callback.answer("Нет прав", show_alert=True)
    _, uid_str = callback.data.split(":")
    user_id = int(uid_str)
    await user_repo.set_user_role(user_id, "Участник", "Отклонен")
    await callback.message.edit_text(f"Запрос на выдачу прав (ID: {user_id}) отклонен.")