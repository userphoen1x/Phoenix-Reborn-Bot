import asyncio
import os
from aiogram import Router, F
from aiogram.types import Message
from services.economy_service import EconomyService
from database.repositories.user_repo import UserRepository
from core.exceptions import UserNotRegisteredError, WorkCooldownError, NotEnoughMoneyError

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), lambda msg: str(msg.chat.id) != os.getenv("ADMIN_CHAT_ID"))

def is_cmd(text: str, cmds: list) -> bool:
    if not text: return False
    t = text.lower().strip()
    return any(t == c or t.startswith(c + " ") for c in cmds)

async def delete_later(message: Message, delay: int = 10800):
    await asyncio.sleep(delay)
    try: await message.delete()
    except: pass

@router.message(lambda msg: is_cmd(msg.text, ["сброс экономики"]))
async def cmd_reset_eco(message: Message, user_repo: UserRepository, eco_service: EconomyService):
    admin_role = await user_repo.get_user_role(message.from_user.id)
    if admin_role not in ["Основатель", "Программист"]: return
    await eco_service.eco_repo.reset_all_balances()
    sent = await message.answer("✅ Балансы всех игроков временно сброшены до 1000 ₣.")
    asyncio.create_task(delete_later(sent, 60))

@router.message(lambda msg: is_cmd(msg.text, ["баланс", "кошелек", "кошелёк", "счет", "счёт", "/balance", "balance"]))
async def cmd_balance(message: Message, eco_service: EconomyService):
    try:
        balance = await eco_service.get_balance(message.from_user.id)
        name = f"@{message.from_user.username}" if message.from_user.username else f"<b>{message.from_user.first_name}</b>"
        sent_msg = await message.answer(f"💳 {name}, ваш баланс: <b>{balance}</b> ₣", parse_mode="HTML")
        asyncio.create_task(delete_later(sent_msg))
        asyncio.create_task(delete_later(message, 60))
    except UserNotRegisteredError as e:
        sent_msg = await message.answer(str(e))
        asyncio.create_task(delete_later(sent_msg, 60))

@router.message(lambda msg: is_cmd(msg.text, ["работа", "ворк"]))
async def cmd_work(message: Message, eco_service: EconomyService):
    try:
        reward = await eco_service.do_work(message.from_user.id)
        sent_msg = await message.answer(f"✅ <b>УСПЕШНО!</b>\n🔥 Вы поработали и заработали <b>{reward}</b> ₣!", parse_mode="HTML")
        asyncio.create_task(delete_later(sent_msg))
    except UserNotRegisteredError as e:
        sent = await message.answer(str(e))
        asyncio.create_task(delete_later(sent, 60))
    except WorkCooldownError as e:
        sent_msg = await message.answer(str(e), parse_mode="HTML")
        asyncio.create_task(delete_later(sent_msg))

@router.message(lambda msg: is_cmd(msg.text, ["перевод", "перевести", "pay", "/pay"]))
async def cmd_pay(message: Message, eco_service: EconomyService, user_repo: UserRepository):
    parts = message.text.split()
    if len(parts) < 3:
        sent = await message.answer("❌ Укажите пользователя и сумму. Пример: <code>перевод @username 100</code>", parse_mode="HTML")
        asyncio.create_task(delete_later(sent, 60))
        return
    target_id = None
    target_name = None
    idx = 1
    if parts[idx].startswith("@"):
        target_username = parts[idx]
        idx += 1
        all_users = await user_repo.get_all_users_for_roles()
        for u in all_users:
            if u["tg_name"].lower() == target_username.lower() or f"@{u['tg_name']}".lower() == target_username.lower():
                target_id = u["user_id"]
                break
        target_name = target_username
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        u = message.reply_to_message.from_user
        target_name = f"@{u.username}" if u.username else u.full_name
    if not target_id:
        sent_msg = await message.answer("❌ Не удалось найти пользователя. Укажите @username или ответьте на его сообщение.")
        asyncio.create_task(delete_later(sent_msg))
        return
    if not parts[idx].isdigit():
        sent_msg = await message.answer("❌ Укажите сумму перевода числом. Пример: <code>перевод @username 100</code>", parse_mode="HTML")
        asyncio.create_task(delete_later(sent_msg))
        return
    amount = int(parts[idx])
    try:
        await eco_service.transfer_funds(message.from_user.id, target_id, amount)
        sent_msg = await message.answer(f"✅ <b>Перевод выполнен!</b>\n\n👤 Кому: <b>{target_name}</b>\n💸 Сумма: <b>{amount}</b> ₣", parse_mode="HTML")
        asyncio.create_task(delete_later(sent_msg))
    except (UserNotRegisteredError, NotEnoughMoneyError, ValueError) as e:
        sent_msg = await message.answer(str(e))
        asyncio.create_task(delete_later(sent_msg))