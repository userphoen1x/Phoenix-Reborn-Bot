import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from utils.brawl_api import get_all_club_members, CLAN_TAGS, get_live_club_detailed_stats, get_clan_names
from utils.database import get_top_messages, get_top_gain, get_top_absolute, get_tag_to_tg_map

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


class TopCb(CallbackData, prefix="top"):
    act: str
    uid: int
    c: str


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
        [InlineKeyboardButton(text="Статистика семейства", callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())]]
    for tag, name in clan_names.items():
        clean = tag.replace("#", "")
        buttons.append([InlineKeyboardButton(text=f"{name}", callback_data=TopCb(act="cat", uid=uid, c=clean).pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_main_top(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сообщения", callback_data=TopCb(act="msg", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Рост кубков", callback_data=TopCb(act="cups_gain", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Общие кубки", callback_data=TopCb(act="cups_menu", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Победы", callback_data=TopCb(act="wins", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Ранкед", callback_data=TopCb(act="ranks_curr", uid=uid, c=c).pack())],
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


def kb_cups_type(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Актуальные", callback_data=TopCb(act="cups_cur", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Все", callback_data=TopCb(act="cups_rec", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]
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
    await message.answer("Сбор данных запущен...")
    from utils.scheduler import collect_daily_stats
    await collect_daily_stats()
    await message.answer("Готово")


@router.message(F.text.lower().in_({"топ", "топ 10", "топ10", "top", "top 10", "top10"}))
async def cmd_top_trigger(message: Message):
    kb = await kb_choose_club(message.from_user.id)
    await message.answer("<b>Выберите клуб:</b>", reply_markup=kb)
    try:
        await message.delete()
    except:
        pass


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
    elif act == "cups_menu":
        await callback.message.edit_text("<b>Общие кубки:</b>", reply_markup=kb_cups_type(uid, c))
    elif act == "wins":
        await callback.message.edit_text("<b>Победы:</b>", reply_markup=kb_wins(uid, c))
    elif act == "wins_sd":
        await callback.message.edit_text("<b>Столкновение (ШД):</b>", reply_markup=kb_wins_sd(uid, c))

    elif act == "cups_cur":
        await callback.message.edit_text("Сбор LIVE...")
        members, err = await get_all_club_members(c)
        if not members:
            err_msg = f"Ошибка загрузки.\nДетали: {err}" if err else "Ошибка загрузки."
            await callback.message.edit_text(err_msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data=TopCb(act="cups_menu", uid=uid, c=c).pack())]]))
            return
        members.sort(key=lambda x: x.get("trophies", 0), reverse=True)
        tg_map = await get_tag_to_tg_map()
        res = f"<b>ТОП КУБКОВ (Актуальные)</b>\n\n"
        for i, m in enumerate(members[:10]):
            tg_id = tg_map.get(m["tag"])
            name_link = f'<a href="tg://user?id={tg_id}">{m["name"]}</a>' if tg_id else m["name"]
            res += f"{i + 1}. {name_link} - {m['trophies']}\n"
        await callback.message.edit_text(res, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=TopCb(act="cups_menu", uid=uid, c=c).pack())]]))

    elif act in ["wins_tot", "wins_3v3", "wins_sd_solo", "wins_sd_duo", "ranks_curr"]:
        await callback.message.edit_text("Сбор профилей (10-15 сек)...")
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
            await callback.message.edit_text("Ошибка.", reply_markup=back)
            return

        if act == "ranks_curr":
            sort_key = lambda x: (x.get("ranked_curr_rank", 0), x.get("ranked_curr_elo", 0))
            title = "Ранкед"
        elif act == "wins_tot":
            sort_key = lambda x: x.get("solo_wins", 0) + x.get("duo_wins", 0) + x.get("wins_3v3", 0)
            title = "Всего побед"
        elif act == "wins_3v3":
            sort_key = lambda x: x.get("wins_3v3", 0)
            title = "Победы 3 на 3"
        elif act == "wins_sd_solo":
            sort_key = lambda x: x.get("solo_wins", 0)
            title = "Победы Соло"
        elif act == "wins_sd_duo":
            sort_key = lambda x: x.get("duo_wins", 0)
            title = "Победы Дуо"

        members.sort(key=sort_key, reverse=True)
        txt = f"<b>{title} (LIVE)</b>\n\n"
        for i, m in enumerate(members[:10]):
            tg_id = tg_map.get(m["tag"])
            name_link = f'<a href="tg://user?id={tg_id}">{m["name"]}</a>' if tg_id else m["name"]
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
                data = await get_top_messages(d, tags_filter)
                txt = "<b>Топ сообщений</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i + 1}. {n} - {v}\n"
                await callback.message.edit_text(txt, reply_markup=kb_timeframe("msg", "cat", uid, c))

            elif act.startswith("cups_gain_"):
                d = {"cups_gain_day": 1, "cups_gain_week": 7, "cups_gain_month": 30, "cups_gain_all": 3650}[act]
                data = await get_top_gain("trophies", d, tags_filter)
                txt = "<b>Рост кубков</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i + 1}. {n} - +{v}\n"
                await callback.message.edit_text(txt, reply_markup=kb_timeframe("cups_gain", "cat", uid, c))

            elif act == "cups_rec":
                data = await get_top_absolute("trophies", tags_filter, use_max=True)
                txt = "<b>Топ Общих Кубков (Все время)</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i + 1}. {n} - {v}\n"
                await callback.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data=TopCb(act="cups_menu", uid=uid, c=c).pack())]]))

        except:
            await callback.message.edit_text("Ошибка вычислений", reply_markup=back)


@router.message()
async def message_counter(message: Message):
    if message.text:
        if message.text.lower() not in {"топ", "топ 10", "топ10", "top", "top 10", "top10"}:
            from utils.database import increment_message
            await increment_message(message.from_user.id, message.chat.id)