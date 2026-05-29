import asyncio
import os
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from services.economy_service import EconomyService
from database.repositories.user_repo import UserRepository
from core.exceptions import UserNotRegisteredError, WorkCooldownError, NotEnoughMoneyError

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), lambda msg: str(msg.chat.id) != os.getenv("ADMIN_CHAT_ID"))

class TransferFSM(StatesGroup):
    waiting_for_target = State()
    waiting_for_amount = State()

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

@router.message(lambda msg: is_cmd(msg.text, ["работа", "ворк", "работать", "/work", "work"]))
async def cmd_work(message: Message, eco_service: EconomyService):
    try:
        reward = await eco_service.do_work(message.from_user.id)
        sent_msg = await message.answer(f"✅ Вы заработали <b>{reward}</b> ₣!", parse_mode="HTML")
        asyncio.create_task(delete_later(sent_msg, 60))
        try: await message.delete()
        except: pass
    except WorkCooldownError as e:
        sent_msg = await message.answer(str(e))
        asyncio.create_task(delete_later(sent_msg, 60))
    except UserNotRegisteredError as e:
        sent_msg = await message.answer(str(e))
        asyncio.create_task(delete_later(sent_msg, 60))

@router.message(lambda msg: is_cmd(msg.text, ["баланс", "кошелек", "кошелёк", "счет", "счёт", "/balance", "balance"]))
async def cmd_balance(message: Message, eco_service: EconomyService, user_repo: UserRepository):
    target_id = message.from_user.id
    target_name_display = f"@{message.from_user.username}" if message.from_user.username else f"<b>{message.from_user.first_name}</b>"
    parts = message.text.split()

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name_display = f"@{message.reply_to_message.from_user.username}" if message.reply_to_message.from_user.username else f"<b>{message.reply_to_message.from_user.first_name}</b>"
    elif len(parts) > 1 and parts[1].startswith("@"):
        target_username = parts[1]
        all_users = await user_repo.get_all_users_for_roles()
        found = False
        for u in all_users:
            tg_name = u.get("tg_name", "")
            if tg_name:
                check_name = tg_name.lower() if tg_name.startswith("@") else f"@{tg_name.lower()}"
                if check_name == target_username.lower():
                    target_id = u["user_id"]
                    target_name_display = target_username
                    found = True
                    break
        if not found:
            sent_msg = await message.answer(f"❌ Пользователь {target_username} не найден.")
            asyncio.create_task(delete_later(sent_msg, 60))
            return

    try:
        balance = await eco_service.get_balance(target_id)
        sent_msg = await message.answer(f"💳 {target_name_display}, баланс: <b>{balance}</b> ₣", parse_mode="HTML")
        asyncio.create_task(delete_later(sent_msg))
        asyncio.create_task(delete_later(message, 60))
    except UserNotRegisteredError as e:
        err_text = "❌ Этот игрок еще не зарегистрирован." if target_id != message.from_user.id else str(e)
        sent_msg = await message.answer(err_text)
        asyncio.create_task(delete_later(sent_msg, 60))

async def execute_transfer(message: Message, sender_id: int, target_id: int, target_name: str, amount: int, eco_service: EconomyService, state: FSMContext):
    try:
        await eco_service.transfer_funds(sender_id, target_id, amount)
        sent_msg = await message.answer(f"✅ <b>Перевод выполнен!</b>\n\n👤 Кому: {target_name}\n💸 Сумма: <b>{amount} ₣</b>", parse_mode="HTML")
        asyncio.create_task(delete_later(sent_msg, 60))
    except UserNotRegisteredError as e:
        err_text = "❌ Этот игрок еще не зарегистрирован в боте." if target_id != sender_id else str(e)
        sent_msg = await message.answer(err_text)
        asyncio.create_task(delete_later(sent_msg, 15))
    except NotEnoughMoneyError as e:
        sent_msg = await message.answer(str(e))
        asyncio.create_task(delete_later(sent_msg, 15))
    except ValueError as e:
        sent_msg = await message.answer(f"❌ {e}")
        asyncio.create_task(delete_later(sent_msg, 15))
    finally:
        await state.clear()

@router.message(lambda msg: msg.text and is_cmd(msg.text, ["перевод", "передать", "transfer"]))
async def cmd_transfer(message: Message, state: FSMContext, eco_service: EconomyService, user_repo: UserRepository):
    await state.clear()
    parts = message.text.split()
    target_username = None
    amount = None

    for word in parts[1:]:
        if word.startswith("@") and not target_username:
            target_username = word
        elif word.isdigit() and amount is None:
            amount = int(word)

    target_id, target_name = None, None

    if target_username:
        all_users = await user_repo.get_all_users_for_roles()
        for u in all_users:
            tg_name = u.get("tg_name", "")
            if tg_name:
                check_name = tg_name.lower() if tg_name.startswith("@") else f"@{tg_name.lower()}"
                if check_name == target_username.lower():
                    target_id = u["user_id"]
                    target_name = target_username
                    break
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        u = message.reply_to_message.from_user
        target_name = f"@{u.username}" if u.username else f"<b>{u.first_name}</b>"

    if target_id and amount is not None and amount > 0:
        await execute_transfer(message, message.from_user.id, target_id, target_name, amount, eco_service, state)
        try: await message.delete()
        except: pass
    elif target_id:
        await state.update_data(target_id=target_id, target_name=target_name)
        await message.answer("💸 <b>Сколько Феников вы хотите перевести?</b>\n<i>Напишите сумму числом.</i>", parse_mode="HTML")
        await state.set_state(TransferFSM.waiting_for_amount)
    elif amount is not None and amount > 0:
        await state.update_data(amount=amount)
        await message.answer("👤 <b>Кому перевести?</b>\n<i>Напишите @username игрока.</i>", parse_mode="HTML")
        await state.set_state(TransferFSM.waiting_for_target)
    else:
        await message.answer("👤 <b>Кому перевести?</b>\n<i>Напишите @username игрока.</i>", parse_mode="HTML")
        await state.set_state(TransferFSM.waiting_for_target)

@router.message(TransferFSM.waiting_for_target)
async def process_transfer_target(message: Message, state: FSMContext, user_repo: UserRepository, eco_service: EconomyService):
    if is_cmd(message.text, ["отмена", "cancel", "стоп"]):
        await state.clear()
        return await message.answer("❌ Перевод отменен.")

    target_username = message.text.strip()
    if not target_username.startswith("@"):
        target_username = f"@{target_username}"

    target_id, target_name = None, None
    all_users = await user_repo.get_all_users_for_roles()
    for u in all_users:
        tg_name = u.get("tg_name", "")
        if tg_name:
            check_name = tg_name.lower() if tg_name.startswith("@") else f"@{tg_name.lower()}"
            if check_name == target_username.lower():
                target_id = u["user_id"]
                target_name = target_username
                break
    
    if not target_id:
        sent_msg = await message.answer(f"❌ Пользователь {target_username} не найден. Попробуйте еще раз или напишите «отмена».")
        asyncio.create_task(delete_later(sent_msg, 15))
        return
        
    data = await state.get_data()
    amount = data.get("amount")
    
    if amount:
        await execute_transfer(message, message.from_user.id, target_id, target_name, amount, eco_service, state)
    else:
        await state.update_data(target_id=target_id, target_name=target_name)
        await message.answer("💸 <b>Сколько Феников вы хотите перевести?</b>\n<i>Напишите сумму числом.</i>", parse_mode="HTML")
        await state.set_state(TransferFSM.waiting_for_amount)

@router.message(TransferFSM.waiting_for_amount)
async def process_transfer_amount(message: Message, state: FSMContext, eco_service: EconomyService):
    if is_cmd(message.text, ["отмена", "cancel", "стоп"]):
        await state.clear()
        return await message.answer("❌ Перевод отменен.")

    if not message.text.isdigit():
        sent_msg = await message.answer("❌ Укажите сумму целым числом. Попробуйте еще раз или напишите «отмена».")
        asyncio.create_task(delete_later(sent_msg, 15))
        return
        
    amount = int(message.text)
    if amount <= 0:
        sent_msg = await message.answer("❌ Сумма должна быть больше нуля.")
        asyncio.create_task(delete_later(sent_msg, 15))
        return
        
    data = await state.get_data()
    target_id = data.get("target_id")
    target_name = data.get("target_name")
    
    if target_id and target_name:
        await execute_transfer(message, message.from_user.id, target_id, target_name, amount, eco_service, state)
    else:
        await state.clear()
        await message.answer("❌ Произошла ошибка. Пожалуйста, начните перевод заново.")
