import asyncio
import random
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
    await message.answer(f"Вы успешно поработали и заработали {reward} Ф!")


@router.message(Command("pay"))
async def cmd_pay(message: Message, bot: Bot):
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].startswith("@") or not parts[2].isdigit():
        await message.answer("Формат: /pay @username 100")
        return

    amount = int(parts[2])
    if amount <= 0: return

    sender_id = message.from_user.id
    eco_sender = await get_eco_data(sender_id)
    if not eco_sender or eco_sender["balance"] < amount:
        await message.answer("Недостаточно средств.")
        return

    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.full_name
    else:
        await message.answer("Ответьте на сообщение пользователя командой /pay 100")
        return

    if sender_id == target_id: return

    await update_balance(sender_id, -amount)
    await update_balance(target_id, amount)
    await message.answer(f"Перевод {amount} Ф для {target_name} успешен!")


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
        await message.answer(f"Выпало {result_num} ({color}). Вы выиграли {win} Ф!")
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
        await message.reply(f"Выпало {dice_msg.dice.value}! Вы угадали и выиграли {win} Ф!",
                            reply_to_message_id=dice_msg.message_id)
    else:
        await message.reply(f"Выпало {dice_msg.dice.value}. Вы проиграли.", reply_to_message_id=dice_msg.message_id)