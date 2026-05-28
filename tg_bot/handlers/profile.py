from aiogram import Router, F
from aiogram.types import Message, LinkPreviewOptions
from database.repositories.user_repo import UserRepository
from database.repositories.economy_repo import EconomyRepository
from database.repositories.chat_repo import ChatRepository
from external.brawl_api import BrawlAPIClient

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

ROLE_SYMBOLS = {"Главарь": "👑", "Программист": "🧑🏻‍💻", "Президент": "🌟", "Вице-президент": "⭐", "Ветеран": "🎖", "Участник": "👤", "Гость": "🗣️"}

def get_rank_name(val: int):
    ranks = {1: "🥉 Бронза 1", 2: "🥉 Бронза 2", 3: "🥉 Бронза 3", 4: "🥈 Серебро 1", 5: "🥈 Серебро 2", 6: "🥈 Серебро 3", 7: "🥇 Золото 1", 8: "🥇 Золото 2", 9: "🥇 Золото 3", 10: "💎 Алмаз 1", 11: "💎 Алмаз 2", 12: "💎 Алмаз 3", 13: "🟣 Мифик 1", 14: "🟣 Мифик 2", 15: "🟣 Мифик 3", 16: "🔴 Лега 1", 17: "🔴 Лега 2", 18: "🔴 Лега 3", 19: "🟡 Мастер 1", 20: "🟡 Мастер 2", 21: "🟡 Мастер 3", 22: "🟢 Про"}
    return ranks.get(val, "🏳️ Без ранга")

@router.message(F.text.lower().startswith(("профиль", "мой профиль", "/profile")))
async def cmd_profile(message: Message, user_repo: UserRepository, eco_repo: EconomyRepository, chat_repo: ChatRepository, brawl_client: BrawlAPIClient):
    target_id = message.from_user.id
    if message.reply_to_message: target_id = message.reply_to_message.from_user.id
    db_user = await user_repo.get_user_data(target_id)
    eco_data = await eco_repo.get_eco_data(target_id)
    role = await user_repo.get_user_role(target_id)
    if not db_user or not eco_data:
        return await message.answer("❌ Профиль не найден. Игрок не привязал тег.")
    player_name, _, _, tg_full_name = db_user
    sym = ROLE_SYMBOLS.get(role, "🗣️")
    name_link = f"<a href='https://t.me/{tg_full_name[1:]}'>{player_name}</a>" if tg_full_name and tg_full_name.startswith("@") else f"<b>{player_name}</b>"
    bs_tag = eco_data.get('bs_tag', '')
    if bs_tag:
        stats = await brawl_client.get_player_stats(bs_tag)
        baseline_map = await chat_repo.get_baseline_trophies(1, [bs_tag])
        if stats:
            trophies = stats['trophies']
            baseline = baseline_map.get(bs_tag, trophies)
            gain = trophies - baseline
            gain_str = f"+{gain}" if gain > 0 else str(gain)
            wins3v3 = stats['wins_3v3']
            sd_wins = stats['solo_wins'] + stats['duo_wins']
            rank_name = get_rank_name(stats.get('ranked_curr_rank', 0))
            rank_elo = stats.get('ranked_curr_elo', 0)
        else: gain_str = trophies = wins3v3 = sd_wins = rank_name = rank_elo = "???"
    else: gain_str = trophies = wins3v3 = sd_wins = rank_name = rank_elo = "???"
    balance = eco_data["balance"]
    level = eco_data["level"]
    text = f"👤 <b>ПРОФИЛЬ УЧАСТНИКА</b>\n\n┌ 📱 Ник: {sym} {name_link}\n├ 📈 За день: {gain_str}\n├ 🏆 Общие: {trophies}\n├ ⚔️ 3 на 3: {wins3v3}\n├ 🌵 ШД: {sd_wins}\n├ 🎖 Ранкед: {rank_name} ({rank_elo})\n├ 🌟 Уровень: {level}\n└ 💰 Баланс: {balance} ₣"
    await message.answer(text, link_preview_options=LinkPreviewOptions(is_disabled=True))