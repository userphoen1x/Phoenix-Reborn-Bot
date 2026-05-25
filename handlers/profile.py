import os
import asyncio
import aiosqlite
from datetime import date, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, LinkPreviewOptions
from utils.database import get_user_data, get_eco_data, get_user_role_by_id, get_baseline_trophies, ROLE_SYMBOLS
from utils.brawl_api import get_player_stats

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


def get_rank_name(val: int):
    ranks = {
        1: "🥉 Бронза 1", 2: "🥉 Бронза 2", 3: "🥉 Бронза 3",
        4: "🥈 Серебро 1", 5: "🥈 Серебро 2", 6: "🥈 Серебро 3",
        7: "🥇 Золото 1", 8: "🥇 Золото 2", 9: "🥇 Золото 3",
        10: "💎 Алмаз 1", 11: "💎 Алмаз 2", 12: "💎 Алмаз 3",
        13: "🟣 Мифик 1", 14: "🟣 Мифик 2", 15: "🟣 Мифик 3",
        16: "🔴 Лега 1", 17: "🔴 Лега 2", 18: "🔴 Лега 3",
        19: "🟡 Мастер 1", 20: "🟡 Мастер 2", 21: "🟡 Мастер 3",
        22: "🟢 Про"
    }
    return ranks.get(val, "🏳️ Без ранга")


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
                    await message.answer("❌ Пользователь не найден в базе.")
                    return
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id

    # 🚀 ПАРАЛЛЕЛЬНЫЙ ЗАПРОС К БД: Вытягиваем 3 независимые таблицы одновременно
    db_results = await asyncio.gather(
        get_user_data(target_id),
        get_eco_data(target_id),
        get_user_role_by_id(target_id),
        return_exceptions=True
    )

    db_user = db_results[0] if not isinstance(db_results[0], Exception) else None
    eco_data = db_results[1] if not isinstance(db_results[1], Exception) else None
    role = db_results[2] if not isinstance(db_results[2], Exception) else "Гость"

    if not db_user or not eco_data:
        sent = await message.answer("❌ Профиль не найден. Игрок не привязал тег.")
        await asyncio.sleep(5)
        try:
            await sent.delete()
        except:
            pass
        return

    player_name, _, _, tg_full_name = db_user
    sym = ROLE_SYMBOLS.get(role, "○")

    if tg_full_name and tg_full_name.startswith("@"):
        name_link = f"<a href='https://t.me/{tg_full_name[1:]}'>{player_name}</a>"
    else:
        name_link = f"<b>{player_name}</b>"

    bs_tag = eco_data.get('bs_tag', '')

    if bs_tag:
        # 🚀 ПАРАЛЛЕЛЬНЫЙ ЗАПРОС: API игры и Снимок кубков из БД одновременно
        api_db_results = await asyncio.gather(
            get_player_stats(bs_tag),
            get_baseline_trophies(1, [bs_tag]),
            return_exceptions=True
        )
        stats = api_db_results[0] if not isinstance(api_db_results[0], Exception) else None
        baseline_map = api_db_results[1] if not isinstance(api_db_results[1], Exception) else {}

        if stats:
            trophies = stats['trophies']
            baseline = baseline_map.get(bs_tag, trophies)
            gain = trophies - baseline
            gain_str = f"+{gain}" if gain > 0 else str(gain)

            wins3v3 = stats['wins_3v3']
            sd_wins = stats['solo_wins'] + stats['duo_wins']
            rank_name = get_rank_name(stats.get('ranked_curr_rank', 0))
            rank_elo = stats.get('ranked_curr_elo', 0)
        else:
            gain_str = "???"
            trophies = wins3v3 = sd_wins = rank_name = rank_elo = "???"
    else:
        gain_str = "???"
        trophies = wins3v3 = sd_wins = rank_name = rank_elo = "???"

    balance = eco_data["balance"]
    level = eco_data["level"]

    text = (
        f"👤 <b>ПРОФИЛЬ УЧАСТНИКА</b>\n\n"
        f"┌ 📱 Ник: {sym} {name_link}\n"
        f"├ 📈 За день: {gain_str}\n"
        f"├ 🏆 Общие: {trophies}\n"
        f"├ ⚔️ 3 на 3: {wins3v3}\n"
        f"├ 🌵 ШД: {sd_wins}\n"
        f"├ 🎖 Ранкед: {rank_name} ({rank_elo})\n"
        f"├ 🌟 Уровень: {level}\n"
        f"└ 💰 Баланс: {balance} ₣"
    )

    await message.answer(text, link_preview_options=LinkPreviewOptions(is_disabled=True))