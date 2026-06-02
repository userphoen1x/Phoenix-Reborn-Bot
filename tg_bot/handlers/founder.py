from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, LinkPreviewOptions
from database.repositories.user_repo import UserRepository
from core.config import settings


@router.message(Command("force_scan"), F.chat.type == "private")
async def admin_force_scan(message: Message):
    if str(message.from_user.id) not in settings.DEVELOPER_IDS and str(message.from_user.id) != settings.FOUNDER_ID: 
        return
    
    sent_msg = await message.answer("⏳ Собираю данные...")
    from scheduler.jobs import collect_daily_stats
    await collect_daily_stats()
    await sent_msg.edit_text("✅ Готово. Сбор данных завершен.")


@router.message(Command("all_reg_list"), F.chat.type == "private")
async def cmd_all_reg_list(message: Message, user_repo: UserRepository):
    a_role = await user_repo.get_user_role(message.from_user.id)
    is_founder = str(message.from_user.id) == settings.FOUNDER_ID
    is_dev = str(message.from_user.id) in settings.DEVELOPER_IDS
    
    if not is_founder and not is_dev and a_role not in ["Президент", "Вице-президент"]: 
        return

    users = await user_repo.get_all_registered_users()
    if not users:
        await message.answer("📭 Список зарегистрированных пользователей пуст.")
        return
        
    lines = ["📋 <b>Список зарегистрированных игроков:</b>\n"]
    for i, (tg_name, tag, player_name) in enumerate(users, 1):
        name_str = tg_name if tg_name.startswith("@") else f"<b>{tg_name}</b>"
        lines.append(f"{i}. {name_str} привязан к тегу {tag} ({player_name})")
        
    text = "\n".join(lines)
    # Телеграм не пропускает сообщения длиннее 4096 символов, поэтому разбиваем
    for x in range(0, len(text), 4000):
        await message.answer(
            text[x:x + 4000], 
            parse_mode="HTML", 
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
