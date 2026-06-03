import asyncio
import re
import string
from aiogram import Router, F
from aiogram.types import Message, LinkPreviewOptions
from database.repositories.user_repo import UserRepository
from database.repositories.economy_repo import EconomyRepository
from database.repositories.chat_repo import ChatRepository
from external.brawl_api import BrawlAPIClient
from core.config import settings

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

ROLE_SYMBOLS = {"Главарь": "👑", "Программист": "🧑🏻‍💻", "Президент": "🌟", "Вице-президент": "⭐", "Ветеран": "🎖",
                "Участник": "👤", "Гость": "🗣️"}

async def delete_later(message: Message, delay: int = 10800):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

def get_rank_name(val: int):
    ranks = {1: "🥉 Бронза 1", 2: "🥉 Бронза 2", 3: "🥉 Бронза 3", 4: "🥈 Серебро 1", 5: "🥈 Серебро 2", 6: "🥈 Серебро 3",
             7: "🥇 Золото 1", 8: "🥇 Золото 2", 9: "🥇 Золото 3", 10: "💎 Алмаз 1", 11: "💎 Алмаз 2", 12: "💎 Алмаз 3",
             13: "🟣 Мифик 1", 14: "🟣 Мифик 2", 15: "🟣 Мифик 3", 16: "🔴 Лега 1", 17: "🔴 Лега 2", 18: "🔴 Лега 3",
             19: "🟡 Мастер 1", 20: "🟡 Мастер 2", 21: "🟡 Мастер 3", 22: "🟢 Про"}
    return ranks.get(val, "🏳️ Без ранга")

def is_cmd(text: str, cmds: list) -> bool:
    if not text: return False
    t = text.lower().strip()
    for c in cmds:
        # Жесткая граница: команда должна быть первым словом в сообщении
        pattern = r'^' + re.escape(c) + r'(?:\s|$|[.,!?\n])'
        if re.match(pattern, t):
            return True
    return False

@router.message(F.text.func(lambda text: is_cmd(text, ["профиль", "мой профиль", "/profile"])))
async def cmd_profile(message: Message, user_repo: UserRepository, eco_repo: EconomyRepository,
                      chat_repo: ChatRepository, brawl_client: BrawlAPIClient):
    
    parts = message.text.split()
    target_id = message.from_user.id

    # 1. Высший приоритет тегу
    target_username = next((word for word in parts[1:] if word.startswith("@")), None)
    
    if target_username:
        all_users = await user_repo.get_all_users_for_roles()
        found = False
        for u in all_users:
            tg_name = u.get("tg_name", "")
            if tg_name:
                check_name = tg_name.lower() if tg_name.startswith("@") else f"@{tg_name.lower()}"
                if check_name == target_username.lower():
                    target_id = u["user_id"]
                    found = True
                    break
        if not found:
            sent_msg = await message.answer(f"❌ Пользователь {target_username} не найден в базе данных.")
            asyncio.create_task(delete_later(sent_msg, 60))
            return
    # 2. Если тега нет, проверяем реплай
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id

    db_user = await user_repo.get_user_data(target_id)
    eco_data = await eco_repo.get_eco_data(target_id)
    game_role = await user_repo.get_user_role(target_id)

    if not db_user or not eco_data:
        return await message.answer("❌ Профиль не найден. Игрок не привязал тег.")

    roles = []
    if str(target_id) == settings.FOUNDER_ID: roles.append("Главарь")
    if str(target_id) in settings.DEVELOPER_IDS: roles.append("Программист")
    roles.append(game_role)

    sym = "".join([ROLE_SYMBOLS.get(r, "🗣️") for r in roles])
    
    player_name, club_name, _, tg_full_name = db_user
    name_link = f"<a href='https://t.me/{tg_full_name[1:]}'>{player_name}</a>" if tg_full_name and tg_full_name.startswith("@") else f"<b>{player_name}</b>"
    club_display = club_name if club_name else "Без клуба"

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
        else:
            gain_str = trophies = wins3v3 = sd_wins = rank_name = rank_elo = "???"
    else:
        gain_str = trophies = wins3v3 = sd_wins = rank_name = rank_elo = "???"

    balance = eco_data.get("balance", 0)

    text = (
        f"👤 <b>ПРОФИЛЬ УЧАСТНИКА</b>\n\n"
        f"┌ 📱 Ник: {sym} {name_link}\n"
        f"├ 🏰 Клуб: {club_display}\n"
        f"├ 🏆 Общие: {trophies}\n"
        f"├ 🎖 Ранкед: {rank_name} ({rank_elo})\n"
        f"├ ⚔️ 3 на 3: {wins3v3}\n"
        f"├ 🌵 ШД: {sd_wins}\n"
        f"├ 📈 За день: {gain_str}\n"
        f"└ 💰 Баланс: {balance} ₣"
    )

    await message.answer(text, link_preview_options=LinkPreviewOptions(is_disabled=True))


@router.message(F.text.func(lambda text: is_cmd(text, ["клуб", "ранкед", "лига", "кубки"])))
async def cmd_mini_stats(message: Message, user_repo: UserRepository, brawl_client: BrawlAPIClient):
    parts = message.text.split()
    cmd = parts[0].lower().strip(string.punctuation)
    
    target_id = message.from_user.id
    target_username = next((word for word in parts[1:] if word.startswith("@")), None)
    
    # 1. Поиск цели по тегу
    if target_username:
        all_users = await user_repo.get_all_users_for_roles()
        found = False
        for u in all_users:
            tg_name = u.get("tg_name", "")
            if tg_name:
                check_name = tg_name.lower() if tg_name.startswith("@") else f"@{tg_name.lower()}"
                if check_name == target_username.lower():
                    target_id = u["user_id"]
                    found = True
                    break
        if not found:
            sent_msg = await message.answer(f"❌ Пользователь {target_username} не найден в базе.")
            asyncio.create_task(delete_later(sent_msg, 60))
            return
            
    # 2. Если нет тега, ищем по реплаю
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id

    db_user = await user_repo.get_user_data(target_id)
    if not db_user:
        return await message.answer("❌ Профиль не найден. Игрок не привязал тег.")

    player_name, db_club_name, bs_tag, tg_full_name = db_user
    
    if not bs_tag:
        return await message.answer("❌ Игрок не привязал тег.")

    stats = await brawl_client.get_player_stats(bs_tag)
    if not stats:
        return await message.answer("❌ Ошибка получения данных из API Brawl Stars.")

    prefix = f"👤 <b>{player_name}</b>"

    if cmd == "клуб":
        c_name = stats.get('club', {}).get('name', 'Без клуба')
        c_role_eng = stats.get('club', {}).get('role', 'Отсутствует')
        role_trans = {"president": "Президент", "vicePresident": "Вице-президент", "senior": "Ветеран", "member": "Участник"}
        c_role_ru = role_trans.get(c_role_eng, c_role_eng) if c_role_eng != 'Отсутствует' else 'Отсутствует'
        
        text = f"{prefix}\n🏰 Клуб: <b>{c_name}</b>\n🔰 Роль: {c_role_ru}"
        
    elif cmd in ["ранкед", "лига"]:
        rank_val = stats.get('ranked_curr_rank', 0)
        elo = stats.get('ranked_curr_elo', 0)
        max_rank = stats.get('highest_ranked_rank', 0)
        text = f"{prefix}\n🎖 Ранкед: <b>{get_rank_name(rank_val)}</b> ({elo})\n🌟 Максимум: {get_rank_name(max_rank)}"
        
    elif cmd == "кубки":
        trophies = stats.get('trophies', 0)
        max_trophies = stats.get('highest_trophies', trophies)
        text = f"{prefix}\n🏆 Кубки: <b>{trophies}</b> (Макс: {max_trophies})"

    await message.answer(text, link_preview_options=LinkPreviewOptions(is_disabled=True))
