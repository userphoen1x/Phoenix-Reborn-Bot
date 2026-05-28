import asyncio
import os
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.casino_service import CasinoService
from core.exceptions import UserNotRegisteredError, NotEnoughMoneyError

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), lambda msg: str(msg.chat.id) != os.getenv("ADMIN_CHAT_ID"))

class CasinoCb(CallbackData, prefix="cas"):
    act: str
    game: str
    val: str = "0"

async def delete_later(message: Message, delay: int = 10800):
    await asyncio.sleep(delay)
    try: await message.delete()
    except: pass

@router.message(F.text.lower().startswith(("слоты", "слот", "кости", "кубик", "дартс", "боулинг", "футбол", "баскет")))
async def cmd_direct_games(message: Message, casino_service: CasinoService):
    parts = message.text.lower().split()
    cmd = parts[0]
    game = "slot" if any(x in cmd for x in ["слот", "slot"]) else "dice" if any(x in cmd for x in ["кост", "кубик", "dice"]) else "darts" if any(x in cmd for x in ["дартс", "darts"]) else "bowl" if any(x in cmd for x in ["боул", "bowl"]) else "fball" if any(x in cmd for x in ["футб", "ногом", "fball"]) else "bball"
    bet_str = next((p for p in parts[1:] if p.isdigit() or p in ["all", "все"]), None)
    if not bet_str or bet_str in ["all", "все"]:
        await message.answer("❌ Укажите ставку числом. Пример: <code>слоты 100</code>", parse_mode="HTML")
        return
    bet = int(bet_str)
    if bet < 10: return await message.answer("❌ Минимальная ставка 10 ₣!")
    guess = 3 if game == "dice" else None
    try:
        emoji_map = {"slot": "🎰", "dice": "🎲", "darts": "🎯", "bowl": "🎳", "fball": "⚽", "bball": "🏀"}
        dice_msg = await message.answer_dice(emoji=emoji_map[game])
        await asyncio.sleep(4.0 if game in ["slot", "bowl", "fball", "bball"] else 3.0)
        msg_result, win_amount = await casino_service.play_emoji_game(user_id=message.from_user.id, game=game, bet=bet, dice_value=dice_msg.dice.value, guess=guess)
        res_text = f"{emoji_map[game]} <b>РЕЗУЛЬТАТ: {dice_msg.dice.value}</b>\n\n{msg_result}\n💸 Выигрыш: <b>{win_amount} ₣</b>"
        kb_retry = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Повторить партию", callback_data=CasinoCb(act="play", game=game, val=str(bet)).pack())]])
        res_msg = await message.answer(res_text, reply_markup=kb_retry, parse_mode="HTML")
        asyncio.create_task(delete_later(dice_msg))
        asyncio.create_task(delete_later(res_msg))
    except UserNotRegisteredError as e:
        await message.answer(str(e))
    except NotEnoughMoneyError as e:
        await message.answer(str(e))