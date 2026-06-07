import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.filters.callback_data import CallbackData
from database.repositories.user_repo import UserRepository
from database.repositories.chat_repo import ChatRepository
from database.repositories.economy_repo import EconomyRepository
from external.brawl_api import BrawlAPIClient
from core.config import settings
from core.constants import ROLE_SYMBOLS, RANK_NAMES

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

class TopCb(CallbackData, prefix="top"):
    act: str
    uid: int
    c: str

def is_cmd(text: str, cmds: list) -> bool:
    if not text: return False
    t = text.lower().strip()
    return any(t == c or t.startswith(c + " ") for c in cmds)

async def delete_later(message: Message, delay: int = 10800):
    await asyncio.sleep(delay)
    try: await message.delete()
    except: pass

def make_link(display_name: str, tg_name: str, tg_id: int) -> str:
    if tg_name and tg_name.startswith("@"): return f"<a href='https://t.me/{tg_name[1:]}'>{display_name}</a>"
    return f"<b>{display_name}</b>"

async def get_roles_bulk(uids: list, user_repo: UserRepository):
    async def safe_get(uid):
        if not uid: return "🗣️"
        try:
            game_role = await user_repo.get_user_role(uid)
            syms = ""
            if str(uid) == settings.FOUNDER_ID: syms += ROLE_SYMBOLS.get("Лидер", "👑")
            if str(uid) in settings.DEVELOPER_IDS: syms += ROLE_SYMBOLS.get("Разработчик", "🧑🏻‍💻")
            syms += ROLE_SYMBOLS.get(game_role, "🗣️")
            return syms
        except: return "🗣️"
    return await asyncio.gather(*(safe_get(uid) for uid in uids))

async def kb_choose_club(uid: int, brawl_client: BrawlAPIClient):
    clan_names = await brawl_client.get_clan_names()
    buttons = [[InlineKeyboardButton(text="🌐 Всего семейства", callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())]]
    for tag, name in clan_names.items():
        clean = tag.replace("#", "")
        buttons.append([InlineKeyboardButton(text=f"🏰 {name}", callback_data=TopCb(act="cat", uid=uid, c=clean).pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_main_top(uid: int, c: str):
    buttons = []
    if c == "ALL": buttons.append([InlineKeyboardButton(text="💬 Сообщения", callback_data=TopCb(act="msg", uid=uid, c=c).pack()), InlineKeyboardButton(text="💰 Богачи", callback_data=TopCb(act="eco", uid=uid, c=c).pack())])
    buttons.append([InlineKeyboardButton(text="📈 Рост кубков", callback_data=TopCb(act="cups_gain", uid=uid, c=c).pack()), InlineKeyboardButton(text="🏆 Общие кубки", callback_data=TopCb(act="cups_cur", uid=uid, c=c).pack())])
    buttons.append([InlineKeyboardButton(text="⚔️ Победы", callback_data=TopCb(act="wins", uid=uid, c=c).pack()), InlineKeyboardButton(text="🎖 Ранкед", callback_data=TopCb(act="ranks_curr", uid=uid, c=c).pack())])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к клубам", callback_data=TopCb(act="main", uid=uid, c="ALL").pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_timeframe(prefix: str, back: str, uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 День", callback_data=TopCb(act=f"{prefix}_day", uid=uid, c=c).pack()), InlineKeyboardButton(text="🗓 Неделя", callback_data=TopCb(act=f"{prefix}_week", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="📆 Месяц", callback_data=TopCb(act=f"{prefix}_month", uid=uid, c=c).pack()), InlineKeyboardButton(text="🗃 Все время", callback_data=TopCb(act=f"{prefix}_all", uid=uid, c=c).pack())],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act=back, uid=uid, c=c).pack())]
    ])

def kb_wins(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ 3 на 3", callback_data=TopCb(act="wins_3v3", uid=uid, c=c).pack())], [InlineKeyboardButton(text="🌵 ШД", callback_data=TopCb(act="wins_sd", uid=uid, c=c).pack())], [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]])

def kb_wins_sd(uid: int, c: str):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👥 Дуо", callback_data=TopCb(act="wins_sd_duo", uid=uid, c=c).pack()), InlineKeyboardButton(text="👤 Соло", callback_data=TopCb(act="wins_sd_solo", uid=uid, c=c).pack())], [InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="wins", uid=uid, c=c).pack())]])

@router.message(F.text.func(lambda text: is_cmd(text, ["топ", "top", "топ10", "top10", "топ 10", "top 10"])))
async def cmd_top_trigger(message: Message, user_repo: UserRepository, chat_repo: ChatRepository, eco_repo: EconomyRepository, brawl_client: BrawlAPIClient):
    text = message.text.lower().strip()
    for prefix in ["топ 10", "top 10", "топ10", "top10", "топ", "top"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    args_str = text
    uid = message.from_user.id
    c = "ALL"
    try: await message.delete()
    except: pass
    if not args_str:
        kb = await kb_choose_club(uid, brawl_client)
        sent_msg = await message.answer("📊 <b>Выберите клуб:</b>", reply_markup=kb)
        asyncio.create_task(delete_later(sent_msg))
        return

    args_lower = args_str.lower()
    is_push_direct = False
    push_days = 1
    push_title = "за день"
    if any(word in args_lower for word in ["пушеров недели", "пушеров неделя", "пушеры неделя", "пуш неделя", "рост неделя"]): is_push_direct = True; push_days = 7; push_title = "за неделю"
    elif any(word in args_lower for word in ["пушеров месяца", "пушеров месяц", "пушеры месяц", "пуш месяц", "рост месяц"]): is_push_direct = True; push_days = 30; push_title = "за месяц"
    elif any(word in args_lower for word in ["пушеров", "пушеры", "пуш", "рост кубков", "рост", "ап", "апп"]): is_push_direct = True

    if is_push_direct:
        sent_msg = await message.answer("⏳ Собираю актуальные данные...", link_preview_options=LinkPreviewOptions(is_disabled=True))
        try:
            live_members, err = await brawl_client.get_all_club_members(c)
            if not live_members or not isinstance(live_members, list):
                await sent_msg.edit_text("❌ Ошибка загрузки данных из API.", link_preview_options=LinkPreviewOptions(is_disabled=True))
                asyncio.create_task(delete_later(sent_msg, 60))
                return
            tags_filter = [m.get("tag") for m in live_members if isinstance(m, dict) and m.get("tag")]
            baseline_map = await chat_repo.get_baseline_trophies(push_days, tags_filter)
            results = []
            for m in live_members:
                if not isinstance(m, dict): continue
                tag = m.get("tag")
                if not tag: continue
                live_cups = int(m.get("trophies", 0) or 0)
                base_raw = baseline_map.get(tag)
                baseline = int(base_raw) if base_raw is not None else live_cups
                gain = live_cups - baseline
                if gain > 0: results.append((m.get("name", "Игрок"), gain, tag))
            results.sort(key=lambda x: x[1], reverse=True)
            results = results[:10]
            tg_map = (await user_repo.get_tag_to_tg_map()) or {}
            uids = []
            for _, _, tag_str in results:
                tg_data = tg_map.get(tag_str)
                uids.append(tg_data.get("id") if isinstance(tg_data, dict) else None)
            syms_list = await get_roles_bulk(uids, user_repo)
            txt = f"🏆 <b>Топ пушеров ({push_title})</b>\n\n"
            for i, (n, v, tag_str) in enumerate(results):
                tg_data = tg_map.get(tag_str)
                t_uid = tg_data.get("id") if isinstance(tg_data, dict) else None
                tg_name = tg_data.get("name") if isinstance(tg_data, dict) else None
                sym = syms_list[i]
                name_link = make_link(n, tg_name, t_uid)
                place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
                txt += f"{place} {sym} {name_link}: +{v} 🏆\n"
            if not results: txt += "📭 Пока нет данных для расчета (или никто не апнул кубки)."
            back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ К меню топов", callback_data=TopCb(act="main", uid=uid, c="ALL").pack())]])
            await sent_msg.edit_text(txt, reply_markup=back, link_preview_options=LinkPreviewOptions(is_disabled=True))
            asyncio.create_task(delete_later(sent_msg))
        except Exception as e:
            await sent_msg.edit_text(f"❌ Ошибка вычислений: {str(e)}", link_preview_options=LinkPreviewOptions(is_disabled=True))
            asyncio.create_task(delete_later(sent_msg))
        return

    msg_triggers = {"смс", "соо", "сообщение", "сообщения", "sms", "msg", "messages", "чат", "флуд", "писари"}
    wins_triggers = {"победы", "вины", "побед", "wins", "win"}
    cups_triggers = {"общих", "общие", "кубки", "кубков", "общих кубков", "trophies", "cups", "куб"}
    ranks_triggers = {"ранкед", "лига", "ранг", "ranked", "league", "rank", "эло", "elo"}
    eco_triggers = {"феники", "феников", "₣", "f", "эко", "баланс", "богачи", "богачей", "деньги", "phoenix", "balance", "eco", "топ богачей", "топ феников"}

    sent_msg = None
    if args_str in msg_triggers:
        if c != "ALL": return
        sent_msg = await message.answer("💬 <b>Сообщения (Все клубы):</b>", reply_markup=kb_timeframe("msg", "main", uid, c))
    elif args_str in wins_triggers: sent_msg = await message.answer("⚔️ <b>Победы (Все клубы):</b>", reply_markup=kb_wins(uid, c))
    elif args_str in eco_triggers or "top phoenix" in text:
        if c != "ALL": return
        data = await eco_repo.get_top_balance(10)
        uids = [t_uid for _, _, _, t_uid in data]
        syms_list = await get_roles_bulk(uids, user_repo)
        txt = "🔥 <b>Топ богачей (₣)</b>\n\n"
        for i, (tg_name, player_name, bal, t_uid) in enumerate(data):
            display_name = player_name if player_name else (tg_name if tg_name else "Игрок")
            sym = syms_list[i]
            name_link = make_link(display_name, tg_name, t_uid)
            place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
            txt += f"{place} {sym} {name_link}: {bal} ₣\n"
        if not data: txt += "📭 Пока никого нет."
        back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())]])
        sent_msg = await message.answer(txt, reply_markup=back, link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif args_str in cups_triggers:
        sent_msg = await message.answer("⏳ Собираю актуальные данные...")
        try:
            members, err = await brawl_client.get_all_club_members(c)
            if not members or not isinstance(members, list):
                await sent_msg.edit_text(f"❌ Ошибка загрузки.\nДетали: {err}" if err else "❌ Ошибка загрузки.", link_preview_options=LinkPreviewOptions(is_disabled=True))
            else:
                members.sort(key=lambda x: int(x.get("trophies", 0) or 0) if isinstance(x, dict) else 0, reverse=True)
                tg_map = (await user_repo.get_tag_to_tg_map()) or {}
                top_10 = members[:10]
                uids = []
                for m in top_10:
                    tg_data = tg_map.get(m.get("tag")) if isinstance(m, dict) else None
                    uids.append(tg_data.get("id") if isinstance(tg_data, dict) else None)
                syms_list = await get_roles_bulk(uids, user_repo)
                res = f"🏆 <b>ТОП КУБКОВ</b>\n\n"
                for i, m in enumerate(top_10):
                    if not isinstance(m, dict): continue
                    tg_data = tg_map.get(m.get("tag"))
                    t_uid = tg_data.get("id") if isinstance(tg_data, dict) else None
                    tg_name = tg_data.get("name") if isinstance(tg_data, dict) else None
                    sym = syms_list[i]
                    name_link = make_link(m.get('name', 'Игрок'), tg_name, t_uid)
                    place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
                    res += f"{place} {sym} {name_link}: {m.get('trophies', 0)}\n"
                await sent_msg.edit_text(res, link_preview_options=LinkPreviewOptions(is_disabled=True))
        except Exception as e:
            await sent_msg.edit_text(f"❌ Ошибка вычислений: {str(e)}", link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif args_str in ranks_triggers:
        sent_msg = await message.answer("⏳ Собираю актуальные данные...")
        try:
            members, err = await brawl_client.get_live_club_detailed_stats(c)
            tg_map = (await user_repo.get_tag_to_tg_map()) or {}
            if not members or not isinstance(members, list):
                await sent_msg.edit_text("❌ Ошибка загрузки.", link_preview_options=LinkPreviewOptions(is_disabled=True))
            else:
                members.sort(key=lambda x: (int(x.get("ranked_curr_rank", 0) or 0), int(x.get("ranked_curr_elo", 0) or 0)) if isinstance(x, dict) else (0, 0), reverse=True)
                top_10 = members[:10]
                uids = []
                for m in top_10:
                    tg_data = tg_map.get(m.get("tag")) if isinstance(m, dict) else None
                    uids.append(tg_data.get("id") if isinstance(tg_data, dict) else None)
                syms_list = await get_roles_bulk(uids, user_repo)
                txt = f"🎖 <b>Ранкед</b>\n\n"
                for i, m in enumerate(top_10):
                    if not isinstance(m, dict): continue
                    tg_data = tg_map.get(m.get("tag"))
                    t_uid = tg_data.get("id") if isinstance(tg_data, dict) else None
                    tg_name = tg_data.get("name") if isinstance(tg_data, dict) else None
                    sym = syms_list[i]
                    r_val = int(m.get("ranked_curr_rank", 0) or 0)
                    e_val = int(m.get("ranked_curr_elo", 0) or 0)
                    r_name = RANK_NAMES.get(r_val, "🏳️ Без ранга")
                    name_link = make_link(m.get('name', 'Игрок'), tg_name, t_uid)
                    place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
                    txt += f"{place} {sym} {name_link}: {r_name} ({e_val})\n"
                if err: txt += f"\nОшибки: {err}"
                await sent_msg.edit_text(txt, link_preview_options=LinkPreviewOptions(is_disabled=True))
        except Exception as e:
            await sent_msg.edit_text(f"❌ Ошибка вычислений: {str(e)}", link_preview_options=LinkPreviewOptions(is_disabled=True))
    else:
        kb = await kb_choose_club(uid, brawl_client)
        sent_msg = await message.answer("📊 <b>Выберите клуб:</b>", reply_markup=kb)
    if sent_msg: asyncio.create_task(delete_later(sent_msg))

@router.callback_query(TopCb.filter())
async def process_top_callbacks(callback: CallbackQuery, callback_data: TopCb, user_repo: UserRepository, chat_repo: ChatRepository, eco_repo: EconomyRepository, brawl_client: BrawlAPIClient):
    if callback.from_user.id != callback_data.uid: return await callback.answer("❌ Не твое меню", show_alert=True)
    act, uid, c = callback_data.act, callback_data.uid, callback_data.c
    if act == "main":
        kb = await kb_choose_club(uid, brawl_client)
        await callback.message.edit_text("📊 <b>Выберите клуб:</b>", reply_markup=kb)
    elif act == "cat": await callback.message.edit_text("📂 <b>Категория:</b>", reply_markup=kb_main_top(uid, c))
    elif act == "msg":
        if c != "ALL": return
        await callback.message.edit_text("💬 <b>Сообщения:</b>", reply_markup=kb_timeframe("msg", "cat", uid, c))
    elif act == "cups_gain": await callback.message.edit_text("📈 <b>Рост кубков:</b>", reply_markup=kb_timeframe("cups_gain", "cat", uid, c))
    elif act == "wins": await callback.message.edit_text("⚔️ <b>Победы:</b>", reply_markup=kb_wins(uid, c))
    elif act == "wins_sd": await callback.message.edit_text("🌵 <b>Столкновение (ШД):</b>", reply_markup=kb_wins_sd(uid, c))
    elif act == "eco":
        if c != "ALL": return
        await callback.message.edit_text("⏳ Собираю данные...", link_preview_options=LinkPreviewOptions(is_disabled=True))
        try:
            data = await eco_repo.get_top_balance(10)
            uids = [t_uid for _, _, _, t_uid in data]
            syms_list = await get_roles_bulk(uids, user_repo)
            txt = "🔥 <b>Топ богачей (₣)</b>\n\n"
            for i, (tg_name, player_name, bal, t_uid) in enumerate(data):
                display_name = player_name if player_name else (tg_name if tg_name else "Игрок")
                sym = syms_list[i]
                name_link = make_link(display_name, tg_name, t_uid)
                place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
                txt += f"{place} {sym} {name_link}: {bal} ₣\n"
            if not data: txt += "📭 Пока никого нет."
            back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())]])
            await callback.message.edit_text(txt, reply_markup=back, link_preview_options=LinkPreviewOptions(is_disabled=True))
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка вычислений: {str(e)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c="ALL").pack())]]), link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif act == "cups_cur":
        await callback.message.edit_text("⏳ Собираю актуальные данные...", link_preview_options=LinkPreviewOptions(is_disabled=True))
        try:
            members, err = await brawl_client.get_all_club_members(c)
            if not members or not isinstance(members, list):
                await callback.message.edit_text(f"❌ Ошибка загрузки.\nДетали: {err}" if err else "❌ Ошибка загрузки.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]]), link_preview_options=LinkPreviewOptions(is_disabled=True))
                return
            members.sort(key=lambda x: int(x.get("trophies", 0) or 0) if isinstance(x, dict) else 0, reverse=True)
            tg_map = (await user_repo.get_tag_to_tg_map()) or {}
            top_10 = members[:10]
            uids = []
            for m in top_10:
                tg_data = tg_map.get(m.get("tag")) if isinstance(m, dict) else None
                uids.append(tg_data.get("id") if isinstance(tg_data, dict) else None)
            syms_list = await get_roles_bulk(uids, user_repo)
            res = f"🏆 <b>ТОП КУБКОВ</b>\n\n"
            for i, m in enumerate(top_10):
                if not isinstance(m, dict): continue
                tg_data = tg_map.get(m.get("tag"))
                t_uid = tg_data.get("id") if isinstance(tg_data, dict) else None
                tg_name = tg_data.get("name") if isinstance(tg_data, dict) else None
                sym = syms_list[i]
                name_link = make_link(m.get('name', 'Игрок'), tg_name, t_uid)
                place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
                res += f"{place} {sym} {name_link}: {m.get('trophies', 0)}\n"
            await callback.message.edit_text(res, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]]), link_preview_options=LinkPreviewOptions(is_disabled=True))
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка вычислений: {str(e)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]]), link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif act in ["wins_3v3", "wins_sd_solo", "wins_sd_duo", "ranks_curr"]:
        await callback.message.edit_text("⏳ Собираю актуальные данные...", link_preview_options=LinkPreviewOptions(is_disabled=True))
        back_act = "wins_sd" if act.startswith("wins_sd_") else "wins" if act.startswith("wins_") else "cat"
        back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act=back_act, uid=uid, c=c).pack())]])
        try:
            members, err = await brawl_client.get_live_club_detailed_stats(c)
            tg_map = (await user_repo.get_tag_to_tg_map()) or {}
            if not members or not isinstance(members, list): return await callback.message.edit_text("❌ Ошибка загрузки", reply_markup=back, link_preview_options=LinkPreviewOptions(is_disabled=True))
            if act == "ranks_curr": sort_key = lambda x: (int(x.get("ranked_curr_rank", 0) or 0), int(x.get("ranked_curr_elo", 0) or 0)) if isinstance(x, dict) else (0, 0); title = "🎖 Ранкед"
            elif act == "wins_3v3": sort_key = lambda x: int(x.get("wins_3v3", 0) or 0) if isinstance(x, dict) else 0; title = "⚔️ 3 на 3"
            elif act == "wins_sd_solo": sort_key = lambda x: int(x.get("solo_wins", 0) or 0) if isinstance(x, dict) else 0; title = "👤 Соло"
            elif act == "wins_sd_duo": sort_key = lambda x: int(x.get("duo_wins", 0) or 0) if isinstance(x, dict) else 0; title = "👥 Дуо"
            members.sort(key=sort_key, reverse=True)
            top_10 = members[:10]
            uids = []
            for m in top_10:
                tg_data = tg_map.get(m.get("tag")) if isinstance(m, dict) else None
                uids.append(tg_data.get("id") if isinstance(tg_data, dict) else None)
            syms_list = await get_roles_bulk(uids, user_repo)
            txt = f"<b>{title}</b>\n\n"
            for i, m in enumerate(top_10):
                if not isinstance(m, dict): continue
                tg_data = tg_map.get(m.get("tag"))
                t_uid = tg_data.get("id") if isinstance(tg_data, dict) else None
                tg_name = tg_data.get("name") if isinstance(tg_data, dict) else None
                sym = syms_list[i]
                name_link = make_link(m.get('name', 'Игрок'), tg_name, t_uid)
                place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
                if act == "ranks_curr":
                    r_val = int(m.get("ranked_curr_rank", 0) or 0)
                    e_val = int(m.get("ranked_curr_elo", 0) or 0)
                    txt += f"{place} {sym} {name_link}: {RANK_NAMES.get(r_val, '🏳️ Без ранга')} ({e_val})\n"
                else: txt += f"{place} {sym} {name_link}: {sort_key(m)}\n"
            if err: txt += f"\nОшибки: {err}"
            await callback.message.edit_text(txt, reply_markup=back, link_preview_options=LinkPreviewOptions(is_disabled=True))
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка вычислений: {str(e)}", reply_markup=back, link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif act.startswith("msg_"):
        await callback.message.edit_text("⏳ Собираю данные...", link_preview_options=LinkPreviewOptions(is_disabled=True))
        try:
            d = {"msg_day": 1, "msg_week": 7, "msg_month": 30, "msg_all": None}.get(act)
            data = await chat_repo.get_top_messages(d)
            uids = [t_uid for _, _, _, t_uid in data]
            syms_list = await get_roles_bulk(uids, user_repo)
            txt = "💬 <b>Топ сообщений чата</b>\n\n"
            for i, (tg_name, player_name, v, t_uid) in enumerate(data):
                display_name = player_name if player_name else (tg_name if tg_name else "Игрок")
                sym = syms_list[i]
                name_link = make_link(display_name, tg_name, t_uid)
                place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
                txt += f"{place} {sym} {name_link}: {v}\n"
            await callback.message.edit_text(txt, reply_markup=kb_timeframe("msg", "cat", uid, c), link_preview_options=LinkPreviewOptions(is_disabled=True))
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка вычислений: {str(e)}", reply_markup=kb_timeframe("msg", "cat", uid, c), link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif act.startswith("cups_gain_"):
        d = {"cups_gain_day": 1, "cups_gain_week": 7, "cups_gain_month": 30, "cups_gain_all": 3650}.get(act, 1)
        await callback.message.edit_text("⏳ Собираю актуальные данные...", link_preview_options=LinkPreviewOptions(is_disabled=True))
        back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=TopCb(act="cat", uid=uid, c=c).pack())]])
        try:
            live_members, err = await brawl_client.get_all_club_members(c)
            if not live_members or not isinstance(live_members, list):
                await callback.message.edit_text("❌ Ошибка API", reply_markup=kb_timeframe("cups_gain", "cat", uid, c), link_preview_options=LinkPreviewOptions(is_disabled=True))
                return
            tags_filter = [m.get("tag") for m in live_members if isinstance(m, dict) and m.get("tag")]
            baseline_map = await chat_repo.get_baseline_trophies(d, tags_filter)
            results = []
            for m in live_members:
                if not isinstance(m, dict): continue
                tag = m.get("tag")
                if not tag: continue
                live_cups = int(m.get("trophies", 0) or 0)
                base_raw = baseline_map.get(tag)
                baseline = int(base_raw) if base_raw is not None else live_cups
                gain = live_cups - baseline
                if gain > 0: results.append((m.get("name", "Игрок"), gain, tag))
            results.sort(key=lambda x: x[1], reverse=True)
            top_10 = results[:10]
            tg_map = (await user_repo.get_tag_to_tg_map()) or {}
            uids = []
            for _, _, tag_str in top_10:
                tg_data = tg_map.get(tag_str)
                uids.append(tg_data.get("id") if isinstance(tg_data, dict) else None)
            syms_list = await get_roles_bulk(uids, user_repo)
            txt = "📈 <b>Рост кубков</b>\n\n"
            for i, (n, v, tag_str) in enumerate(top_10):
                tg_data = tg_map.get(tag_str)
                t_uid = tg_data.get("id") if isinstance(tg_data, dict) else None
                tg_name = tg_data.get("name") if isinstance(tg_data, dict) else None
                sym = syms_list[i]
                name_link = make_link(n, tg_name, t_uid)
                place = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"<b>{i + 1}.</b>")
                txt += f"{place} {sym} {name_link}: +{v} 🏆\n"
            if not top_10: txt += "📭 Пока нет данных для расчета."
            await callback.message.edit_text(txt, reply_markup=kb_timeframe("cups_gain", "cat", uid, c), link_preview_options=LinkPreviewOptions(is_disabled=True))
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка вычислений: {str(e)}", reply_markup=back, link_preview_options=LinkPreviewOptions(is_disabled=True))