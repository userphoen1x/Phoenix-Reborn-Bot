import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from utils.database import get_top_messages, get_top_gain, get_top_absolute
from utils.brawl_api import get_all_club_members, CLAN_TAGS

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


class TopCb(CallbackData, prefix="top"):
    act: str
    uid: int
    c: str


def kb_choose_club(uid: int):
    buttons = []
    buttons.append([InlineKeyboardButton(text="🌐 Общая статистика семейства",
                                         callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())])
    for tag in CLAN_TAGS:
        clean = tag.replace("#", "")
        buttons.append(
            [InlineKeyboardButton(text=f"Клуб {tag}", callback_data=TopCb(act="cat", uid=uid, c=clean).pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_main_top(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Сообщения", callback_data=TopCb(act="msg", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="📈 Рост кубков", callback_data=TopCb(act="cups_gain", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🏆 Общие кубки", callback_data=TopCb(act="cups_menu", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🎖 Звания", callback_data=TopCb(act="ranks", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="⚔️ Победы", callback_data=TopCb(act="wins", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🔙 Назад к клубам", callback_data=TopCb(act="main", uid=uid, c="ALL").pack())]
    ])


def kb_timeframe(prefix: str, back: str, uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="День", callback_data=TopCb(act=f"{prefix}_day", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="Неделя", callback_data=TopCb(act=f"{prefix}_week", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Месяц", callback_data=TopCb(act=f"{prefix}_month", uid=uid, c=c).pack()),
         InlineKeyboardButton(text="Всё", callback_data=TopCb(act=f"{prefix}_all", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act=back, uid=uid, c=c).pack())]
    ])


def kb_cups_type(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ Текущие (LIVE)", callback_data=TopCb(act="cups_cur", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🌟 Рекордные (База)", callback_data=TopCb(act="cups_rec", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]
    ])


def kb_ranks(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Актуальные", callback_data=TopCb(act="ranks_curr", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Рекордные", callback_data=TopCb(act="ranks_high", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]
    ])


def kb_wins(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Всего", callback_data=TopCb(act="wins_tot", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="3 на 3", callback_data=TopCb(act="wins_3v3", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="ШД", callback_data=TopCb(act="wins_sd", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]
    ])


def kb_wins_sd(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Все ШД", callback_data=TopCb(act="wins_sd_tot", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Соло", callback_data=TopCb(act="wins_sd_solo", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="Дуо", callback_data=TopCb(act="wins_sd_duo", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="wins", uid=uid, c=c).pack())]
    ])


@router.message(Command("force_scan"))
async def admin_force_scan(message: Message):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or message.from_user.id != int(admin_id):
        return
    await message.answer("🔄 Сбор данных...")
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
    elif act == "cups_menu":
        await callback.message.edit_text("🏆 <b>Тип кубков:</b>", reply_markup=kb_cups_type(uid, c))
    elif act == "ranks":
        await callback.message.edit_text("🎖 <b>Звания:</b>", reply_markup=kb_ranks(uid, c))
    elif act == "wins":
        await callback.message.edit_text("⚔️ <b>Победы:</b>", reply_markup=kb_wins(uid, c))
    elif act == "wins_sd":
        await callback.message.edit_text("☠️ <b>ШД:</b>", reply_markup=kb_wins_sd(uid, c))

    elif act == "cups_cur":
        await callback.message.edit_text("⏳ Сбор LIVE...")
        members = await get_all_club_members(c)
        if not members:
            await callback.message.edit_text("❌ Ошибка связи с API.", reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cups_menu", uid=uid, c=c).pack())]]))
            return
        members.sort(key=lambda x: x.get("trophies", 0), reverse=True)
        res = f"🏆 <b>ТОП КУБКОВ (Текущие)</b>\n\n"
        for i, m in enumerate(members[:10]):
            res += f"{i + 1}. <b>{m['name']}</b> — {m['trophies']} 🏆\n"
        await callback.message.edit_text(res, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cups_menu", uid=uid, c=c).pack())]]))

    else:
        await callback.message.edit_text("⏳ Расчет...")
        back = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]])
        try:
            tags_filter = None
            if c != "ALL":
                members = await get_all_club_members(c)
                tags_filter = [m["tag"] for m in members]
                if not tags_filter:
                    await callback.message.edit_text("❌ Нет данных о клубе или ошибка API.", reply_markup=back)
                    return

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

            elif act == "cups_rec":
                data = await get_top_absolute("rank_highest", tags_filter)
                txt = "🌟 <b>Топ Рекордных Кубков</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i + 1}. {n} — {v} 🏆\n"
                await callback.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="cups_menu", uid=uid, c=c).pack())]]))

            elif act.startswith("ranks_"):
                col = "rank_current" if act == "ranks_curr" else "rank_highest"
                data = await get_top_absolute(col, tags_filter)
                txt = "🎖 <b>Топ званий</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i + 1}. {n} — {v}\n"
                await callback.message.edit_text(txt, reply_markup=back)

            elif act.startswith("wins_"):
                m = {"wins_tot": "solo_wins+duo_wins+wins_3v3", "wins_3v3": "wins_3v3",
                     "wins_sd_tot": "solo_wins+duo_wins", "wins_sd_solo": "solo_wins", "wins_sd_duo": "duo_wins"}
                data = await get_top_absolute(m[act], tags_filter)
                txt = "⚔️ <b>Топ побед</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i + 1}. {n} — {v}\n"
                await callback.message.edit_text(txt, reply_markup=back)
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка вычислений", reply_markup=back)


@router.message()
async def message_counter(message: Message):
    if message.text:
        if message.text.lower() not in {"топ", "топ 10", "топ10", "top", "top 10", "top10"}:
            from utils.database import increment_message
            await increment_message(message.from_user.id, message.chat.id)