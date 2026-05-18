import os
import asyncio
import aiosqlite
from datetime import date, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, LinkPreviewOptions
from utils.database import get_user_data, get_eco_data, get_user_role_by_id, ROLE_SYMBOLS
from utils.brawl_api import get_player_stats

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


def get_rank_name(val: int):
    ranks = {
        1: "Бронза 1", 2: "Бронза 2", 3: "Бронза 3",
        4: "Серебро 1", 5: "Серебро 2", 6: "Серебро 3",
        7: "Золото 1", 8: "Золото 2", 9: "Золото 3",
        10: "Алмаз 1", 11: "Алмаз 2", 12: "Алмаз 3",
        13: "Мифик 1", 14: "Мифик 2", 15: "Мифик 3",
        16: "Лега 1", 17: "Лега 2", 18: "Лега 3",
        19: "Мастер 1", 20: "Мастер 2", 21: "Мастер 3",
        22: "Про"
    }
    return ranks.get(val, "Без ранга")


async def get_daily_gain(tag: str) -> int:
    db_path = "/app/data/bot_data_v3.db"
    td = (date.today() - timedelta(days=1)).isoformat()
    async with aiosqlite.connect(db_path) as db:
        query = """
                SELECT (SELECT trophies FROM bs_snapshots WHERE tag = ? ORDER BY record_date DESC LIMIT 1) -
                (SELECT trophies FROM bs_snapshots WHERE tag = ? AND record_date >= ? ORDER BY record_date ASC LIMIT 1) \
                """
        async with db.execute(query, (tag, tag, td)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] is not None else 0


@router.message(lambda msg: msg.text and msg.text.lower().startswith(("профиль", "мой профиль", "/profile")))
async def cmd_profile(message: Message):
    target_id = message.from_user.id
    parts = message.text.split()

    idx = 1
    if message.text.lower().startswith("мой профиль"):
        idx = 2

    if len(parts) > idx and parts[idx].startswith("@"):
        target_username = parts[idx]
        db_path = "/app/data/bot_data_v3.db"
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT user_id FROM tg_profiles WHERE full_name = ? COLLATE NOCASE",
                                  (target_username,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    target_id = row[0]
                else:
                    await message.answer("Пользователь не найден в базе.")
                    return
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id

    db_user = await get_user_data(target_id)
    eco_data = await get_eco_data(target_id)

    if not db_user or not eco_data:
        sent = await message.answer("Профиль не найден. Игрок не привязал тег.")
        await asyncio.sleep(5)
        try:
            await sent.delete()
        except:
            pass
        return

    player_name, _, _, tg_full_name = db_user
    role = await get_user_role_by_id(target_id)
    sym = ROLE_SYMBOLS.get(role, "○")

    if tg_full_name and tg_full_name.startswith("@"):
        name_link = f"<a href='https://t.me/{tg_full_name[1:]}'>{player_name}</a>"
    else:
        name_link = f"<a href='tg://user?id={target_id}'>{player_name}</a>"

    bs_tag = eco_data.get('bs_tag', '')
    stats = await get_player_stats(bs_tag) if bs_tag else None
    gain = await get_daily_gain(bs_tag) if bs_tag else 0
    gain_str = f"+{gain}" if gain > 0 else str(gain)

    if stats:
        trophies = stats['trophies']
        wins3v3 = stats['wins_3v3']
        sd_wins = stats['solo_wins'] + stats['duo_wins']
        rank_name = get_rank_name(stats.get('ranked_curr_rank', 0))
        rank_elo = stats.get('ranked_curr_elo', 0)
    else:
        trophies = wins3v3 = sd_wins = rank_name = rank_elo = "???"

    balance = eco_data["balance"]
    level = eco_data["level"]

    text = (
        f"<b>Профиль игрока</b>\n\n"
        f"┌ Ник: {sym} <b>{name_link}</b>\n"
        f"├ За день: {gain_str}\n"
        f"├ Общие: {trophies}\n"
        f"├ 3 на 3: {wins3v3}\n"
        f"├ ШД: {sd_wins}\n"
        f"├ Ранкед: {rank_name} ({rank_elo})\n"
        f"├ Уровень: {level}\n"
        f"└ Баланс: {balance} ₣"
    )

    await message.answer(text, link_preview=LinkPreviewOptions(is_disabled=True))