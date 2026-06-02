import os
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from database.repositories.economy_repo import EconomyRepository
from utils.admin_logger import send_log

router = Router()

@router.message(F.chat.type.in_({"group", "supergroup"}) & F.new_chat_members)
async def on_user_join(message: Message, bot: Bot, eco_repo: EconomyRepository):
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_id and str(message.chat.id) == admin_chat_id: return
    for new_member in message.new_chat_members:
        if new_member.id == bot.id: continue
        u_name = f"@{new_member.username}" if new_member.username else new_member.full_name
        eco = await eco_repo.get_eco_data(new_member.id)
        if not eco or not eco.get("bs_tag"):
            try:
                await bot.ban_chat_member(message.chat.id, new_member.id)
                await bot.unban_chat_member(message.chat.id, new_member.id)
                await send_log(bot, "TOPIC_SESSION", f"🚫 <b>ЗАЙЧИК КИКНУТ</b>\nПользователь: {u_name} (<code>{new_member.id}</code>) попытался войти без регистрации.")
            except Exception as e: logging.error(e)
        else: await send_log(bot, "TOPIC_SESSION", f"📥 <b>ВХОД В ЧАТ</b>\nПользователь: {u_name} (<code>{new_member.id}</code>)")

@router.message(F.chat.type.in_({"group", "supergroup"}) & F.left_chat_member)
async def on_user_leave(message: Message, bot: Bot):
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_id and str(message.chat.id) == admin_chat_id: return
    left_member = message.left_chat_member
    u_name = f"@{left_member.username}" if left_member.username else left_member.full_name
    await send_log(bot, "TOPIC_SESSION", f"📤 <b>ВЫХОД ИЗ ЧАТА</b>\nПользователь: {u_name} (<code>{left_member.id}</code>) покинул группу.")
