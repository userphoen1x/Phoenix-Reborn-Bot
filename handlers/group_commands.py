import os
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from aiogram.filters.callback_data import CallbackData
from utils.brawl_api import get_all_club_members, CLAN_TAGS, get_live_club_detailed_stats, get_clan_names
from utils.database import get_top_messages, get_top_gain, get_top_absolute, get_tag_to_tg_map, get_user_role_by_id, \
    get_top_balance, ROLE_SYMBOLS

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


class TopCb(CallbackData, prefix="top"):
    act: str
    uid: int
    c: str


async def delete_later(message: Message, delay: int = 86400):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass


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


async def kb_choose_club(uid: int):
    clan_names = await get_clan_names()
    buttons = [
        [InlineKeyboardButton(text="Всего семейства", callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())]]
    for tag, name in clan_names.items():
        clean = tag.replace("#", "")
        buttons.append([InlineKeyboardButton(text=f"{name}", callback_data=TopCb(act="cat", uid=uid, c=clean).pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_main_top(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сообщения", callback_data=TopCb(act="msg", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="Баланс (₣)", callback_data=TopCb(act="eco", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Рост кубков", callback_data=TopCb(act="cups_gain", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="Общие кубки", callback_data=TopCb(act="cups_cur", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Победы", callback_data=TopCb(act="wins", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="Ранкед", callback_data=TopCb(act="ranks_curr", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Назад к клубам", callback_data=TopCb(act="main", uid=uid, c="ALL").pack())]
    ])


def kb_timeframe(prefix: str, back: str, uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="День", callback_data=TopCb(act=f"{prefix}_day", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="Неделя", callback_data=TopCb(act=f"{prefix}_week", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Месяц", callback_data=TopCb(act=f"{prefix}_month", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="Все время", callback_data=TopCb(act=f"{prefix}_all", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Назад", callback_data=TopCb(act=back, uid=uid, c=c).pack())]
    ])


def kb_wins(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В сумме", callback_data=TopCb(act="wins_tot", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="3 на 3", callback_data=TopCb(act="wins_3v3", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="ШД", callback_data=TopCb(act="wins_sd", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]
    ])


def kb_wins_sd(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дуо", callback_data=TopCb(act="wins_sd_duo", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="Соло", callback_data=TopCb(act="wins_sd_solo", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Назад", callback_data=TopCb(act="wins", uid=uid, c=c).pack())]
    ])


@router.message(Command("force_scan"))
async def admin_force_scan(message: Message):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or message.from_user.id != int(admin_id): return
    sent_msg = await message.answer("Сбор данных запущен...")
    asyncio.create_task(delete_later(sent_msg))
    from utils.scheduler import collect_daily_stats
    await collect_daily_stats()
    sent_msg2 = await message.answer("Готово")
    asyncio.create_task(delete_later(sent_msg2))


@router.message(lambda msg: msg.text and msg.text.lower().startswith(("топ", "top")))
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
        sent_msg = await message.answer("<b>Выберите клуб:</b>", reply_markup=kb)
        asyncio.create_task(delete_later(sent_msg))
        return

    msg_triggers = {"смс", "соо", "сообщение", "сообщения", "sms", "msg", "messages", "чат", "флуд", "писари"}
    gain_triggers = {"рост", "пушеры", "пуш", "рост кубков", "gain", "push", "pushers", "ап", "апп"}
    wins_triggers = {"победы", "вины", "побед", "wins", "win"}
    cups_triggers = {"общих", "общие", "кубки", "кубков", "общих кубков", "trophies", "cups", "куб"}
    ranks_triggers = {"ранкед", "лига", "ранг", "ranked", "league", "rank", "эло", "elo"}
    eco_triggers = {"феники", "феников", "₣", "f", "эко", "баланс", "богачи", "деньги", "phoenix", "balance", "eco"}

    sent_msg = None

    if args_str in msg_triggers:
        sent_msg = await message.answer("<b>Сообщения (Все клубы):</b>",
                                        reply_markup=kb_timeframe("msg", "main", uid, c))
    elif args_str in gain_triggers:
        sent_msg = await message.answer("<b>Рост кубков (Все клубы):</b>",
                                        reply_markup=kb_timeframe("cups_gain", "main", uid, c))
    elif args_str in wins_triggers:
        sent_msg = await message.answer("<b>Победы (Все клубы):</b>", reply_markup=kb_wins(uid, c))
    elif args_str in eco_triggers or "top phoenix" in text:
        data = await get_top_balance(10)
        txt = "<b>Топ богачей (₣)</b>\n\n"
        for i, (name, bal, t_uid) in enumerate(data):
            u_role = await get_user_role_by_id(t_uid) if t_uid else "Гость"
            sym = ROLE_SYMBOLS.get(u_role, "○")
            name_link = f"<a href='tg://user?id={t_uid}'>{name}</a>" if t_uid else name
            txt += f"{i + 1}. {sym} {name_link} - {bal} ₣\n"
        if not data:
            txt += "Пока никого нет."

        back = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())]
        ])
        sent_msg = await message.answer(txt, reply_markup=back)
    elif args_str in cups_triggers:
        sent_msg = await message.answer("Сбор данных...")
        members, err = await get_all_club_members(c)
        if not members:
            err_msg = f"Ошибка загрузки.\nДетали: {err}" if err else "Ошибка загрузки."
            await sent_msg.edit_text(err_msg)
        else:
            members.sort(key=lambda x: x.get("trophies", 0), reverse=True)
            tg_map = await get_tag_to_tg_map()
            res = f"<b>ТОП КУБКОВ</b>\n\n"
            for i, m in enumerate(members[:10]):
                tg_id = tg_map.get(m["tag"])
                u_role = await get_user_role_by_id(tg_id) if tg_id else "Гость"
                sym = ROLE_SYMBOLS.get(u_role, "○")
                name_link = f"{sym} <a href='tg://user?id={tg_id}'>{m['name']}</a>" if tg_id else f"{sym} {m['name']}"
                res += f"{i + 1}. {name_link} - {m['trophies']}\n"
            await sent_msg.edit_text(res)
    elif args_str in ranks_triggers:
        sent_msg = await message.answer("Сбор профилей...")
        members, err = await get_live_club_detailed_stats(c)
        tg_map = await get_tag_to_tg_map()
        if not members:
            await sent_msg.edit_text("Ошибка.")
        else:
            sort_key = lambda x: (x.get("ranked_curr_rank", 0), x.get("ranked_curr_elo", 0))
            members.sort(key=sort_key, reverse=True)
            txt = f"<b>Ранкед</b>\n\n"
            for i, m in enumerate(members[:10]):
                tg_id = tg_map.get(m["tag"])
                u_role = await get_user_role_by_id(tg_id) if tg_id else "Гость"
                sym = ROLE_SYMBOLS.get(u_role, "○")
                name_link = f"{sym} <a href='tg://user?id={tg_id}'>{m['name']}</a>" if tg_id else f"{sym} {m['name']}"
                r_val = m.get("ranked_curr_rank", 0)
                e_val = m.get("ranked_curr_elo", 0)
                r_name = get_rank_name(r_val)
                txt += f"{i + 1}. {name_link} - {r_name} ({e_val})\n"
            if err: txt += f"\nОшибки: {err}"
            await sent_msg.edit_text(txt)
    else:
        kb = await kb_choose_club(uid)
        sent_msg = await message.answer("<b>Выберите клуб:</b>", reply_markup=kb)

    if sent_msg:
        asyncio.create_task(delete_later(sent_msg))


@router.callback_query(TopCb.filter())
async def process_top_callbacks(callback: CallbackQuery, callback_data: TopCb):
    if callback.from_user.id != callback_data.uid:
        await callback.answer("Не твое меню", show_alert=True)
        return
    act, uid, c = callback_data.act, callback_data.uid, callback_data.c

    if act == "main":
        kb = await kb_choose_club(uid)
        await callback.message.edit_text("<b>Выберите клуб:</b>", reply_markup=kb)
    elif act == "cat":
        await callback.message.edit_text("<b>Категория:</b>", reply_markup=kb_main_top(uid, c))
    elif act == "msg":
        await callback.message.edit_text("<b>Сообщения:</b>", reply_markup=kb_timeframe("msg", "cat", uid, c))
    elif act == "cups_gain":
        await callback.message.edit_text("<b>Рост кубков:</b>", reply_markup=kb_timeframe("cups_gain", "cat", uid, c))
    elif act == "wins":
        await callback.message.edit_text("<b>Победы:</b>", reply_markup=kb_wins(uid, c))
    elif act == "wins_sd":
        await callback.message.edit_text("<b>Столкновение (ШД):</b>", reply_markup=kb_wins_sd(uid, c))
    elif act == "eco":
        await callback.message.edit_text("Расчет...")
        data = await get_top_balance(10)
        txt = "<b>Топ богачей (₣)</b>\n\n"
        for i, (name, bal, t_uid) in enumerate(data):
            u_role = await get_user_role_by_id(t_uid) if t_uid else "Гость"
            sym = ROLE_SYMBOLS.get(u_role, "○")
            name_link = f"<a href='tg://user?id={t_uid}'>{name}</a>" if t_uid else name
            txt += f"{i + 1}. {sym} {name_link} - {bal} ₣\n"
        if not data:
            txt += "Пока никого нет."

        back = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]
        ])
        await callback.message.edit_text(txt, reply_markup=back)
    elif act == "cups_cur":
        await callback.message.edit_text("Сбор данных...")
        members, err = await get_all_club_members(c)
        if not members:
            err_msg = f"Ошибка загрузки.\nДетали: {err}" if err else "Ошибка загрузки."
            await callback.message.edit_text(err_msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]]))
            return
        members.sort(key=lambda x: x.get("trophies", 0), reverse=True)
        tg_map = await get_tag_to_tg_map()
        res = f"<b>ТОП КУБКОВ</b>\n\n"
        for i, m in enumerate(members[:10]):
            tg_id = tg_map.get(m["tag"])
            u_role = await get_user_role_by_id(tg_id) if tg_id else "Гость"
            sym = ROLE_SYMBOLS.get(u_role, "○")
            name_link = f"{sym} <a href='tg://user?id={tg_id}'>{m['name']}</a>" if tg_id else f"{sym} {m['name']}"
            res += f"{i + 1}. {name_link} - {m['trophies']}\n"
        await callback.message.edit_text(res, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]]))
    elif act in ["wins_tot", "wins_3v3", "wins_sd_solo", "wins_sd_duo", "ranks_curr"]:
        await callback.message.edit_text("Сбор профилей...")
        members, err = await get_live_club_detailed_stats(c)
        tg_map = await get_tag_to_tg_map()

        if act.startswith("wins_sd_"):
            back_act = "wins_sd"
        elif act.startswith("wins_"):
            back_act = "wins"
        else:
            back_act = "cat"
        back = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=TopCb(act=back_act, uid=uid, c=c).pack())]])

        if not members:
            await callback.message.edit_text("Ошибка", reply_markup=back)
            return

        if act == "ranks_curr":
            sort_key = lambda x: (x.get("ranked_curr_rank", 0), x.get("ranked_curr_elo", 0))
            title = "Ранкед"
        elif act == "wins_tot":
            sort_key = lambda x: x.get("solo_wins", 0) + x.get("duo_wins", 0) + x.get("wins_3v3", 0)
            title = "В сумме"
        elif act == "wins_3v3":
            sort_key = lambda x: x.get("wins_3v3", 0)
            title = "3 на 3"
        elif act == "wins_sd_solo":
            sort_key = lambda x: x.get("solo_wins", 0)
            title = "Соло"
        elif act == "wins_sd_duo":
            sort_key = lambda x: x.get("duo_wins", 0)
            title = "Дуо"

        members.sort(key=sort_key, reverse=True)
        txt = f"<b>{title}</b>\n\n"
        for i, m in enumerate(members[:10]):
            tg_id = tg_map.get(m["tag"])
            u_role = await get_user_role_by_id(tg_id) if tg_id else "Гость"
            sym = ROLE_SYMBOLS.get(u_role, "○")
            name_link = f"{sym} <a href='tg://user?id={tg_id}'>{m['name']}</a>" if tg_id else f"{sym} {m['name']}"
            if act == "ranks_curr":
                r_val = m.get("ranked_curr_rank", 0)
                e_val = m.get("ranked_curr_elo", 0)
                r_name = get_rank_name(r_val)
                txt += f"{i + 1}. {name_link} - {r_name} ({e_val})\n"
            else:
                val = sort_key(m)
                txt += f"{i + 1}. {name_link} - {val}\n"
        if err: txt += f"\nОшибки: {err}"
        await callback.message.edit_text(txt, reply_markup=back)
    else:
        await callback.message.edit_text("Расчет...")
        back = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]])
        try:
            tags_filter = None
            if c != "ALL":
                members, err = await get_all_club_members(c)
                tags_filter = [m["tag"] for m in members]

            if act.startswith("msg_"):
                d = {"msg_day": 1, "msg_week": 7, "msg_month": 30, "msg_all": None}[act]
                data = await get_top_messages(d)
                txt = "<b>Топ сообщений чата</b>\n\n"
                for i, (n, v, t_uid) in enumerate(data):
                    u_role = await get_user_role_by_id(t_uid)
                    sym = ROLE_SYMBOLS.get(u_role, "○")
                    name_link = f"<a href='tg://user?id={t_uid}'>{n}</a>" if t_uid else n
                    txt += f"{i + 1}. {sym} {name_link} ({v})\n"
                await callback.message.edit_text(txt, reply_markup=kb_timeframe("msg", "cat", uid, c))
            elif act.startswith("cups_gain_"):
                d = {"cups_gain_day": 1, "cups_gain_week": 7, "cups_gain_month": 30, "cups_gain_all": 3650}[act]
                data = await get_top_gain("trophies", d, tags_filter)
                tg_map = await get_tag_to_tg_map()
                txt = "<b>Рост кубков</b>\n\n"
                for i, (n, v, tag_str) in enumerate(data):
                    tg_id = tg_map.get(tag_str)
                    u_role = await get_user_role_by_id(tg_id) if tg_id else "Гость"
                    sym = ROLE_SYMBOLS.get(u_role, "○")
                    name_link = f"<a href='tg://user?id={tg_id}'>{n}</a>" if tg_id else n
                    txt += f"{i + 1}. {sym} {name_link} - +{v}\n"
                await callback.message.edit_text(txt, reply_markup=kb_timeframe("cups_gain", "cat", uid, c))
        except:
            await callback.message.edit_text("Ошибка вычислений", reply_markup=back)


@router.message(lambda msg: msg.text and msg.text.lower().startswith(
    ("мут", "mute", "анмут", "unmute", "кик", "kick", "бан", "ban")))
async def cmd_moderation(message: Message, bot: Bot):
    admin_id = message.from_user.id
    a_role = await get_user_role_by_id(admin_id)

    if a_role not in ["Основатель", "Программист", "Президент", "Вице-президент"]:
        return

    parts = message.text.split()
    if not parts:
        return

    cmd = parts[0].lower()
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
        sent_msg = await message.answer(
            "Не удалось найти пользователя. Укажите @username (если он есть в базе) или ответьте на его сообщение.")
        asyncio.create_task(delete_later(sent_msg, 10))
        return

    time_str = ""
    dt = None

    if cmd in ["мут", "mute", "бан", "ban"]:
        if idx < len(parts):
            val_str = parts[idx].lower()
            if val_str in ["навсегда", "пермач", "forever"]:
                time_str = "навсегда"
                dt = None
                idx += 1
            elif val_str == "полгода":
                time_str = "полгода"
                dt = timedelta(days=180)
                idx += 1
            elif val_str.isdigit():
                val = int(val_str)
                idx += 1
                if idx < len(parts):
                    unit = parts[idx].lower()
                    idx += 1
                    time_str = f"{val} {unit}"
                    if unit.startswith(("мин", "m")):
                        dt = timedelta(minutes=val)
                    elif unit.startswith(("час", "h")):
                        dt = timedelta(hours=val)
                    elif unit.startswith(("ден", "дн", "d")):
                        dt = timedelta(days=val)
                    elif unit.startswith(("недел", "w")):
                        dt = timedelta(weeks=val)
                    elif unit.startswith(("мес", "mo")):
                        dt = timedelta(days=val * 30)
                    elif unit.startswith(("год", "лет", "y")):
                        dt = timedelta(days=val * 365)
                    else:
                        time_str = ""
                        idx -= 2

    if not time_str and cmd in ["мут", "mute"]:
        time_str = "навсегда"

    reason_parts = parts[idx:]
    reason = " ".join(reason_parts) if reason_parts else "Не указана"

    admin_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name

    t_role = await get_user_role_by_id(target_id)
    a_sym = ROLE_SYMBOLS.get(a_role, "○")
    t_sym = ROLE_SYMBOLS.get(t_role, "○")

    fmt_admin = f"{a_sym} {admin_name}"
    fmt_target = f"{t_sym} {target_name}"

    try:
        if cmd in ["мут", "mute"]:
            until = datetime.now() + dt if dt else None
            await bot.restrict_chat_member(message.chat.id, target_id,
                                           permissions=ChatPermissions(can_send_messages=False), until_date=until)
            action_pub = f"лишен права голоса на {time_str}"
            action_log = f"замутил пользователя {fmt_target} на {time_str}"
        elif cmd in ["анмут", "unmute"]:
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
        elif cmd in ["кик", "kick"]:
            await bot.ban_chat_member(message.chat.id, target_id)
            await bot.unban_chat_member(message.chat.id, target_id)
            action_pub = "исключен из группы"
            action_log = f"кикнул пользователя {fmt_target}"
        elif cmd in ["бан", "ban"]:
            until = datetime.now() + dt if dt else None
            await bot.ban_chat_member(message.chat.id, target_id, until_date=until)
            t_str = f" на {time_str}" if time_str else " навсегда"
            action_pub = f"забанен{t_str}"
            action_log = f"забанил пользователя {fmt_target}{t_str}"

        try:
            await message.delete()
        except:
            pass

        if cmd in ["анмут", "unmute"]:
            pub_text = f"Пользователь {fmt_target} был {action_pub} администратором {fmt_admin}."
            log_text = f"Администратор {fmt_admin} {action_log}."
        else:
            pub_text = f"Пользователь {fmt_target} был {action_pub} администратором {fmt_admin}.\nПричина: {reason}"
            log_text = f"Администратор {fmt_admin} {action_log}.\nПричина: {reason}."

        pub_msg = await message.answer(pub_text)
        asyncio.create_task(delete_later(pub_msg))

        admin_log_chat = os.getenv("ADMIN_ID")
        if admin_log_chat:
            await bot.send_message(admin_log_chat, log_text)

    except Exception as e:
        err_msg = await message.answer("Ошибка выполнения: боту не хватает прав или цель имеет иммунитет.")
        asyncio.create_task(delete_later(err_msg, 10))


@router.message(lambda msg: msg.text and msg.text.lower().startswith(
    ("мут", "mute", "анмут", "unmute", "кик", "kick", "бан", "ban")))
async def cmd_moderation(message: Message, bot: Bot):
    admin_id = message.from_user.id
    a_role = await get_user_role_by_id(admin_id)

    if a_role not in ["Основатель", "Программист", "Президент", "Вице-президент"]:
        return

    parts = message.text.split()
    if not parts:
        return

    cmd = parts[0].lower()
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
        sent_msg = await message.answer(
            "Не удалось найти пользователя. Укажите @username (если он есть в базе) или ответьте на его сообщение.")
        asyncio.create_task(delete_later(sent_msg, 10))
        return

    time_str = ""
    dt = None

    if cmd in ["мут", "mute", "бан", "ban"]:
        if idx < len(parts):
            val_str = parts[idx].lower()

            word_durations = {
                "навсегда": (None, "навсегда"),
                "пермач": (None, "навсегда"),
                "forever": (None, "навсегда"),
                "минута": (timedelta(minutes=1), "1 минуту"),
                "минуту": (timedelta(minutes=1), "1 минуту"),
                "час": (timedelta(hours=1), "1 час"),
                "день": (timedelta(days=1), "1 день"),
                "сутки": (timedelta(days=1), "1 день"),
                "неделя": (timedelta(weeks=1), "1 неделю"),
                "неделю": (timedelta(weeks=1), "1 неделю"),
                "месяц": (timedelta(days=30), "1 месяц"),
                "полгода": (timedelta(days=180), "полгода"),
                "год": (timedelta(days=365), "1 год")
            }

            if val_str in word_durations:
                dt, time_str = word_durations[val_str]
                idx += 1
            elif val_str.isdigit():
                val = int(val_str)
                idx += 1
                if idx < len(parts):
                    unit = parts[idx].lower()
                    idx += 1
                    time_str = f"{val} {unit}"
                    if unit.startswith(("мин", "m")):
                        dt = timedelta(minutes=val)
                    elif unit.startswith(("час", "h")):
                        dt = timedelta(hours=val)
                    elif unit.startswith(("ден", "дн", "сут", "d")):
                        dt = timedelta(days=val)
                    elif unit.startswith(("недел", "w")):
                        dt = timedelta(weeks=val)
                    elif unit.startswith(("мес", "mo")):
                        dt = timedelta(days=val * 30)
                    elif unit.startswith(("год", "лет", "y")):
                        dt = timedelta(days=val * 365)
                    else:
                        time_str = ""
                        idx -= 2

    if not time_str:
        if cmd in ["мут", "mute"]:
            time_str = "10 минут"
            dt = timedelta(minutes=10)
        elif cmd in ["бан", "ban"]:
            time_str = "навсегда"
            dt = None

    reason_parts = parts[idx:]
    reason = " ".join(reason_parts) if reason_parts else "Не указана"

    admin_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name

    t_role = await get_user_role_by_id(target_id)
    a_sym = ROLE_SYMBOLS.get(a_role, "○")
    t_sym = ROLE_SYMBOLS.get(t_role, "○")

    fmt_admin = f"{a_sym} {admin_name}"
    fmt_target = f"{t_sym} {target_name}"

    try:
        if cmd in ["мут", "mute"]:
            until = datetime.now() + dt if dt else None
            await bot.restrict_chat_member(message.chat.id, target_id,
                                           permissions=ChatPermissions(can_send_messages=False), until_date=until)
            action_pub = f"лишен права голоса на {time_str}"
            action_log = f"замутил пользователя {fmt_target} на {time_str}"
        elif cmd in ["анмут", "unmute"]:
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
        elif cmd in ["кик", "kick"]:
            await bot.ban_chat_member(message.chat.id, target_id)
            await bot.unban_chat_member(message.chat.id, target_id)
            action_pub = "исключен из группы"
            action_log = f"кикнул пользователя {fmt_target}"
        elif cmd in ["бан", "ban"]:
            until = datetime.now() + dt if dt else None
            await bot.ban_chat_member(message.chat.id, target_id, until_date=until)
            t_str = f" на {time_str}" if time_str != "навсегда" else " навсегда"
            action_pub = f"забанен{t_str}"
            action_log = f"забанил пользователя {fmt_target}{t_str}"

        try:
            await message.delete()
        except:
            pass

        if cmd in ["анмут", "unmute"]:
            pub_text = f"Пользователь {fmt_target} был {action_pub} администратором {fmt_admin}."
            log_text = f"Администратор {fmt_admin} {action_log}."
        else:
            pub_text = f"Пользователь {fmt_target} был {action_pub} администратором {fmt_admin}.\nПричина: {reason}"
            log_text = f"Администратор {fmt_admin} {action_log}.\nПричина: {reason}."

        pub_msg = await message.answer(pub_text)
        asyncio.create_task(delete_later(pub_msg))

        admin_log_chat = os.getenv("ADMIN_ID")
        if admin_log_chat:
            await bot.send_message(admin_log_chat, log_text)

    except Exception as e:
        err_msg = await message.answer("Ошибка выполнения: боту не хватает прав или цель имеет иммунитет.")
        asyncio.create_task(delete_later(err_msg, 10))