import os
import asyncio
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message
from database.repositories.user_repo import UserRepository
from external.brawl_api import BrawlAPIClient
from core.config import settings

router = Router()


def is_superadmin(user_id: int) -> bool:
    return str(user_id) in [settings.FOUNDER_ID, settings.ADMIN_ID]


@router.message(Command("unlink"))
async def cmd_unlink_tag(message: Message, bot: Bot, user_repo: UserRepository):
    if not is_superadmin(message.from_user.id): return
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

    res = await user_repo.unlink_user_tag(target_name)
    if res:
        await message.answer(f"✅ Тег успешно отвязан от профиля {target_name}, пользователь переведен в Гости.")
    else:
        await message.answer(f"❌ Пользователь {target_name} не найден в базе.")


@router.message(Command("set_key"))
async def cmd_set_key(message: Message, brawl_client: BrawlAPIClient):
    if not is_superadmin(message.from_user.id): return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Укажите новый ключ. Пример:\n<code>/set_key eyJhbGciOi...</code>", parse_mode="HTML")
        return

    new_key = parts[1].strip()

    settings.BS_API_KEY = new_key

    wait_msg = await message.answer("⏳ Проверяю новый ключ и IP-адрес...")

    is_valid, status_msg = await brawl_client.check_api_connection()

    if is_valid:
        await wait_msg.edit_text(
            "✅ <b>API ключ успешно обновлен!</b>\nСвязь с серверами Brawl Stars установлена (200 OK).",
            parse_mode="HTML"
        )
    else:
        await wait_msg.edit_text(
            f"⚠️ <b>Ключ сохранен, но API недоступно!</b>\nВозможно, вы не добавили новый IP в белый список Supercell.\nОшибка: <code>{status_msg}</code>",
            parse_mode="HTML"
        )
    from aiogram.types import FSInputFile

    @router.message(Command("ping"))
    async def admin_ping(message: Message, brawl_client: BrawlAPIClient):
        if not is_superadmin(message.from_user.id): return
        wait_msg = await message.answer("⏳ Проверяю связь с серверами Supercell...")
        ok, text = await brawl_client.check_api_connection()
        await wait_msg.edit_text(f"Статус API:\n{text}")

    @router.message(Command("get_db"))
    async def admin_get_db(message: Message):
        if not is_superadmin(message.from_user.id): return
        if os.path.exists(settings.DB_PATH):
            await message.answer_document(document=FSInputFile(settings.DB_PATH), caption="🗄 База данных")
        else:
            await message.answer("❌ Файл не найден")

    @router.message(Command("force_roles"))
    async def cmd_force_roles(message: Message, bot: Bot):
        if not is_superadmin(message.from_user.id): return
        await message.answer("Запускаю ручную проверку ролей. Ждите...")
        from scheduler.jobs import check_roles
        await check_roles(bot)
        await message.answer("✅ Проверка завершена.")

    try:
        await message.delete()
    except Exception:
        pass