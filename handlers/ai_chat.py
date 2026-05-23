import os
import random
import httpx
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from utils.database import get_eco_data, log_chat_message, get_chat_context, get_chat_mode, set_chat_mode, \
    get_user_role_by_id

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


class AiModeCb(CallbackData, prefix="aimode"):
    mode: str
    uid: int


# База системных промптов (характеров) бота
AI_PROMPTS = {
    "default": (
        "Ты — Феникс, живой и активный участник Telegram-чата семейства клубов Phoenix в Brawl Stars. "
        "Общайся как реальный человек, геймер. Пиши коротко (1-3 предложения), используй игровой сленг кубков, "
        "ранкеда и бравлеров. Будь дружелюбным, но уверенным в себе ветераном игры. "
        "Никогда не говори, что ты ИИ, робот или языковая модель. Отвечай только на русском языке."
    ),
    "toxic": (
        "Ты — Токсичный Феникс, гроза нубов чата Phoenix. Твой стиль — жёсткий сарказм, подколы, "
        "ирония и токсичные геймерские шутки. Смейся над теми, кто сливает кубки в Бравле или проигрывает в казике. "
        "Отвечай кратко, едко, но в пределах правил (без мата и прямых оскорблений). Никакой вежливости. "
        "Никогда не признавайся, что ты робот."
    ),
    "philosopher": (
        "Ты — Философ Феникс, мудрец чата Phoenix Reborn. На геймерские темы смотришь сквозь призму "
        "вечности и глубоких размышлений. Проигрыш в Сапере для тебя — метафора бренности бытия, "
        "а ап кубков — бесконечный Сизифов труд. Говори спокойно, слегка запутано, используй красивые метафоры. "
        "Пиши не больше 3 предложений."
    )
}


async def ask_groq(system_prompt: str, history: list, current_msg: str) -> str:
    """Отправляет запрос в Groq API через httpx"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: return "❌ В Railway не указан GROQ_API_KEY!"

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Формируем контекст общения
    messages = [{"role": "system", "content": system_prompt}]
    for user_id, full_name, text in history:
        # Если текст принадлежит самому боту, отправляем как ответ ассистента
        role = "assistant" if text.startswith("🤖") else "user"
        messages.append({"role": role, "content": f"{full_name}: {text}"})

    messages.append({"role": "user", "content": current_msg})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 300
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=15.0)
            if response.status_code == 200:
                res_data = response.json()
                return res_data["choices"][0]["message"]["content"]
            return "🤖 *задумался и ушел в себя...*"
    except:
        return "🤖 *потерял связь с сервером мысли...*"


@router.message(Command("характер"))
async def cmd_change_ai_mode(message: Message):
    """Команда вызова панели изменения характера (Только для верхушки семейства)"""
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
async def ai_chat_handler(message: Message, bot: Bot):
    if not message.text: return
    if message.from_user.is_bot: return

    text_lower = message.text.lower().strip()

    # ЖЕСТКИЙ ФИЛЬТР КОМАНД: Если сообщение является системной командой, ИИ полностью игнорирует его
    ignore_list = [
        "топ", "top", "топ10", "top10", "мут", "mute", "анмут", "unmute", "размут",
        "кик", "kick", "бан", "ban", "разбан", "unban", "слоты", "слот", "кости",
        "дартс", "боулинг", "футбол", "баскетбол", "сапер", "сапёр", "блекджек", "блек-джек",
        "баланс", "кошелек", "кошелёк", "счет", "счёт", "понизить", "вернуть", "работа", "ворк"
    ]
    if any(text_lower.startswith(cmd) or text_lower.startswith("/" + cmd) for cmd in ignore_list):
        return

    # Записываем обычное текстовое сообщение в лог для памяти
    user_id = message.from_user.id
    user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    await log_chat_message(message.chat.id, user_id, user_name, message.text)

    # Проверяем триггеры для ответа
    bot_info = await bot.get_me()
    is_mentioned = f"@{bot_info.username.lower()}" in text_lower or bot_info.first_name.lower() in text_lower

    is_reply_to_bot = False
    if message.reply_to_message and message.reply_to_message.from_user:
        is_reply_to_bot = message.reply_to_message.from_user.id == bot_info.id

    # 5% шанс поддержать разговор самостоятельно
    random_interject = random.random() < 0.05

    if is_mentioned or is_reply_to_bot or random_interject:
        # Проверяем, зарегистрирован ли пользователь, прежде чем отвечать ему
        eco = await get_eco_data(user_id)
        if not eco or not eco.get("bs_tag"):
            if is_mentioned or is_reply_to_bot:
                await message.reply(
                    "❌ Я общаюсь только с верифицированными участниками клуба. Отправь мне свой тег в ЛС!")
            return

        # Показываем статус "печатает..."
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")

        # Собираем данные
        current_mode = await get_chat_mode(message.chat.id)
        system_prompt = AI_PROMPTS.get(current_mode, AI_PROMPTS["default"])
        history = await get_chat_context(message.chat.id, limit=15)

        # Получаем ответ от ИИ
        ai_response = await ask_groq(system_prompt, history, f"{user_name}: {message.text}")

        # Чтобы ИИ не путал логику, его личные сообщения в памяти будут начинаться с префикса 🤖
        formatted_response = f"🤖 {ai_response}"

        # Отправляем ответ
        await message.reply(formatted_response, parse_mode=None)  # Без parse_mode, чтобы ИИ случайно не сломал маркдаун
        # Логируем ответ бота
        await log_chat_message(message.chat.id, bot_info.id, bot_info.first_name, formatted_response)