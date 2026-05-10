import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from utils.database import get_top_messages, get_top_gain, get_top_absolute
from utils.brawl_api import get_all_club_members

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

class TopCb(CallbackData, prefix="top"):
    act: str
    uid: int

def kb_main_top(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Сообщения", callback_data=TopCb(act="msg", uid=uid).pack())],
        [InlineKeyboardButton(text="📈 Рост кубков", callback_data=TopCb(act="cups_gain", uid=uid).pack())],
        [InlineKeyboardButton(text="🏆 Общие кубки", callback_data=TopCb(act="cups_total", uid=uid).pack())],
        [InlineKeyboardButton(text="🎖 Звания", callback_data=TopCb(act="ranks", uid=uid).pack())],
        [InlineKeyboardButton(text="⚔️ Победы", callback_data=TopCb(act="wins", uid=uid).pack())]
    ])

def kb_timeframe(prefix: str, back: str, uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="День", callback_data=TopCb(act=f"{prefix}_day", uid=uid).pack()),
         InlineKeyboardButton(text="Неделя", callback_data=TopCb(act=f"{prefix}_week", uid=uid).pack())],
        [InlineKeyboardButton(text="Месяц", callback_data=TopCb(act=f"{prefix}_month", uid=uid).pack()),
         InlineKeyboardButton(text="Всё", callback_data=TopCb(act=f"{prefix}_all", uid=uid).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act=back, uid=uid).pack())]
    ])

def kb_ranks(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Актуальные", callback_data=TopCb(act="ranks_curr", uid=uid).pack())],
        [InlineKeyboardButton(text="Рекордные", callback_data=TopCb(act="ranks_high", uid=uid).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="main", uid=uid).pack())]
    ])

def kb_wins(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Всего", callback_data=TopCb(act="wins_tot", uid=uid).pack())],
        [InlineKeyboardButton(text="3 на 3", callback_data=TopCb(act="wins_3v3", uid=uid).pack())],
        [InlineKeyboardButton(text="ШД", callback_data=TopCb(act="wins_sd", uid=uid).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="main", uid=uid).pack())]
    ])

def kb_wins_sd(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Все ШД", callback_data=TopCb(act="wins_sd_tot", uid=uid).pack())],
        [InlineKeyboardButton(text="Соло", callback_data=TopCb(act="wins_sd_solo", uid=uid).pack())],
        [InlineKeyboardButton(text="Дуо", callback_data=TopCb(act="wins_sd_duo", uid=uid).pack())],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="wins", uid=uid).pack())]
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
    await message.answer("📊 <b>Категория:</b>", reply_markup=kb_main_top(message.from_user.id))
    try: await message.delete()
    except: pass

@router.callback_query(TopCb.filter())
async def process_top_callbacks(callback: CallbackQuery, callback_data: TopCb):
    if callback.from_user.id != callback_data.uid:
        await callback.answer("⚠️ Не твое меню", show_alert=True)
        return
    act, uid = callback_data.act, callback_data.uid
    if act == "main": await callback.message.edit_text("📊 <b>Категория:</b>", reply_markup=kb_main_top(uid))
    elif act == "msg": await callback.message.edit_text("💬 <b>Сообщения:</b>", reply_markup=kb_timeframe("msg", "main", uid))
    elif act == "cups_gain": await callback.message.edit_text("📈 <b>Рост кубков:</b>", reply_markup=kb_timeframe("cups_gain", "main", uid))
    elif act == "ranks": await callback.message.edit_text("🎖 <b>Звания:</b>", reply_markup=kb_ranks(uid))
    elif act == "wins": await callback.message.edit_text("⚔️ <b>Победы:</b>", reply_markup=kb_wins(uid))
    elif act == "wins_sd": await callback.message.edit_text("☠️ <b>ШД:</b>", reply_markup=kb_wins_sd(uid))
    elif act == "cups_total":
        await callback.message.edit_text("⏳ Сбор LIVE...")
        from utils.brawl_api import get_all_club_members
        members = await get_all_club_members()
        members.sort(key=lambda x: x.get("trophies", 0), reverse=True)
        res = "🏆 <b>ТОП КУБКОВ</b>\n\n"
        for i, m in enumerate(members[:10]):
            res += f"{i+1}. <b>{m['name']}</b> — {m['trophies']} 🏆\n"
        await callback.message.edit_text(res, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="main", uid=uid).pack())]]))
    else:
        await callback.message.edit_text("⏳ Расчет...")
        back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=TopCb(act="main", uid=uid).pack())]])
        try:
            if act.startswith("msg_"):
                d = {"msg_day": 1, "msg_week": 7, "msg_month": 30, "msg_all": None}[act]
                data = await get_top_messages(d)
                txt = "📊 <b>Топ сообщений</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i+1}. {n} — {v}\n"
                await callback.message.edit_text(txt, reply_markup=back)
            elif act.startswith("cups_gain_"):
                d = {"cups_gain_day": 1, "cups_gain_week": 7, "cups_gain_month": 30, "cups_gain_all": 3650}[act]
                data = await get_top_gain("trophies", d)
                txt = "📈 <b>Рост кубков</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i+1}. {n} — +{v} 🏆\n"
                await callback.message.edit_text(txt, reply_markup=back)
            elif act.startswith("ranks_"):
                col = "rank_current" if act == "ranks_curr" else "rank_highest"
                data = await get_top_absolute(col)
                txt = "🎖 <b>Топ званий</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i+1}. {n} — {v}\n"
                await callback.message.edit_text(txt, reply_markup=back)
            elif act.startswith("wins_"):
                m = {"wins_tot": "solo_wins+duo_wins+wins_3v3", "wins_3v3": "wins_3v3", "wins_sd_tot": "solo_wins+duo_wins", "wins_sd_solo": "solo_wins", "wins_sd_duo": "duo_wins"}
                data = await get_top_absolute(m[act])
                txt = "⚔️ <b>Топ побед</b>\n\n"
                for i, (n, v) in enumerate(data): txt += f"{i+1}. {n} — {v}\n"
                await callback.message.edit_text(txt, reply_markup=back)
        except: await callback.message.edit_text("❌ Ошибка", reply_markup=back)