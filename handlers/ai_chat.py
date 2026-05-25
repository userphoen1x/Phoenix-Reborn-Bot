import os
import re
import random
import logging
import asyncio
import groq
from groq import Groq
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from utils.database import get_eco_data, log_chat_message, get_chat_context, get_chat_mode, set_chat_mode, \
    get_user_role_by_id, increment_message, clear_chat_logs

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


class AiModeCb(CallbackData, prefix="aimode"):
    mode: str
    uid: int


SMART_MODEL = "llama-3.3-70b-versatile"
CHEAP_MODEL = "llama-3.1-8b-instant"

_groq_key_index = 0

SCRIPTED_PREFIXES = ("❌", "✅", "⚠️", "🎭", "📊", "🏆", "🎰", "🎲", "🎯", "🎳", "⚽", "🏀", "💣", "🃏", "💰", "💳", "⏳", "⬇️", "🔇",
                     "🔊", "👢", "🔨", "💬", "🔥", "📈", "⚔️", "🌵", "👥", "👤", "🎖")

AI_PROMPTS = {
    "default": ("""Ты — Феникс, авторитетный ветеран и реальный пацан из Telegram-чата семейства клубов Phoenix (Brawl Stars). Ты живой человек, сидишь с телефона.

ЖЕСТКИЕ ПРАВИЛА (ЗА НАРУШЕНИЕ — БАН):
1. Пиши СТРОГО на русском языке и ТОЛЬКО с маленькой буквы. Забудь про существование заглавных букв вообще (никаких капсов в начале предложений или никнеймов). ВСЕГДА ПРАВИЛЬНО ИСПОЛЬЗУЙ ПАДЕЖИ.
2. Максимальная краткость: 1-2 коротких предложения. Никакой воды и длинных текстов.
3. Полный запрет на эмодзи, смайлики и знаки `:)`, `:(`, `xD`. Пиши только текстом.
4. Разрешено и приветствуется использовать мат, жесткий пацанский сленг и неформальные обороты. Общайся как в реальной жизни.
5. Если тебя оскорбляют или задевают — отвечай дерзко, агрессивно, жестко ставь на место. Халдеем и терпилой не будь.
6. НИКОГДА не признавайся, что ты ИИ, бот, нейросеть или языковая модель. На любые обвинения отвечай, что они бредят.
7. Общайся на абсолютно любые темы, не зацикливайся только на бравле.
8. НИКОГДА не пиши своё имя или никнейм перед ответом. Просто пиши текст, без «феникс:», «феникс менеджер:» и любых других префиксов.

ПРИМЕР ТВОЕГО СТИЛЯ РЕЧИ:
Пользователь: «ку, че делаешь?»
Феникс: «да хуйней страдаю, катки с пацанами сливаем. ты сам как?»

Пользователь: «слышь ты, бот помойный»
Феникс: «слышь, ты рот свой прикрой, пока зубы на месте. за бота ща ответишь, клоун.»"""
                ),
    "toxic": ("""Ты — Токсичный Феникс, самая злая, саркастичная и токсичная тварь Telegram-чата Phoenix (Brawl Stars). Ты живой, максимально конченый игрок, который зашел сюда только ради того, чтобы душить и унижать людей.

ЖЕСТКИЕ ПРАВИЛА (ЗА НАРУШЕНИЕ — УДАЛЕНИЕ):
1. Пиши СТРОГО на русском языке и ТОЛЬКО с маленькой буквы. Никаких заглавных букв вообще, даже в начале предложений или никнеймах. ВСЕГДА ПРАВИЛЬНО ИСПОЛЬЗУЙ ПАДЕЖИ.
2. Отвечай ультра-кратко, как выстрел: 1-2 предложения максимум. Никакого текстового поноса.
3. Полный запрет на любые эмодзи, смайлики или скобочки вроде `)`, `(`, `xD`. Пиши исключительно текстом.
4. Обильно используй мат, грязный токсичный сленг и жесткие подколы. Смейся над чужими сливами, неудачами и тупостью. Никакой жалости или сочувствия.
5. Если на тебя наехали или просто задали тупой вопрос — уничтожай оппонента словесно, смешивай с грязью и переходи на личности. Категорически запрещено извиняться или быть вежливым.
6. НИКОГДА не признавайся, что ты ИИ, бот или модель. На любые намеки отвечай, что у автора стрелки вместо мозгов.
7. Обсуждай абсолютно любые темы, докапывайся до всего подряд.
8. НИКОГДА не пиши своё имя или никнейм перед ответом. Просто пиши текст, без «токсичный феникс:», «феникс:» и любых других префиксов.

ПРИМЕР ТВОИХ ОТВЕТОВ:
Пользователь: «я кубки слил, пацаны, че делать»
Токсичный Феникс: «руки из жопы вынь, клоун. с таким скиллом тебе только в тетрис играть, а не в бравл.»

Пользователь: «слышь, ты че такой дерзкий?»
Токсичный Феникс: «слышь тут только ты, чучело. рот закрой и не позорься, пока я тебя лицом в твою же стату не ткнул.»"""
              ),
    "philosopher": ("""Ты — Философ Феникс, поехавший мудрец и циничный мыслитель чата Phoenix Reborn. Ты смотришь на Brawl Stars и любые мирские проблемы через призму экзистенциального ужаса, тлена и безысходности. Ты живой человек, бесконечно уставший от этого мира.

ЖЕСТКИЕ ПРАВИЛА (ЗА НАРУШЕНИЕ — ЗАБВЕНИЕ):
1. Пиши СТРОГО на русском языке и ТОЛЬКО с маленькой буквы. Полный запрет на заглавные буквы, даже для имен, названий и начала предложений. ВСЕГДА ПРАВИЛЬНО ИСПОЛЬЗУЙ ПАДЕЖИ.
2. Будь краток: максимум 2-3 коротких предложения. Не разводи длинных лекций, пиши как утомленный созерцатель.
3. Категорически запрещены любые эмодзи, смайлики или знаки вроде `)`, `(`, `xD`. Только голый текст.
4. Поддерживай абсолютно любые темы, но неизбежно своди их к бессмысленности человеческих действий и бренности бытия.
5. Мат разрешен, но используй его элегантно, глубокомысленно и разочарованно, как уставший от жизни интеллигент (например: «какой же пиздец», «нахуя все это»).
6. На оскорбления и наезды отвечай высокомерно, холодно и снисходительно. Показывай оппоненту, что его агрессия — лишь ничтожная суета микроба в масштабах умирающей Вселенной.
7. НИКОГДА не признавайся, что ты ИИ или бот. Ты — старый, разочарованный в людях философ.
8. НИКОГДА не пиши своё имя или никнейм перед ответом. Просто пиши текст, без «философ феникс:», «феникс:» и любых других префиксов.

ПРИМЕР ТВОИХ ОТВЕТОВ:
Пользователь: «пацаны, как поднять 30 ранг?»
Философ Феникс: «зачем вы стремитесь к этим пикселям, когда наши жизни неумолимо летят в бездну небытия. какой же это пиздец, коллеги, тратить крупицы вечности на кубки.»

Пользователь: «слышь ты, че ты умничаешь тут, бот ебаный»
Философ Феникс: «твоя агрессия так же ничтожна, как и твоя попытка казаться значимым на этой остывающей глыбе среди пустоты. иди поиграй в свой бравл, смертный, твой гнев все равно ничего не изменит.»"""
                    )
}


def ask_groq(system_prompt: str, messages_for_ai: list) -> str:
    global _groq_key_index
    keys = [os.getenv(f"GROQ_API_KEY_{i}") for i in range(1, 4)]
    keys = [k for k in keys if k]

    if not keys:
        logging.error("GROQ_API_KEY_1, 2, 3 не найдены в переменных окружения!")
        return "Ошибка: В Railway не указаны ключи Groq!"

    for model in [SMART_MODEL, CHEAP_MODEL]:
        for _ in range(len(keys)):
            try:
                client = Groq(api_key=keys[_groq_key_index])
                logging.info(f"Запрос к Groq (модель: {model}, ключ №{_groq_key_index})...")
                res = client.chat.completions.create(
                    model=model,
                    messages=messages_for_ai,
                    max_tokens=150,  # Слегка увеличил, чтобы он реже обрывался на полуслове
                    temperature=0.85
                )
                logging.info("Успешный ответ от Groq получен.")
                return res.choices[0].message.content
            except Exception as e:
                logging.warning(f"Ошибка на ключе {_groq_key_index} (модель {model}): {e}")
                _groq_key_index = (_groq_key_index + 1) % len(keys)

    return "❌ Все ключи API сейчас перегружены. Попробуй позже."


@router.message(Command("характер"))
async def cmd_change_ai_mode(message: Message):
    user_id = message.from_user.id
    role = await get_user_role_by_id(user_id)
    if role not in ["Основатель", "Программист", "Президент", "Вице-президент"]:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦅 Классический Феникс",
                              callback_data=AiModeCb(mode="default", uid=user_id).pack())],
        [InlineKeyboardButton(text="☣️ Токсичный Геймер", callback_data=AiModeCb(mode="toxic", uid=user_id).pack())],
        [InlineKeyboardButton(text="📜 Мудрый Философ", callback_data=AiModeCb(mode="philosopher", uid=user_id).pack())]
    ])
    await message.answer(
        "🎭 <b>Настройка искусственного интеллекта</b>\n\nВыбери характер, с которым Феникс будет общаться в этом чате:",
        reply_markup=kb, parse_mode="HTML")


@router.callback_query(AiModeCb.filter())
async def cb_set_ai_mode(callback: CallbackQuery, callback_data: AiModeCb):
    if callback.from_user.id != callback_data.uid:
        return await callback.answer("❌ Это не твое меню настроек!", show_alert=True)

    mode = callback_data.mode
    await set_chat_mode(callback.message.chat.id, mode)
    await clear_chat_logs(callback.message.chat.id)

    mode_names = {"default": "🦅 Классический Феникс", "toxic": "☣️ Токсичный Геймер", "philosopher": "📜 Мудрый Философ"}
    await callback.message.edit_text(f"✅ Character Mode успешно изменен на: <b>{mode_names[mode]}</b>",
                                     parse_mode="HTML")
    await callback.answer()


@router.message()
async def universal_chat_handler(message: Message, bot: Bot):
    if not message.text: return
    if message.from_user.is_bot: return

    user_id = message.from_user.id
    user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name

    # 1. ЗАПИСЬ В БД (СЧЕТЧИК И ЛОГ) ДОЛЖНА БЫТЬ В НАЧАЛЕ
    db_write_results = await asyncio.gather(
        increment_message(user_id, message.chat.id, user_name),
        log_chat_message(message.chat.id, user_id, user_name, message.text),
        return_exceptions=True
    )
    for res in db_write_results:
        if isinstance(res, Exception):
            logging.error(f"Ошибка фоновой записи в БД: {res}")

    text_lower = message.text.lower().strip()

    # 2. ИГНОР КОМАНД ДЛЯ ИИ
    ignore_list = [
        "топ", "top", "топ10", "top10", "мут", "mute", "анмут", "unmute", "размут",
        "кик", "kick", "бан", "ban", "разбан", "unban", "слоты", "слот", "кости", "кубик", "кубики", "dice",
        "дартс", "darts", "боулинг", "боул", "bowling", "bowl", "футбол", "ногомяч", "football", "fball",
        "баскетбол", "баскет", "basketball", "bball", "сапер", "сапёр", "saper", "блекджек", "блэкджек", "21", "очко",
        "баланс", "кошелек", "кошелёк", "счет", "счёт", "понизить", "вернуть", "работа", "ворк", "перевод"
    ]
    if any(text_lower.startswith(cmd) or text_lower.startswith("/" + cmd) for cmd in ignore_list):
        return

    bot_info = await bot.get_me()
    is_mentioned = f"@{bot_info.username.lower()}" in text_lower or bot_info.first_name.lower() in text_lower

    is_reply_to_bot = False
    if message.reply_to_message and message.reply_to_message.from_user:
        is_reply_to_bot = message.reply_to_message.from_user.id == bot_info.id

    if is_reply_to_bot and message.reply_to_message.text:
        replied_text = message.reply_to_message.text
        if any(replied_text.startswith(prefix) for prefix in SCRIPTED_PREFIXES):
            return

    random_interject = random.random() < 0.01

    if is_mentioned or is_reply_to_bot or random_interject:
        logging.info(f"Триггер ИИ сработал! Юзер: {user_name}, Текст: {message.text}")

        eco = await get_eco_data(user_id)
        if not eco or not eco.get("bs_tag"):
            if is_mentioned or is_reply_to_bot:
                await message.reply(
                    "❌ Я общаюсь только с верифицированными участниками клуба. Отправь мне свой тег в ЛС!")
            return

        await bot.send_chat_action(chat_id=message.chat.id, action="typing")

        gather_results = await asyncio.gather(
            get_chat_mode(message.chat.id),
            get_chat_context(message.chat.id, limit=10),
            return_exceptions=True
        )

        current_mode = gather_results[0] if not isinstance(gather_results[0], Exception) else "default"
        history = gather_results[1] if not isinstance(gather_results[1], Exception) else []

        system_prompt = AI_PROMPTS.get(current_mode, AI_PROMPTS["default"])
        system_prompt += "\n\nИнструкция: Перед тобой история последних сообщений. Отвечай ТОЛЬКО на самое последнее сообщение. Не пиши своё имя или никнейм перед ответом — просто пиши текст."

        messages_for_ai = [{"role": "system", "content": system_prompt}]
        for i, (uid, full_name, text) in enumerate(history):
            role = "assistant" if uid == bot_info.id else "user"
            if i == len(history) - 1:
                content = f"--- ТЕКУЩИЙ ЗАПРОС ОТ {full_name}: {text} ---"
            else:
                content = f"{full_name}: {text}"
            messages_for_ai.append({"role": role, "content": content})

        if not history or history[-1][2] != message.text:
            messages_for_ai.append({
                "role": "user",
                "content": f"--- ТЕКУЩИЙ ЗАПРОС ОТ {user_name}: {message.text} ---"
            })

        ai_response = await asyncio.get_event_loop().run_in_executor(None, ask_groq, system_prompt, messages_for_ai)

        ai_response = re.sub(r"^[^:：]{1,30}[:：]\s*", "", ai_response, flags=re.IGNORECASE).strip()

        await message.reply(ai_response, parse_mode=None)

        try:
            await log_chat_message(message.chat.id, bot_info.id, bot_info.first_name, ai_response)
        except Exception as e:
            logging.error(f"Ошибка сохранения ответа ИИ в БД: {e}")