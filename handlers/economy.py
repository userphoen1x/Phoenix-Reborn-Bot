import asyncio
import random
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message
from utils.database import get_eco_data, update_balance, set_eco_data

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


def get_class_bonus(bot_class: str):
    if bot_class == "Махим": return {"work_cd": 4, "luck": 0.10, "rob_mult": 1.0}
    if bot_class == "Спырту": return {"work_cd": 3, "luck": -0.05, "rob_mult": 1.5}
    if bot_class == "Ванёк": return {"work_cd": 5, "luck": 0.20, "rob_mult": 1.0}
    return {"work_cd": 4, "luck": 0.0, "rob_mult": 1.0}


@router.message(F.text.lower().in_({"работа", "ворк"}))
async def cmd_work(message: Message):
    user_id = message.from_user.id
    eco = await get_eco_data(user_id)
    if not eco: return

    bonuses = get_class_bonus(eco["bot_class"])
    cd_hours = bonuses["work_cd"]

    now = datetime.now()
    if eco["last_work"]:
        last_work = datetime.fromisoformat(eco["last_work"])
        diff = now - last_work
        if diff < timedelta(hours=cd_hours):
            rem = timedelta(hours=cd_hours) - diff
            mm, ss = divmod(int(rem.total_seconds()), 60)
            hh, mm = divmod(mm, 60)
            await message.answer(f"Ожидание... Вы сможете работать через {hh}ч {mm}м.")
            return

    reward = random.randint(50, 150)
    await update_balance(user_id, reward)
    await set_eco_data(user_id, "last_work", now.isoformat())
    await message.answer(f"Вы успешно поработали и заработали {reward} ₣!")


@router.message(lambda msg: msg.text and msg.text.lower().startswith(("перевод", "перевести", "pay", "/pay")))
async def cmd_pay(message: Message, bot: Bot):
    parts = message.text.split()
    if not parts: return

    target_id = None
    target_name = None
    idx = 1

    if idx < len(parts) and parts[idx].startswith("@"):
        target_username = parts[idx]
        idx += 1
        db_path = "/app/data/bot_data_v3.db"
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT user_id FROM tg_profiles WHERE full_name = ? COLLATE NOCASE",
                                  (target_username,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    target_id = row[0]
                    target_name = target_username
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        u = message.reply_to_message.from_user
        target_name = f"@{u.username}" if u.username else u.full_name

    if not target_id:
        await message.answer("Не удалось найти пользователя. Укажите @username или ответьте на его сообщение.")
        return

    if idx >= len(parts) or not parts[idx].isdigit():
        await message.answer("Укажите сумму перевода числом. Пример: перевод 100")
        return

    amount = int(parts[idx])
    if amount <= 0: return

    sender_id = message.from_user.id
    if sender_id == target_id: return

    eco_sender = await get_eco_data(sender_id)
    if not eco_sender or eco_sender["balance"] < amount:
        await message.answer("Недостаточно средств.")
        return

    eco_target = await get_eco_data(target_id)
    if not eco_target:
        await message.answer("Этот пользователь еще не зарегистрирован в экономической системе бота.")
        return

    await update_balance(sender_id, -amount)
    await update_balance(target_id, amount)
    await message.answer(f"Перевод {amount} ₣ для {target_name} успешен!")


@router.message(lambda msg: msg.text and msg.text.lower().startswith(("рулетка", "roulette")))
async def cmd_roulette(message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Формат: рулетка [сумма] [красное/черное/зеро]")
        return

    amount_str, bet_type = parts[1], parts[2].lower()
    if not amount_str.isdigit(): return
    amount = int(amount_str)

    user_id = message.from_user.id
    eco = await get_eco_data(user_id)
    if not eco or eco["balance"] < amount:
        await message.answer("Недостаточно средств.")
        return

    await update_balance(user_id, -amount)
    result_num = random.randint(0, 36)
    is_red = result_num in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]

    color = "зеро" if result_num == 0 else ("красное" if is_red else "черное")

    win = 0
    if bet_type in ["зеро", "zero", "0"] and result_num == 0:
        win = amount * 35
    elif bet_type in ["красное", "red"] and is_red:
        win = amount * 2
    elif bet_type in ["черное", "black"] and not is_red and result_num != 0:
        win = amount * 2

    if win > 0:
        await update_balance(user_id, win)
        await message.answer(f"Выпало {result_num} ({color}). Вы выиграли {win} ₣!")
    else:
        await message.answer(f"Выпало {result_num} ({color}). Ставка сгорела.")


@router.message(lambda msg: msg.text and msg.text.lower().startswith(("кости", "dice")))
async def cmd_dice(message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Формат: кости [сумма] [число 1-6]")
        return

    amount, guess = parts[1], parts[2]
    if not amount.isdigit() or not guess.isdigit(): return
    amount, guess = int(amount), int(guess)

    if guess < 1 or guess > 6: return

    user_id = message.from_user.id
    eco = await get_eco_data(user_id)
    if not eco or eco["balance"] < amount:
        await message.answer("Недостаточно средств.")
        return

    await update_balance(user_id, -amount)
    dice_msg = await message.answer_dice(emoji="🎲")

    await asyncio.sleep(4)

    if dice_msg.dice.value == guess:
        win = amount * 5
        await update_balance(user_id, win)
        await message.reply(f"Выпало {dice_msg.dice.value}! Вы угадали и выиграли {win} ₣!",
                            reply_to_message_id=dice_msg.message_id)
    else:
        await message.reply(f"Выпало {dice_msg.dice.value}. Вы проиграли.", reply_to_message_id=dice_msg.message_id)