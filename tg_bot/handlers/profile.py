import re
import string
from aiogram import Router, F
from aiogram.types import Message, LinkPreviewOptions
from dishka.integrations.aiogram import inject, FromDishka

from database.repositories.user_repo import UserRepository
from database.repositories.economy_repo import EconomyRepository
from database.repositories.chat_repo import ChatRepository
from external.brawl_api import BrawlAPIClient
from core.config import settings
from core.constants import ROLE_SYMBOLS, RANK_NAMES, DELAYS
from core.garbage_collector import schedule_delete
from core.lexicon import LEXICON

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


def is_cmd(text: str, cmds: list) -> bool:
    if not text: return False
    t = text.lower().strip()
    for c in cmds:
        pattern = r'^' + re.escape(c) + r'(?:\s|$|[.,!?\n])'
        if re.match(pattern, t):
            return True
    return False


@router.message(F.text.func(lambda text: is_cmd(text, ["профиль", "мой профиль", "/profile"])))
@inject
async def cmd_profile(message: Message, user_repo: FromDishka[UserRepository], eco_repo: FromDishka[EconomyRepository],
                      chat_repo: FromDishka[ChatRepository], brawl_client: FromDishka[BrawlAPIClient]):
    parts = message.text.split()
    target_id = message.from_user.id
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
            sent_msg = await message.answer(LEXICON["profile_not_found_db"].format(target=target_username))
            schedule_delete(sent_msg, DELAYS["default"])
            return
    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id

    db_user = await user_repo.get_user_data(target_id)
    eco_data = await eco_repo.get_eco_data(target_id)
    game_role = await user_repo.get_user_role(target_id)

    if not db_user or not eco_data:
        sent = await message.answer(LEXICON["profile_not_linked"])
        schedule_delete(sent, DELAYS["short"])
        return

    roles = []
    if str(target_id) == settings.FOUNDER_ID: roles.append("Лидер")
    if str(target_id) in settings.DEVELOPER_IDS: roles.append("Разработчик")
    roles.append(game_role)

    role_label = "Роли" if len(roles) > 1 else "Роль"
    role_str = ", ".join([f"{ROLE_SYMBOLS.get(r, '🗣️')} {r}" for r in roles])

    player_name, club_name, _, tg_full_name = db_user
    name_link = f"<a href='https://t.me/{tg_full_name[1:]}'>{player_name}</a>" if tg_full_name and tg_full_name.startswith(
        "@") else f"<b>{player_name}</b>"
    club_display = club_name if club_name else "Без клуба"

    bs_tag = eco_data.get('bs_tag', '')
    if bs_tag:
        stats = await brawl_client.get_player_stats(bs_tag)
        baseline_map = await chat_repo.get_baseline_trophies(1, [bs_tag])
        if stats:
            trophies = stats['trophies']
            baseline = baseline_map.get(bs_tag, trophies)
            gain = trophies - baseline
            gain_display = f" (+{gain})" if gain > 0 else (f" ({gain})" if gain < 0 else "")
            trophies_str = f"{trophies}{gain_display}"
            wins3v3 = stats['wins_3v3']
            sd_wins = stats['solo_wins'] + stats['duo_wins']
            rank_name = RANK_NAMES.get(stats.get('ranked_curr_rank', 0), "🏳️ Без ранга")
            rank_elo = stats.get('ranked_curr_elo', 0)
        else:
            trophies_str = wins3v3 = sd_wins = rank_name = rank_elo = "???"
    else:
        trophies_str = wins3v3 = sd_wins = rank_name = rank_elo = "???"

    balance = eco_data.get("balance", 0)

    text = LEXICON["profile_text"].format(
        name_link=name_link, role_label=role_label, role_str=role_str,
        club_display=club_display, trophies_str=trophies_str, rank_name=rank_name,
        rank_elo=rank_elo, wins3v3=wins3v3, sd_wins=sd_wins, balance=balance
    )

    await message.answer(text, link_preview_options=LinkPreviewOptions(is_disabled=True))


@router.message(F.text.func(lambda text: is_cmd(text, ["клуб", "ранкед", "лига", "кубки"])))
@inject
async def cmd_mini_stats(message: Message, user_repo: FromDishka[UserRepository],
                         eco_repo: FromDishka[EconomyRepository], brawl_client: FromDishka[BrawlAPIClient]):
    parts = message.text.split()
    cmd = parts[0].lower().strip(string.punctuation)

    target_id = message.from_user.id
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
            sent_msg = await message.answer(LEXICON["profile_not_found_db"].format(target=target_username))
            schedule_delete(sent_msg, DELAYS["default"])
            return

    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id

    db_user = await user_repo.get_user_data(target_id)
    eco_data = await eco_repo.get_eco_data(target_id)
    game_role = await user_repo.get_user_role(target_id)

    if not db_user or not eco_data:
        sent = await message.answer(LEXICON["profile_not_linked"])
        schedule_delete(sent, DELAYS["short"])
        return

    player_name, db_club_name, _, tg_full_name = db_user
    bs_tag = eco_data.get('bs_tag', '')

    if not bs_tag:
        sent = await message.answer(LEXICON["profile_not_linked"])
        schedule_delete(sent, DELAYS["short"])
        return

    wait_msg = await message.answer(LEXICON["profile_loading"])

    stats = await brawl_client.get_player_stats(bs_tag)
    if not stats:
        return await wait_msg.edit_text(LEXICON["profile_api_error"])

    prefix = f"👤 <b>{player_name}</b>"

    if cmd == "клуб":
        c_name = db_club_name if db_club_name else "Без клуба"
        text = f"{prefix}\n🏰 Клуб: <b>{c_name}</b>\n🔰 Роль: {game_role}"
    elif cmd in ["ранкед", "лига"]:
        rank_val = stats.get('ranked_curr_rank', 0)
        elo = stats.get('ranked_curr_elo', 0)
        text = f"{prefix}\n🎖 Ранкед: <b>{RANK_NAMES.get(rank_val, '🏳️ Без ранга')}</b> ({elo})"
    elif cmd == "кубки":
        trophies = stats.get('trophies', 0)
        text = f"{prefix}\n🏆 Кубки: <b>{trophies}</b>"

    await wait_msg.edit_text(text, link_preview_options=LinkPreviewOptions(is_disabled=True))