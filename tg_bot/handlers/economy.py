import asyncio
import re
from aiogram import Router, F
from aiogram.types import Message
from services.economy_service import EconomyService
from tg_bot.filters.role_filters import IsModerator
from database.repositories.user_repo import UserRepository

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

def is_cmd(text: str, cmds: list) -> bool:
    if not text: return False
    t = text.lower().strip()
    for c in cmds:
        pattern = r'^' + re.escape(c) + r'(?:\s|$|[.,!?\n])'
        if re.match(pattern, t):
            return True
    return False

async def delete_later(message: Message, delay: int = 10800):
    await asyncio.sleep(delay)
    try: await message.delete()
    except: pass

async def resolve_target(message: Message, user_repo: UserRepository):
    parts = message.text.split()
    target_username = next((word for word in parts[1:] if word.startswith("@")), None)
    if target_username:
        all_users = await user_repo.get_all_users_for_roles()
        for u in all_users:
            tg_name = u.get("tg_name", "")
            if tg_name:
                check_name = tg_name.lower() if tg_name.startswith("@") else f"@{tg_name.lower()}"
                if check_name == target_username.lower():
                    return u["user_id"], target_username
    elif message.reply_to_message:
        u = message.reply_to_message.from_user
        t_name = f"@{u.username}" if u.username else u.full_name
        return u.id, t_name
    return None, None

@router.message(F.text.func(lambda text: is_cmd(text, ["баланс", "б", "bal"])))
async def cmd_balance(message: Message, eco_service: EconomyService, user_repo: UserRepository):
    target_id, target_name = await resolve_target(message, user_repo)
    if not target_id:
        target_id = message.from_user.id
        target_name = "Ваш"
    else:
        target_name = f"Пользователя {target_name}"

    try:
        bal = await eco_service.get_balance(target_id)
        sent = await message.answer(f"💰 Баланс {target_name}: <b>{bal} ₣</b>", parse_mode="HTML")
        asyncio.create_task(delete_later(sent, 60))
    except Exception as e:
        sent = await message.answer(f"❌ {e}")
        asyncio.create_task(delete_later(sent, 60))

@router.message(F.text.func(lambda text: is_cmd(text, ["перевод", "pay", "give"])))
async def cmd_transfer(message: Message, eco_service: EconomyService, user_repo: UserRepository):
    parts = message.text.split()
    amount = next((int(p) for p in parts[1:] if p.isdigit()), None)
    target_id, target_name = await resolve_target(message, user_repo)

    if not amount or not target_id:
        sent = await message.answer("❌ Формат: <code>/перевод [сумма] [@user или реплай]</code>", parse_mode="HTML")
        asyncio.create_task(delete_later(sent, 60))
        return

    if target_id == message.from_user.id:
        return await message.answer("❌ Нельзя перевести самому себе.")

    try:
        await eco_service.transfer(message.from_user.id, target_id, amount)
        sent = await message.answer(f"✅ Успешный перевод!\n💸 Вы отправили <b>{amount} ₣</b> пользователю {target_name}.", parse_mode="HTML")
        asyncio.create_task(delete_later(sent))
    except Exception as e:
        sent = await message.answer(f"❌ {e}")
        asyncio.create_task(delete_later(sent, 60))

@router.message(F.text.func(lambda text: is_cmd(text, ["начислить", "addmoney"])), IsModerator())
async def cmd_add_money(message: Message, eco_service: EconomyService, user_repo: UserRepository):
    parts = message.text.split()
    amount = next((int(p) for p in parts[1:] if p.isdigit()), None)
    target_id, target_name = await resolve_target(message, user_repo)

    if not amount or not target_id:
        sent = await message.answer("❌ Формат: <code>/начислить [сумма] [@user или реплай]</code>", parse_mode="HTML")
        return asyncio.create_task(delete_later(sent, 60))

    try:
        await eco_service.add_money(target_id, amount)
        sent = await message.answer(f"🏦 Администратор начислил <b>{amount} ₣</b> пользователю {target_name}.", parse_mode="HTML")
        asyncio.create_task(delete_later(sent))
    except Exception as e:
        sent = await message.answer(f"❌ {e}")
        asyncio.create_task(delete_later(sent, 60))

@router.message(F.text.func(lambda text: is_cmd(text, ["штраф", "removemoney"])), IsModerator())
async def cmd_remove_money(message: Message, eco_service: EconomyService, user_repo: UserRepository):
    parts = message.text.split()
    amount = next((int(p) for p in parts[1:] if p.isdigit()), None)
    target_id, target_name = await resolve_target(message, user_repo)

    if not amount or not target_id:
        sent = await message.answer("❌ Формат: <code>/штраф [сумма] [@user или реплай]</code>", parse_mode="HTML")
        return asyncio.create_task(delete_later(sent, 60))

    try:
        await eco_service.add_money(target_id, -amount)
        sent = await message.answer(f"⚖️ Администратор выписал штраф <b>{amount} ₣</b> пользователю {target_name}.", parse_mode="HTML")
        asyncio.create_task(delete_later(sent))
    except Exception as e:
        sent = await message.answer(f"❌ {e}")
        asyncio.create_task(delete_later(sent, 60))