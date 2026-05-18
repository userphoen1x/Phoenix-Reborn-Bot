import os
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message
from utils.database import get_user_data, get_eco_data, get_user_role_by_id, ROLE_SYMBOLS
from utils.brawl_api import get_player_stats

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(Command("profile"))
@router.message(F.text.lower().in_({"профиль", "мой профиль"}))
async def cmd_profile(message: Message):
    user_id = message.from_user.id

    db_user = await get_user_data(user_id)
    eco_data = await get_eco_data(user_id)

    if not db_user or not eco_data:
        sent = await message.answer("Ваш профиль не найден. Привяжите тег через личные сообщения бота.")
        await asyncio.sleep(5)
        await sent.delete()
        return

    name, club, _ = db_user
    role = await get_user_role_by_id(user_id)
    sym = ROLE_SYMBOLS.get(role, "○")

    stats = await get_player_stats(eco_data.get('bs_tag', '')) if 'bs_tag' in eco_data else None
    trophies = stats['trophies'] if stats else "???"
    wins3v3 = stats['wins_3v3'] if stats else "???"
    rank_elo = stats['ranked_curr_elo'] if stats else "???"

    balance = eco_data["balance"]
    level = eco_data["level"]
    bot_class = eco_data["bot_class"]

    text = (
        f"ПРОФИЛЬ ИГРОКА {sym} {name}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"[Баланс] {balance} Ф\n"
        f"[Уровень] {level}\n"
        f"[Класс] {bot_class}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"[Кубки] {trophies}\n"
        f"[Победы 3v3] {wins3v3}\n"
        f"[Ранкед Эло] {rank_elo}\n"
        f"[Клуб] {club}"
    )

    await message.answer(text)