import os
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from database.repositories.user_repo import UserRepository

router = Router()

@router.message(Command("unlink"))
async def cmd_unlink_tag(message: Message, bot: Bot, user_repo: UserRepository):
    if str(message.from_user.id) not in [os.getenv("FOUNDER_ID"), os.getenv("ADMIN_ID")]: return
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