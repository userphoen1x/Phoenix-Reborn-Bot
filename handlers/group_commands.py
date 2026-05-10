import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from utils.brawl_api import get_all_club_members, CLAN_TAGS, get_live_club_detailed_stats
from utils.database import get_top_messages, get_top_gain, get_top_absolute, get_tag_to_tg_map

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


class TopCb(CallbackData, prefix="top"):
    act: str
    uid: int
    c: str


def get_rank_name(elo: int):
    if elo <= 0: return "Без ранга"
    if elo >= 9000: return "Мастера"

    ranks = ["Бронза", "Серебро", "Золото", "Алмаз", "Мифик", "Легенда"]
    main_idx = min(elo // 1500, 5)
    sub_rank = ((elo % 1500) // 500) + 1
    roman = ["I", "II", "III"][sub_rank - 1]

    return f"{ranks[main_idx]} {roman}"


def kb_choose_club(uid: int):
    buttons = [
        [InlineKeyboardButton(text="🌐 Статистика семейства", callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())]]
    for tag in CLAN_TAGS:
        buttons.append([InlineKeyboardButton(text=f"Клуб {tag}",
                                             callback_data=TopCb(act="cat", uid=uid, c=tag.replace("#", "")).pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_main_top(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Сообщения", callback_data=TopCb(act="msg", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="📈 Рост кубков", callback_data=TopCb(act="cups_gain", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🏆 Кубки (LIVE)", callback_data=TopCb(act="cups_cur", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🎖 Ранкед и Уровень (LIVE)", callback_data=TopCb(act="ranks", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="⚔️ Победы (LIVE)", callback_data=TopCb(act="wins", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="main", uid=uid, c="ALL").pack())]
    ])


def kb_timeframe(prefix: str, back: str, uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="День", callback_data=TopCb(act=f"{prefix}_day", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="Неделя", callback_data=TopCb(act=f"{prefix}_week", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Месяц", callback_data=TopCb(act=f"{prefix}_month", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="Всё", callback_data=TopCb(act=f"{prefix}_all", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act=back, uid=uid, c=c).pack())]
    ])


def kb_ranks(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Текущий Ранкед", callback_data=TopCb(act="ranks_curr", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Рекордный Ранкед", callback_data=TopCb(act="ranks_high", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Уровень (EXP)", callback_data=TopCb(act="ranks_exp", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]
    ])


def kb_wins(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В сумме", callback_data=TopCb(act="wins_tot", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="3 на 3", callback_data=TopCb(act="wins_3v3", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Все Столкновения", callback_data=TopCb(act="wins_sd_tot", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Соло ШД", callback_data=TopCb(act="wins_sd_solo", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Дуо ШД", callback_data=TopCb(act="wins_sd_duo", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]
    ])


@router.message(Command("force_scan"))
async def admin_force_scan(message: Message):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or message.from_user.id != int(admin_id):
        return
    await message.answer("🔄 Сбор данных запущен...")
    from utils.scheduler import collect_daily_stats
    await collect_daily_stats()
    await message.answer("✅ Готово")


@router.message(F.text.lower().in_({"топ", "топ 10", "топ10", "top", "top 10", "top10"}))
async def cmd_top_trigger(message: Message):
    await message.answer("🏢 <b>Выберите клуб:</b>", reply_markup=kb_choose_club(message.from_user.id))
    try:
        await message.delete()
    except:
        pass


@router.callback_query(TopCb.filter())
async def process_top_callbacks(callback: CallbackQuery, callback_data: TopCb):
    if callback.from_user.id != callback_data.uid:
        await callback.answer("⚠️ Не твое меню", show_alert=True)
        return

    act, uid, c = callback_data.act, callback_data.uid, callback_data.c

    if act == "main":
        await callback.message.edit_text("🏢 <b>Выберите клуб:</b>", reply_markup=kb_choose_club(uid))
    elif act == "cat":
        await callback.message.edit_text("📊 <b>Категория:</b>", reply_markup=kb_main_top(uid, c))
    elif act == "msg":
        await callback.message.edit_text("💬 <b>Сообщения:</b>", reply_markup=kb_timeframe("msg", "cat", uid, c))
    elif act == "cups_gain":
        await callback.message.edit_text("📈 <b>Рост кубков:</b>", reply_markup=kb_timeframe("cups_gain", "cat", uid, c))
    elif act == "ranks":
        await callback.message.edit_text("🎖 <b>Ранкед и Уровень:</b>", reply_markup=kb_ranks(uid, c))
    elif act == "wins":
        await callback.message.edit_text("⚔️ <b>Победы:</b>", reply_markup=kb_wins(uid, c))

    elif act == "cups_cur":
        await callback.message.edit_text("⏳ Сбор LIVE...")
        members, err = await get_all_club_members(c)
        if not members:
            await callback.message.edit_text("❌ Ошибка API.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]]))
            return
        members.sort(key=lambda x: x.get("trophies", 0), reverse=True)
        tg_map = await get_tag_to_tg_map()
        res = f"🏆 <b>ТОП КУБКОВ (LIVE)</b>\n\n"
        for i, m in enumerate(members[:10]):
            tg_id = tg_map.get(m["tag"])
            name_link = f'<a href="tg://user?id={tg_id}">{m["name"]}</a>' if tg_id else m["name"]
            res += f"{i + 1}. {name_link} — {m['trophies']} 🏆\n"
        await callback.message.edit_text(res, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]]))

    elif act in ["wins_tot", "wins_3v3", "wins_sd_tot", "wins_sd_solo", "wins_sd_duo", "ranks_curr", "ranks_high",
                 "ranks_exp"]:
        await callback.message.edit_text("⏳ Сбор профилей (10-15 сек)...")
        members, err = await get_live_club_detailed_stats(c)
        tg_map = await get_tag_to_tg_map()
        back = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]])

        if not members:
            await callback.message.edit_text("❌ Ошибка загрузки.", reply_markup=back)
            return

        is_ranked = act in ["ranks_curr", "ranks_high"]

        if act == "ranks_curr":
            sort_key, title = lambda x: x.get("ranked_curr", 0), "Текущий Ранкед"
        elif act == "ranks_high":
            sort_key, title = lambda x: x.get("ranked_high", 0), "Рекордный Ранкед"
        elif act == "ranks_exp":
            sort_key, title = lambda x: x.get("exp_level", 0), "Уровень EXP"
        elif act == "wins_tot":
            sort_key, title = lambda x: x.get("solo_wins", 0) + x.get("duo_wins", 0) + x.get("wins_3v3",
                                                                                             0), "Всего побед"
        elif act == "wins_3v3":
            sort_key, title = lambda x: x.get("wins_3v3", 0), "Победы 3 на 3"
        elif act == "wins_sd_tot":
            sort_key, title = lambda x: x.get("solo_wins", 0) + x.get("duo_wins", 0), "Все Столкновения"
        elif act == "wins_sd_solo":
            sort_key, title = lambda x: x.get("solo_wins", 0), "Победы Соло"
        elif act == "wins_sd_duo":
            sort_key, title = lambda x: x.get("duo_wins", 0), "Победы Дуо"

        members.sort(key=sort_key, reverse=True)
        txt = f"📊 <b>{title} (LIVE)</b>\n\n"

        for i, m in enumerate(members[:10]):
            val = sort_key(m)
            tg_id = tg_map.get(m["tag"])
            name_link = f'<a href="tg://user?id={tg_id}">{m["name"]}</a>' if tg_id else m["name"]

            if is_ranked:
                r_name = get_rank_name(val)
                txt += f"{i + 1}. {name_link} — {r_name} ({val})\n"
            else:
                txt += f"{i + 1}. {name_link} — {val}\n"

        await callback.message.edit_text(txt, reply_markup=back)

    else:
        await callback.message.edit_text("⏳ Расчет...")
        back = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]])
        try:
            tags_filter = None
            if c != "ALL":
                members, err = await get_all_club_members(c)
                tags_filter = [m["tag"] for m in members]

            if act.startswith("msg_"):
                d = {"msg_day": 1, "msg_week": 7, "msg_month": 30, "msg_all": None}[act]
                data = await get_top_messages(d, tags_filter)
                txt = "📊 <b>Топ сообщений</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i + 1}. {n} — {v}\n"
                await callback.message.edit_text(txt, reply_markup=back)
            elif act.startswith("cups_gain_"):
                d = {"cups_gain_day": 1, "cups_gain_week": 7, "cups_gain_month": 30, "cups_gain_all": 3650}[act]
                data = await get_top_gain("trophies", d, tags_filter)
                txt = "📈 <b>Рост кубков</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i + 1}. {n} — +{v} 🏆\n"
                await callback.message.edit_text(txt, reply_markup=back)
        except:
            await callback.message.edit_text("❌ Ошибка", reply_markup=back)