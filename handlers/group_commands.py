import os
import asyncio
import time
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions, \
    LinkPreviewOptions
from aiogram.filters.callback_data import CallbackData
from utils.brawl_api import get_all_club_members, CLAN_TAGS, get_live_club_detailed_stats, get_clan_names
from utils.database import get_top_messages, get_baseline_trophies, get_top_absolute, get_tag_to_tg_map, \
    get_user_role_by_id, get_top_balance, set_user_role, ROLE_SYMBOLS, DB_NAME, get_all_registered_users

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


class TopCb(CallbackData, prefix="top"):
    act: str
    uid: int
    c: str


sticker_spam_cache = {}


def is_cmd(text: str, cmds: list) -> bool:
    if not text: return False
    t = text.lower().strip()
    return any(t == c or t.startswith(c + " ") for c in cmds)


async def delete_later(message: Message, delay: int = 10800):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass


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


def make_link(display_name: str, tg_name: str, tg_id: int) -> str:
    if tg_name and tg_name.startswith("@"):
        return f"<a href='https://t.me/{tg_name[1:]}'>{display_name}</a>"
    return f"<b>{display_name}</b>"


async def get_roles_bulk(uids: list):
    async def safe_get(uid):
        if not uid: return "Гость"
        try:
            res = await get_user_role_by_id(uid)
            return res if res else "Гость"
        except:
            return "Гость"

    return await asyncio.gather(*(safe_get(uid) for uid in uids))


async def kb_choose_club(uid: int):
    clan_names = await get_clan_names()
    buttons = [
        [InlineKeyboardButton(text="🌐 Всего семейства", callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())]]
    for tag, name in clan_names.items():
        clean = tag.replace("#", "")
        buttons.append(
            [InlineKeyboardButton(text=f"🏰 {name}", callback_data=TopCb(act="cat", uid=uid, c=clean).pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_main_top(uid: int, c: str):
    buttons = []
    if c == "ALL":
        buttons.append([
            InlineKeyboardButton(text="💬 Сообщения", callback_data=TopCb(act="msg", uid=uid, c=c).pack()),
            InlineKeyboardButton(text="💰 Богачи", callback_data=TopCb(act="eco", uid=uid, c=c).pack())
        ])

    buttons.append([
        InlineKeyboardButton(text="📈 Рост кубков", callback_data=TopCb(act="cups_gain", uid=uid, c=c).pack()),
        InlineKeyboardButton(text="🏆 Общие кубки", callback_data=TopCb(act="cups_cur", uid=uid, c=c).pack())
    ])

    buttons.append([
        InlineKeyboardButton(text="⚔️ Победы", callback_data=TopCb(act="wins", uid=uid, c=c).pack()),
        InlineKeyboardButton(text="🎖 Ранкед", callback_data=TopCb(act="ranks_curr", uid=uid, c=c).pack())
    ])

    buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад к клубам", callback_data=TopCb(act="main", uid=uid, c="ALL").pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_timeframe(prefix: str, back: str, uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 День", callback_data=TopCb(act=f"{prefix}_day", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="🗓 Неделя", callback_data=TopCb(act=f"{prefix}_week", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="📆 Месяц", callback_data=TopCb(act=f"{prefix}_month", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="🗃 Все время", callback_data=TopCb(act=f"{prefix}_all", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act=back, uid=uid, c=c).pack())]
    ])


def kb_wins(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ 3 на 3", callback_data=TopCb(act="wins_3v3", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🌵 ШД", callback_data=TopCb(act="wins_sd", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]
    ])


def kb_wins_sd(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Дуо", callback_data=TopCb(act="wins_sd_duo", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="👤 Соло", callback_data=TopCb(act="wins_sd_solo", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="wins", uid=uid, c=c).pack())]
    ])


@router.message(Command("force_scan"))
async def admin_force_scan(message: Message):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or message.from_user.id != int(admin_id): return
    sent_msg = await message.answer("⏳ Собираю данные...")
    asyncio.create_task(delete_later(sent_msg, 60))
    from utils.scheduler import collect_daily_stats
    await collect_daily_stats()
    sent_msg2 = await message.answer("✅ Готово")
    asyncio.create_task(delete_later(sent_msg2, 60))


# 🚀 НОВАЯ КОМАНДА: Вывод списка зарегистрированных
@router.message(Command("all_reg_list"))
async def cmd_all_reg_list(message: Message):
    admin_role = await get_user_role_by_id(message.from_user.id)
    if admin_role not in ["Основатель", "Программист", "Президент", "Вице-президент"]:
        return

    users = await get_all_registered_users()

    if not users:
        sent = await message.answer("📭 Список зарегистрированных пользователей пуст.")
        asyncio.create_task(delete_later(sent, 60))
        return

    lines = ["📋 <b>Список зарегистрированных игроков:</b>\n"]
    for i, (tg_name, tag, player_name) in enumerate(users, 1):
        name_str = tg_name if tg_name.startswith("@") else f"<b>{tg_name}</b>"
        lines.append(f"{i}. {name_str} привязан к тегу {tag} ({player_name})")

    # Телеграм не дает отправить больше 4096 символов, поэтому разбиваем на части
    text = "\n".join(lines)
    for x in range(0, len(text), 4000):
        sent = await message.answer(text[x:x + 4000], parse_mode="HTML",
                                    link_preview_options=LinkPreviewOptions(is_disabled=True))
        asyncio.create_task(delete_later(sent, 10800))

    try:
        await message.delete()
    except:
        pass


@router.message(lambda msg: is_cmd(msg.text, ["понизить", "демоут"]))
async def cmd_demote(message: Message):
    admin_role = await get_user_role_by_id(message.from_user.id)
    if admin_role not in ["Основатель", "Президент"]: return

    parts = message.text.split()
    target_id, target_name = None, None

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = f"@{message.reply_to_message.from_user.username}" if message.reply_to_message.from_user.username else message.reply_to_message.from_user.full_name
    elif len(parts) > 1 and parts[1].startswith("@"):
        target_username = parts[1]
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT user_id FROM tg_profiles WHERE full_name = ? COLLATE NOCASE",
                                  (target_username,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    target_id, target_name = row[0], target_username

    if not target_id:
        sent = await message.answer("❌ Укажите @username или ответьте на сообщение.")
        asyncio.create_task(delete_later(sent, 60))
        return

    await set_user_role(target_id, "Гость", "Отклонен")
    sent = await message.answer(f"⬇️ <b>{target_name}</b> понижен до Гостя и лишен системных полномочий в боте.",
                                parse_mode="HTML")
    asyncio.create_task(delete_later(sent))


@router.message(lambda msg: is_cmd(msg.text, ["вернуть звание", "восстановить", "вернуть"]))
async def cmd_restore_rank(message: Message):
    admin_role = await get_user_role_by_id(message.from_user.id)
    if admin_role not in ["Основатель", "Президент"]: return

    parts = message.text.split()
    target_id, target_name = None, None

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = f"@{message.reply_to_message.from_user.username}" if message.reply_to_message.from_user.username else message.reply_to_message.from_user.full_name
    elif len(parts) > 2 and parts[-1].startswith("@"):
        target_username = parts[-1]
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT user_id FROM tg_profiles WHERE full_name = ? COLLATE NOCASE",
                                  (target_username,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    target_id, target_name = row[0], target_username

    if not target_id:
        sent = await message.answer("❌ Укажите @username или ответьте на сообщение.")
        asyncio.create_task(delete_later(sent, 60))
        return

    await set_user_role(target_id, "Участник", "Одобрен")
    sent = await message.answer(
        f"✅ Полномочия <b>{target_name}</b> восстановлены. Реальное звание из API игры синхронизируется в течение минуты.",
        parse_mode="HTML")
    asyncio.create_task(delete_later(sent))


@router.message(lambda msg: is_cmd(msg.text, ["топ", "top", "топ10", "top10", "топ 10", "top 10"]))
async def cmd_top_trigger(message: Message):
    text = message.text.lower().strip()
    for prefix in ["топ 10", "top 10", "топ10", "top10", "топ", "top"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break

    args_str = text
    uid = message.from_user.id
    c = "ALL"

    try:
        await message.delete()
    except:
        pass

    if not args_str:
        kb = await kb_choose_club(uid)
        sent_msg = await message.answer("📊 <b>Выберите клуб:</b>", reply_markup=kb)
        asyncio.create_task(delete_later(sent_msg))
        return

    args_lower = args_str.lower()
    is_push_direct = False
    push_days = 1
    push_title = "за день"

    if any(word in args_lower for word in
           ["пушеров недели", "пушеров неделя", "пушеры неделя", "пуш неделя", "рост неделя"]):
        is_push_direct = True
        push_days = 7
        push_title = "за неделю"
    elif any(word in args_lower for word in
             ["пушеров месяца", "пушеров месяц", "пушеры месяц", "пуш месяц", "рост месяц"]):
        is_push_direct = True
        push_days = 30
        push_title = "за месяц"
    elif any(word in args_lower for word in ["пушеров", "пушеры", "пуш", "рост кубков", "рост", "ап", "апп"]):
        is_push_direct = True
        push_days = 1
        push_title = "за день"

    if is_push_direct:
        sent_msg = await message.answer("⏳ Собираю актуальные данные...",
                                        link_preview_options=LinkPreviewOptions(is_disabled=True))

        live_members, err = await get_live_club_detailed_stats(c)
        if not live_members:
            await sent_msg.edit_text("❌ Ошибка загрузки данных из API.",
                                     link_preview_options=LinkPreviewOptions(is_disabled=True))
            asyncio.create_task(delete_later(sent_msg, 60))
            return

        tags_filter = [m["tag"] for m in live_members]
        baseline_map = await get_baseline_trophies(push_days, tags_filter)

        results = []
        for m in live_members:
            tag = m["tag"]
            live_cups = m.get("trophies", 0)
            baseline = baseline_map.get(tag, live_cups)
            gain = live_cups - baseline
            if gain > 0:
                results.append((m["name"], gain, tag))

        results.sort(key=lambda x: x[1], reverse=True)
        results = results[:10]

        tg_map = await get_tag_to_tg_map()

        uids = [tg_map.get(tag_str, {}).get("id") for _, _, tag_str in results]
        roles = await get_roles_bulk(uids)

        txt = f"🏆 <b>Топ пушеров ({push_title})</b>\n\n"
        for i, (n, v, tag_str) in enumerate(results):
            tg_data = tg_map.get(tag_str)
            t_uid = tg_data["id"] if tg_data else None
            tg_name = tg_data["name"] if tg_data else None
            u_role = roles[i]
            sym = ROLE_SYMBOLS.get(u_role, "👻")
            name_link = make_link(n, tg_name, t_uid)
            place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
            txt += f"{place} {sym} {name_link}: +{v} 🏆\n"

        if not results:
            txt += "📭 Пока нет данных для расчета (или никто не апнул кубки)."

        back = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К меню топов", callback_data=TopCb(act="main", uid=uid, c="ALL").pack())]
        ])
        await sent_msg.edit_text(txt, reply_markup=back, link_preview_options=LinkPreviewOptions(is_disabled=True))
        asyncio.create_task(delete_later(sent_msg))
        return

    msg_triggers = {"смс", "соо", "сообщение", "сообщения", "sms", "msg", "messages", "чат", "флуд", "писари"}
    wins_triggers = {"победы", "вины", "побед", "wins", "win"}
    cups_triggers = {"общих", "общие", "кубки", "кубков", "общих кубков", "trophies", "cups", "куб"}
    ranks_triggers = {"ранкед", "лига", "ранг", "ranked", "league", "rank", "эло", "elo"}
    eco_triggers = {"феники", "феников", "₣", "f", "эко", "баланс", "богачи", "богачей", "деньги", "phoenix", "balance",
                    "eco", "топ богачей", "топ феников"}

    sent_msg = None

    if args_str in msg_triggers:
        if c != "ALL": return
        sent_msg = await message.answer("💬 <b>Сообщения (Все клубы):</b>",
                                        reply_markup=kb_timeframe("msg", "main", uid, c))
    elif args_str in wins_triggers:
        sent_msg = await message.answer("⚔️ <b>Победы (Все клубы):</b>", reply_markup=kb_wins(uid, c))
    elif args_str in eco_triggers or "top phoenix" in text:
        if c != "ALL": return
        data = await get_top_balance(10)

        uids = [t_uid for _, _, _, t_uid in data]
        roles = await get_roles_bulk(uids)

        txt = "🔥 <b>Топ богачей (₣)</b>\n\n"
        for i, (tg_name, player_name, bal, t_uid) in enumerate(data):
            display_name = player_name if player_name else (tg_name if tg_name else "Игрок")
            u_role = roles[i]
            sym = ROLE_SYMBOLS.get(u_role, "👻")
            name_link = make_link(display_name, tg_name, t_uid)
            place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
            txt += f"{place} {sym} {name_link}: {bal} ₣\n"
        if not data:
            txt += "📭 Пока никого нет."

        back = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())]
        ])
        sent_msg = await message.answer(txt, reply_markup=back,
                                        link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif args_str in cups_triggers:
        sent_msg = await message.answer("⏳ Собираю актуальные данные...")
        members, err = await get_live_club_detailed_stats(c)
        if not members:
            err_msg = f"❌ Ошибка загрузки.\nДетали: {err}" if err else "❌ Ошибка загрузки."
            await sent_msg.edit_text(err_msg, link_preview_options=LinkPreviewOptions(is_disabled=True))
        else:
            members.sort(key=lambda x: x.get("trophies", 0), reverse=True)
            tg_map = await get_tag_to_tg_map()
            top_10 = members[:10]

            uids = [tg_map.get(m["tag"], {}).get("id") for m in top_10]
            roles = await get_roles_bulk(uids)

            res = f"🏆 <b>ТОП КУБКОВ</b>\n\n"
            for i, m in enumerate(top_10):
                tg_data = tg_map.get(m["tag"])
                t_uid = tg_data["id"] if tg_data else None
                tg_name = tg_data["name"] if tg_data else None
                u_role = roles[i]
                sym = ROLE_SYMBOLS.get(u_role, "👻")
                name_link = make_link(m['name'], tg_name, t_uid)
                place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
                res += f"{place} {sym} {name_link}: {m['trophies']}\n"
            await sent_msg.edit_text(res, link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif args_str in ranks_triggers:
        sent_msg = await message.answer("⏳ Собираю актуальные данные...")
        members, err = await get_live_club_detailed_stats(c)
        tg_map = await get_tag_to_tg_map()
        if not members:
            await sent_msg.edit_text("❌ Ошибка.", link_preview_options=LinkPreviewOptions(is_disabled=True))
        else:
            sort_key = lambda x: (x.get("ranked_curr_rank", 0), x.get("ranked_curr_elo", 0))
            members.sort(key=sort_key, reverse=True)
            top_10 = members[:10]

            uids = [tg_map.get(m["tag"], {}).get("id") for m in top_10]
            roles = await get_roles_bulk(uids)

            txt = f"🎖 <b>Ранкед</b>\n\n"
            for i, m in enumerate(top_10):
                tg_data = tg_map.get(m["tag"])
                t_uid = tg_data["id"] if tg_data else None
                tg_name = tg_data["name"] if tg_data else None
                u_role = roles[i]
                sym = ROLE_SYMBOLS.get(u_role, "👻")
                r_val = m.get("ranked_curr_rank", 0)
                e_val = m.get("ranked_curr_elo", 0)
                r_name = get_rank_name(r_val)
                name_link = make_link(m['name'], tg_name, t_uid)
                place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
                txt += f"{place} {sym} {name_link}: {r_name} ({e_val})\n"
            if err: txt += f"\nОшибки: {err}"
            await sent_msg.edit_text(txt, link_preview_options=LinkPreviewOptions(is_disabled=True))
    else:
        kb = await kb_choose_club(uid)
        sent_msg = await message.answer("📊 <b>Выберите клуб:</b>", reply_markup=kb)

    if sent_msg:
        asyncio.create_task(delete_later(sent_msg))


@router.callback_query(TopCb.filter())
async def process_top_callbacks(callback: CallbackQuery, callback_data: TopCb):
    if callback.from_user.id != callback_data.uid:
        await callback.answer("❌ Не твое меню", show_alert=True)
        return
    act, uid, c = callback_data.act, callback_data.uid, callback_data.c

    if act == "main":
        kb = await kb_choose_club(uid)
        await callback.message.edit_text("📊 <b>Выберите клуб:</b>", reply_markup=kb)
    elif act == "cat":
        await callback.message.edit_text("📂 <b>Категория:</b>", reply_markup=kb_main_top(uid, c))
    elif act == "msg":
        if c != "ALL": return
        await callback.message.edit_text("💬 <b>Сообщения:</b>", reply_markup=kb_timeframe("msg", "cat", uid, c))
    elif act == "cups_gain":
        await callback.message.edit_text("📈 <b>Рост кубков:</b>", reply_markup=kb_timeframe("cups_gain", "cat", uid, c))
    elif act == "wins":
        await callback.message.edit_text("⚔️ <b>Победы:</b>", reply_markup=kb_wins(uid, c))
    elif act == "wins_sd":
        await callback.message.edit_text("🌵 <b>Столкновение (ШД):</b>", reply_markup=kb_wins_sd(uid, c))
    elif act == "eco":
        if c != "ALL": return
        await callback.message.edit_text("⏳ Собираю данные...",
                                         link_preview_options=LinkPreviewOptions(is_disabled=True))
        data = await get_top_balance(10)

        uids = [t_uid for _, _, _, t_uid in data]
        roles = await get_roles_bulk(uids)

        txt = "🔥 <b>Топ богачей (₣)</b>\n\n"
        for i, (tg_name, player_name, bal, t_uid) in enumerate(data):
            display_name = player_name if player_name else (tg_name if tg_name else "Игрок")
            u_role = roles[i]
            sym = ROLE_SYMBOLS.get(u_role, "👻")
            name_link = make_link(display_name, tg_name, t_uid)
            place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
            txt += f"{place} {sym} {name_link}: {bal} ₣\n"
        if not data:
            txt += "📭 Пока никого нет."

        back = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())]
        ])
        await callback.message.edit_text(txt, reply_markup=back,
                                         link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif act == "cups_cur":
        await callback.message.edit_text("⏳ Собираю актуальные данные...",
                                         link_preview_options=LinkPreviewOptions(is_disabled=True))
        members, err = await get_live_club_detailed_stats(c)
        if not members:
            err_msg = f"❌ Ошибка загрузки.\nДетали: {err}" if err else "❌ Ошибка загрузки."
            await callback.message.edit_text(err_msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]]),
                                             link_preview_options=LinkPreviewOptions(is_disabled=True))
            return
        members.sort(key=lambda x: x.get("trophies", 0), reverse=True)
        tg_map = await get_tag_to_tg_map()
        top_10 = members[:10]

        uids = [tg_map.get(m["tag"], {}).get("id") for m in top_10]
        roles = await get_roles_bulk(uids)

        res = f"🏆 <b>ТОП КУБКОВ</b>\n\n"
        for i, m in enumerate(top_10):
            tg_data = tg_map.get(m["tag"])
            t_uid = tg_data["id"] if tg_data else None
            tg_name = tg_data["name"] if tg_data else None
            u_role = roles[i]
            sym = ROLE_SYMBOLS.get(u_role, "👻")
            name_link = make_link(m['name'], tg_name, t_uid)
            place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
            res += f"{place} {sym} {name_link}: {m['trophies']}\n"
        await callback.message.edit_text(res, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]]),
                                         link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif act in ["wins_3v3", "wins_sd_solo", "wins_sd_duo", "ranks_curr"]:
        await callback.message.edit_text("⏳ Собираю актуальные данные...",
                                         link_preview_options=LinkPreviewOptions(is_disabled=True))
        members, err = await get_live_club_detailed_stats(c)
        tg_map = await get_tag_to_tg_map()

        if act.startswith("wins_sd_"):
            back_act = "wins_sd"
        elif act.startswith("wins_"):
            back_act = "wins"
        else:
            back_act = "cat"
        back = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act=back_act, uid=uid, c=c).pack())]])

        if not members:
            await callback.message.edit_text("❌ Ошибка", reply_markup=back,
                                             link_preview_options=LinkPreviewOptions(is_disabled=True))
            return

        if act == "ranks_curr":
            sort_key = lambda x: (x.get("ranked_curr_rank", 0), x.get("ranked_curr_elo", 0))
            title = "🎖 Ранкед"
        elif act == "wins_3v3":
            sort_key = lambda x: x.get("wins_3v3", 0)
            title = "⚔️ 3 на 3"
        elif act == "wins_sd_solo":
            sort_key = lambda x: x.get("solo_wins", 0)
            title = "👤 Соло"
        elif act == "wins_sd_duo":
            sort_key = lambda x: x.get("duo_wins", 0)
            title = "👥 Дуо"

        members.sort(key=sort_key, reverse=True)
        top_10 = members[:10]

        uids = [tg_map.get(m["tag"], {}).get("id") for m in top_10]
        roles = await get_roles_bulk(uids)

        txt = f"<b>{title}</b>\n\n"
        for i, m in enumerate(top_10):
            tg_data = tg_map.get(m["tag"])
            t_uid = tg_data["id"] if tg_data else None
            tg_name = tg_data["name"] if tg_data else None
            u_role = roles[i]
            sym = ROLE_SYMBOLS.get(u_role, "👻")
            name_link = make_link(m['name'], tg_name, t_uid)
            place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
            if act == "ranks_curr":
                r_val = m.get("ranked_curr_rank", 0)
                e_val = m.get("ranked_curr_elo", 0)
                r_name = get_rank_name(r_val)
                txt += f"{place} {sym} {name_link}: {r_name} ({e_val})\n"
            else:
                val = sort_key(m)
                txt += f"{place} {sym} {name_link}: {val}\n"
        if err: txt += f"\nОшибки: {err}"
        await callback.message.edit_text(txt, reply_markup=back,
                                         link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif act.startswith("msg_"):
        await callback.message.edit_text("⏳ Собираю данные...",
                                         link_preview_options=LinkPreviewOptions(is_disabled=True))
        d = {"msg_day": 1, "msg_week": 7, "msg_month": 30, "msg_all": None}[act]
        data = await get_top_messages(d)

        uids = [t_uid for _, _, _, t_uid in data]
        roles = await get_roles_bulk(uids)

        txt = "💬 <b>Топ сообщений чата</b>\n\n"
        for i, (tg_name, player_name, v, t_uid) in enumerate(data):
            display_name = player_name if player_name else (tg_name if tg_name else "Игрок")
            u_role = roles[i]
            sym = ROLE_SYMBOLS.get(u_role, "👻")
            name_link = make_link(display_name, tg_name, t_uid)
            place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
            txt += f"{place} {sym} {name_link}: {v}\n"
        await callback.message.edit_text(txt, reply_markup=kb_timeframe("msg", "cat", uid, c),
                                         link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif act.startswith("cups_gain_"):
        d = {"cups_gain_day": 1, "cups_gain_week": 7, "cups_gain_month": 30, "cups_gain_all": 3650}[act]
        await callback.message.edit_text("⏳ Собираю актуальные данные...",
                                         link_preview_options=LinkPreviewOptions(is_disabled=True))

        back = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]])
        try:
            live_members, err = await get_all_club_members(c)
            if not live_members:
                await callback.message.edit_text("❌ Ошибка API", reply_markup=kb_timeframe("cups_gain", "cat", uid, c),
                                                 link_preview_options=LinkPreviewOptions(is_disabled=True))
                return

            tags_filter = [m["tag"] for m in live_members]
            baseline_map = await get_baseline_trophies(d, tags_filter)

            results = []
            for m in live_members:
                tag = m["tag"]
                live_cups = m.get("trophies", 0)
                baseline = baseline_map.get(tag, live_cups)
                gain = live_cups - baseline
                if gain > 0:
                    results.append((m["name"], gain, tag))

            results.sort(key=lambda x: x[1], reverse=True)
            top_10 = results[:10]

            tg_map = await get_tag_to_tg_map()

            uids = [tg_map.get(tag_str, {}).get("id") for _, _, tag_str in top_10]
            roles = await get_roles_bulk(uids)

            txt = "📈 <b>Рост кубков</b>\n\n"
            for i, (n, v, tag_str) in enumerate(top_10):
                tg_data = tg_map.get(tag_str)
                t_uid = tg_data["id"] if tg_data else None
                tg_name = tg_data["name"] if tg_data else None
                u_role = roles[i]
                sym = ROLE_SYMBOLS.get(u_role, "👻")
                name_link = make_link(n, tg_name, t_uid)
                place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
                txt += f"{place} {sym} {name_link}: +{v} 🏆\n"

            if not top_10:
                txt += "📭 Пока нет данных для расчета."

            await callback.message.edit_text(txt, reply_markup=kb_timeframe("cups_gain", "cat", uid, c),
                                             link_preview_options=LinkPreviewOptions(is_disabled=True))
        except Exception as e:
            await callback.message.edit_text("❌ Ошибка вычислений", reply_markup=back,
                                             link_preview_options=LinkPreviewOptions(is_disabled=True))


@router.message(lambda msg: is_cmd(msg.text,
                                   ["мут", "mute", "анмут", "unmute", "размут", "кик", "kick", "бан", "ban", "разбан",
                                    "unban"]))
async def cmd_moderation(message: Message, bot: Bot):
    admin_id = message.from_user.id
    a_role = await get_user_role_by_id(admin_id)

    if a_role not in ["Основатель", "Программист", "Президент", "Вице-президент"]:
        return

    parts = message.text.split()
    if not parts: return

    cmd = parts[0].lower()
    target_id = None
    target_name = None
    idx = 1

    if len(parts) > 1 and parts[idx].startswith("@"):
        target_username = parts[idx]
        idx += 1
        async with aiosqlite.connect(DB_NAME) as db:
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
        sent_msg = await message.answer(
            "❌ Не удалось найти пользователя. Укажите @username (если он есть в базе) или ответьте на его сообщение.")
        asyncio.create_task(delete_later(sent_msg, 60))
        return

    time_str = ""
    dt = None

    if cmd in ["мут", "mute", "бан", "ban"]:
        if idx < len(parts):
            first_word = parts[idx].lower()
            standalone = {
                "минута": (1, "minutes", "1 минуту"), "минуту": (1, "minutes", "1 минуту"),
                "минуты": (1, "minutes", "1 минуту"),
                "час": (1, "hours", "1 час"), "часа": (1, "hours", "1 час"),
                "день": (1, "days", "1 день"), "сутки": (1, "days", "1 день"), "дня": (1, "days", "1 день"),
                "неделя": (1, "weeks", "1 неделю"), "неделю": (1, "weeks", "1 неделю"),
                "недели": (1, "weeks", "1 неделю"),
                "месяц": (30, "days", "1 месяц"), "месяца": (30, "days", "1 месяц"),
                "полгода": (180, "days", "полгода"),
                "год": (365, "days", "1 год"), "года": (365, "days", "1 год"),
                "навсегда": (None, None, "навсегда"), "пермач": (None, None, "навсегда")
            }
            if first_word in standalone:
                val, unit_type, time_str = standalone[first_word]
                dt = timedelta(**{unit_type: val}) if val is not None else None
                idx += 1
            elif first_word.isdigit():
                val = int(first_word)
                idx += 1
                if idx < len(parts):
                    unit_word = parts[idx].lower()
                    matched_unit = True
                    if unit_word.startswith(("мин", "m")):
                        dt = timedelta(minutes=val); time_str = f"{val} минут"
                    elif unit_word.startswith(("час", "h")):
                        dt = timedelta(hours=val); time_str = f"{val} часов"
                    elif unit_word.startswith(("ден", "дн", "сут", "d")):
                        dt = timedelta(days=val); time_str = f"{val} дней"
                    elif unit_word.startswith(("недел", "w")):
                        dt = timedelta(weeks=val); time_str = f"{val} недель"
                    elif unit_word.startswith(("мес", "mo")):
                        dt = timedelta(days=val * 30); time_str = f"{val} месяцев"
                    elif unit_word.startswith(("год", "лет", "y")):
                        dt = timedelta(days=val * 365); time_str = f"{val} лет"
                    else:
                        matched_unit = False
                    if matched_unit:
                        idx += 1
                    else:
                        time_str = f"{val} мин"
                        dt = timedelta(minutes=val)
                else:
                    time_str = f"{val} мин"
                    dt = timedelta(minutes=val)

    if not time_str:
        if cmd in ["мут", "mute"]:
            time_str = "10 минут"; dt = timedelta(minutes=10)
        elif cmd in ["бан", "ban"]:
            time_str = "навсегда"; dt = None

    reason_parts = parts[idx:]
    reason = " ".join(reason_parts) if reason_parts else "Не указана"

    admin_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name

    roles = await get_roles_bulk([message.from_user.id, target_id])
    a_role, t_role = roles[0], roles[1]

    a_sym = ROLE_SYMBOLS.get(a_role, "👻")
    t_sym = ROLE_SYMBOLS.get(t_role, "👻")

    fmt_admin = f"{a_sym} <b>{admin_name}</b>"
    fmt_target = f"{t_sym} <b>{target_name}</b>"

    try:
        if cmd in ["мут", "mute"]:
            until = datetime.now() + dt if dt else None
            await bot.restrict_chat_member(message.chat.id, target_id,
                                           permissions=ChatPermissions(can_send_messages=False), until_date=until)
            action_pub = f"лишен права голоса на {time_str}"
            action_log = f"замутил пользователя {fmt_target} на {time_str}"
            emoji = "🔇"
        elif cmd in ["анмут", "unmute", "размут"]:
            await bot.restrict_chat_member(
                message.chat.id, target_id,
                permissions=ChatPermissions(
                    can_send_messages=True, can_send_audios=True, can_send_documents=True,
                    can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                    can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
                    can_add_web_page_previews=True, can_invite_users=True
                )
            )
            action_pub = "возвращен к полноценному общению"
            action_log = f"размутил пользователя {fmt_target}"
            emoji = "🔊"
        elif cmd in ["кик", "kick"]:
            await bot.ban_chat_member(message.chat.id, target_id)
            await bot.unban_chat_member(message.chat.id, target_id)
            action_pub = "исключен из группы"
            action_log = f"кикнул пользователя {fmt_target}"
            emoji = "👢"
        elif cmd in ["бан", "ban"]:
            until = datetime.now() + dt if dt else None
            await bot.ban_chat_member(message.chat.id, target_id, until_date=until)
            t_str = f" на {time_str}" if time_str != "навсегда" else " навсегда"
            action_pub = f"забанен{t_str}"
            action_log = f"забанил пользователя {fmt_target}{t_str}"
            emoji = "🔨"
        elif cmd in ["разбан", "unban"]:
            await bot.unban_chat_member(message.chat.id, target_id)
            action_pub = "разбанен (может вернуться в группу)"
            action_log = f"разбанил пользователя {fmt_target}"
            emoji = "✅"

        try:
            await message.delete()
        except:
            pass

        if cmd in ["анмут", "unmute", "размут", "разбан", "unban"]:
            pub_text = f"{emoji} Пользователь {fmt_target} был {action_pub} администратором {fmt_admin}."
            log_text = f"Администратор {fmt_admin} {action_log}."
        else:
            pub_text = f"{emoji} Пользователь {fmt_target} был {action_pub} администратором {fmt_admin}.\n📝 Причина: {reason}"
            log_text = f"Администратор {fmt_admin} {action_log}.\nПричина: {reason}."

        pub_msg = await message.answer(pub_text, link_preview_options=LinkPreviewOptions(is_disabled=True))
        asyncio.create_task(delete_later(pub_msg))

        admin_log_chat = os.getenv("ADMIN_ID")
        if admin_log_chat:
            await bot.send_message(admin_log_chat, log_text, link_preview_options=LinkPreviewOptions(is_disabled=True))

    except Exception as e:
        err_msg = await message.answer("❌ Ошибка выполнения: боту не хватает прав или цель имеет иммунитет.",
                                       link_preview_options=LinkPreviewOptions(is_disabled=True))
        asyncio.create_task(delete_later(err_msg, 60))


@router.message(F.sticker)
async def sticker_anti_spam(message: Message, bot: Bot):
    user_id = message.from_user.id
    now = time.time()
    msg_id = message.message_id

    if user_id not in sticker_spam_cache:
        sticker_spam_cache[user_id] = []

    sticker_spam_cache[user_id] = [(t, mid) for t, mid in sticker_spam_cache[user_id] if now - t <= 60.0]
    sticker_spam_cache[user_id].append((now, msg_id))

    recent_count = sum(1 for t, mid in sticker_spam_cache[user_id] if now - t <= 1.0)

    if recent_count > 4:
        until = datetime.now() + timedelta(minutes=10)
        try:
            await bot.restrict_chat_member(
                message.chat.id,
                user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )

            for t, mid in sticker_spam_cache[user_id]:
                try:
                    await bot.delete_message(message.chat.id, mid)
                except:
                    pass

            sticker_spam_cache[user_id] = []

            u_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
            role = await get_user_role_by_id(user_id)
            sym = ROLE_SYMBOLS.get(role, "👻")

            msg = await message.answer(
                f"🔇 Пользователь {sym} {u_name} лишен права голоса на 10 минут.\n📝 Причина: Флуд стикерами.",
                link_preview_options=LinkPreviewOptions(is_disabled=True))
            asyncio.create_task(delete_later(msg))
        except:
            pass