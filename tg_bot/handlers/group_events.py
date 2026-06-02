import os
import logging
import aiosqlite
from aiogram import Router, F, Bot
from aiogram.types import Message, ChatJoinRequest
from database.repositories.economy_repo import EconomyRepository
from utils.admin_logger import send_log
from core.config import settings

router = Router()

@router.chat_join_request()
async def process_join_request(update: ChatJoinRequest, bot: Bot):
    if not update.invite_link:
        return

    used_link = update.invite_link.invite_link
    user_id = update.from_user.id
    u_name = f"@{update.from_user.username}" if update.from_user.username else update.from_user.full_name

    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM links WHERE link = ?", (used_link,))
        row = await cursor.fetchone()

        if not row:
            return

        owner_id = row[0]

        if user_id == owner_id:
            await update.approve()
            await db.execute("DELETE FROM links WHERE link = ?", (used_link,))
            await db.commit()
            try:
                await bot.revoke_chat_invite_link(chat_id=update.chat.id, invite_link=used_link)
            except Exception:
                pass
        else:
            await update.decline()
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text="🚫 <b>СИСТЕМА АНТИ-ЗАЙЧИК</b>\n\nВы пытаетесь вступить в клуб по чужой индивидуальной ссылке. Доступ запрещен.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            await send_log(bot, "TOPIC_SESSION", f"🔒 <b>АНТИ-ЗАЙЧИК СРАБОТАЛ</b>\nПользователь {u_name} (<code>{user_id}</code>) пытался зайти по ссылке, сгенерированной для пользователя с ID <code>{owner_id}</code>. Заявка отклонена.")

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
