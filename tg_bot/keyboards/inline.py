from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from external.brawl_api import BrawlAPIClient

class TopCb(CallbackData, prefix="top"):
    act: str
    uid: int
    c: str

class CasinoCb(CallbackData, prefix="cas"):
    act: str
    game: str
    val: str = "0"

class BjCb(CallbackData, prefix="bj"):
    act: str

class SaperSetupCb(CallbackData, prefix="spset"):
    act: str
    val: str

class SaperCb(CallbackData, prefix="sap"):
    act: str
    idx: int

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

def kb_casino_main(balance: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Блэкджек (21)", callback_data=CasinoCb(act="bet", game="bj").pack()), InlineKeyboardButton(text="💣 Сапёр", callback_data=CasinoCb(act="saper_route", game="saper").pack())],
        [InlineKeyboardButton(text="🎰 Слоты", callback_data=CasinoCb(act="bet", game="slot").pack()), InlineKeyboardButton(text="🎲 Кости", callback_data=CasinoCb(act="bet", game="dice").pack())],
        [InlineKeyboardButton(text="🎯 Дартс", callback_data=CasinoCb(act="bet", game="darts").pack()), InlineKeyboardButton(text="🎳 Боулинг", callback_data=CasinoCb(act="bet", game="bowl").pack())],
        [InlineKeyboardButton(text="⚽️ Футбол", callback_data=CasinoCb(act="bet", game="fball").pack()), InlineKeyboardButton(text="🏀 Баскетбол", callback_data=CasinoCb(act="bet", game="bball").pack())],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data=CasinoCb(act="close", game="none").pack())]
    ])

def kb_casino_bet(game: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 10", callback_data=CasinoCb(act="play", game=game, val="10").pack()), InlineKeyboardButton(text="💵 50", callback_data=CasinoCb(act="play", game=game, val="50").pack()), InlineKeyboardButton(text="💵 100", callback_data=CasinoCb(act="play", game=game, val="100").pack())],
        [InlineKeyboardButton(text="💸 500", callback_data=CasinoCb(act="play", game=game, val="500").pack()), InlineKeyboardButton(text="💸 1000", callback_data=CasinoCb(act="play", game=game, val="1000").pack()), InlineKeyboardButton(text="🏦 ВА-БАНК", callback_data=CasinoCb(act="play", game=game, val="all").pack())],
        [InlineKeyboardButton(text="⬅️ Назад к играм", callback_data=CasinoCb(act="menu", game="none").pack())]
    ])

def kb_saper_setup_bet():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 50", callback_data=SaperSetupCb(act="bet", val="50").pack()), InlineKeyboardButton(text="💵 100", callback_data=SaperSetupCb(act="bet", val="100").pack())],
        [InlineKeyboardButton(text="💸 500", callback_data=SaperSetupCb(act="bet", val="500").pack()), InlineKeyboardButton(text="💸 1000", callback_data=SaperSetupCb(act="bet", val="1000").pack())],
        [InlineKeyboardButton(text="🏦 ВА-БАНК", callback_data=SaperSetupCb(act="bet", val="all").pack())],
        [InlineKeyboardButton(text="⬅️ Назад к играм", callback_data=CasinoCb(act="menu", game="none").pack())]
    ])

def kb_saper_setup_diff(bet: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Легкий (5 мин)", callback_data=SaperSetupCb(act=f"start_{bet}", val="easy").pack())],
        [InlineKeyboardButton(text="🟡 Средний (12 мин)", callback_data=SaperSetupCb(act=f"start_{bet}", val="medium").pack())],
        [InlineKeyboardButton(text="🔴 Трудный (20 мин)", callback_data=SaperSetupCb(act=f"start_{bet}", val="hard").pack())],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=SaperSetupCb(act="cancel", val="0").pack())]
    ])

def kb_saper_game(game: dict, game_over=False):
    if not game: return None
    kb = []
    grid = game["grid"]
    clicked = game["clicked"]
    for row in range(5):
        row_btns = []
        for col in range(5):
            idx = row * 5 + col
            if not game_over:
                text = "💎" if idx in clicked else "⬜️"
                cb = SaperCb(act="click", idx=idx).pack()
            else:
                if grid[idx] == 1: text = "💥" if idx in clicked else "💣"
                else: text = "💎" if idx in clicked else "⬜️"
                cb = "ignore"
            row_btns.append(InlineKeyboardButton(text=text, callback_data=cb))
        kb.append(row_btns)
    if not game_over and len(clicked) > 0:
        current_win = int(game["bet"] * game["mult"])
        kb.append([InlineKeyboardButton(text=f"🛑 Забрать {current_win} ₣", callback_data=SaperCb(act="cashout", idx=-1).pack())])
    return InlineKeyboardMarkup(inline_keyboard=kb)