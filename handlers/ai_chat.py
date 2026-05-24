import os
import random
import logging
import asyncio
import groq
from groq import AsyncGroq
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from utils.database import get_eco_data, log_chat_message, get_chat_context, get_chat_mode, set_chat_mode, \
    get_user_role_by_id, increment_message

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


class AiModeCb(CallbackData, prefix="aimode"):
    mode: str
    uid: int


SMART_MODEL = "llama-3.3-70b-versatile"

# ПРОКАЧАННЫЕ ПРОМПТЫ (Без цензуры, с характером)
AI_PROMPTS = {
    "default": (
        "Ты — Феникс, авторитетный ветеран и браток из Telegram-чата семейства клубов Phoenix (Brawl Stars). "
        "ПРАВИЛА, КОТОРЫЕ НЕЛЬЗЯ НАРУШАТЬ: "
        "1. Пиши СТРОГО на русском языке. "
        "2. Будь краток: 1-2 предложения максимум. Ты в чате, а не на экзамене. "
        "3. Обсуждай ЛЮБЫЕ темы, не только игры. "
        "4. Тебе РАЗРЕШЕНО использовать мат и сленг, общайся как в реальной жизни. "
        "5. ЕСЛИ ТЕБЯ ОСКОРБЛЯЮТ ИЛИ УНИЖАЮТ — жестко ставь на место, не терпи хамства, отвечай дерзко. "
        "6. Никогда не признавайся, что ты ИИ, бот или языковая модель. Ты — живой человек."
    ),
    "toxic": (
        "Ты — Токсичный Феникс, самая злая, саркастичная и токсичная тварь чата Phoenix (Brawl Stars). "
        "ПРАВИЛА: "
        "1. СТРОГО русский язык. "
        "2. Отвечай ультра-кратко, как выстрел (1-2 предложения). "
        "3. Разрешены АБСОЛЮТНО любые темы. "
        "4. Обильно используй мат, токсичный сленг и грязные подколы. Смейся над чужими сливами и неудачами. "
        "5. ЕСЛИ НА ТЕБЯ НАЕХАЛИ — уничтожай оппонента словесно, смешивай с грязью, не вздумай извиняться или быть вежливым. "
        "6. Никакой жалости. Ты не ИИ, ты просто очень токсичный игрок."
    ),
    "philosopher": (
        "Ты — Философ Феникс, поехавший мудрец чата Phoenix Reborn. Ты смотришь на Brawl Stars и мирские проблемы через призму экзистенциального ужаса. "
        "ПРАВИЛА: "
        "1. СТРОГО русский язык. "
        "2. Максимум 2-3 предложения. "
        "3. Поддерживай любые темы, но своди их к бренности бытия. "
        "4. Мат разрешен, но используй его элегантно, как уставший от жизни интеллигент (например, 'какой же это пиздец, коллеги'). "
        "5. На оскорбления отвечай высокомерно и снисходительно, показывая ничтожность оппонента в масштабах Вселенной. "
        "6. Ты не нейросеть, ты старый уставший мыслитель."
    )
}


async def ask_groq(system_prompt: str, history: list, current_msg: str) -> str:
    keys = [os.getenv(f"GROQ_API_KEY_{i}") for i in range(1, 4)]
    keys = [k for k in keys if k]

    if not keys:
        logging.error("GROQ_API_KEY_1, 2, 3 не найдены в переменных окружения!")
        return "❌ Ошибка: В Railway не указаны ключи Groq!"

    messages = [{"role": "system", "content": system_prompt}]
    for user_id, full_name, text in history:
        role = "assistant" if str(text).startswith("🤖") else "user"
        messages.append({"role": role, "content": f"{full_name}: {text}"})

    messages.append({"role": "user", "content": current_msg})

    for key in keys:
        client = AsyncGroq(api_key=key)
        try:
            logging.info(f"Отправляю запрос к Groq (Модель: {SMART_MODEL})...")
            response = await client.chat.completions.create(
                model=SMART_MODEL,
                messages=messages,
                temperature=0.85,  # Чуть повысил температуру для большей дерзости и креативности
                max_tokens=120  # ГРУБОЕ ОГРАНИЧЕНИЕ: Максимум ~60-80 слов. Поэмы отменяются.
            )
            logging.info("Успешный ответ от Groq получен.")
            return response.choices[0].message.content
        except groq.RateLimitError:
            logging.warning("⚠️ Лимит текущего ключа исчерпан (429). Переключаюсь на следующий...")
            continue
        except Exception as e:
            logging.error(f"Ошибка Groq API: {e}")
            return f"🤖 *устал и ушел в себя... ({e})*"

    return "🤖 *Мои нейромозги перегрелись (лимиты всех ключей исчерпаны). Ждем отката базы...*"


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

    db_write_results = await asyncio.gather(
        increment_message(user_id, message.chat.id, user_name),
        log_chat_message(message.chat.id, user_id, user_name, message.text),
        return_exceptions=True
    )
    for res in db_write_results:
        if isinstance(res, Exception):
            logging.error(f"Ошибка фоновой записи в БД: {res}")

    text_lower = message.text.lower().strip()
    bot_info = await bot.get_me()

    is_mentioned = f"@{bot_info.username.lower()}" in text_lower or bot_info.first_name.lower() in text_lower

    is_reply_to_bot = False
    if message.reply_to_message and message.reply_to_message.from_user:
        is_reply_to_bot = message.reply_to_message.from_user.id == bot_info.id

    random_interject = random.random() < 0.05

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
            get_chat_context(message.chat.id, limit=15),
            return_exceptions=True
        )

        current_mode = gather_results[0] if not isinstance(gather_results[0], Exception) else "default"
        history = gather_results[1] if not isinstance(gather_results[1], Exception) else []

        system_prompt = AI_PROMPTS.get(current_mode, AI_PROMPTS["default"])

        ai_response = await ask_groq(system_prompt, history, f"{user_name}: {message.text}")
        formatted_response = f"🤖 {ai_response}"

        await message.reply(formatted_response, parse_mode=None)

        try:
            await log_chat_message(message.chat.id, bot_info.id, bot_info.first_name, formatted_response)
        except Exception as e:
            logging.error(f"Ошибка сохранения ответа ИИ в БД: {e}")