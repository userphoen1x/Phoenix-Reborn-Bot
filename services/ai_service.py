import re
import asyncio
from external.groq_client import GroqClient
from database.repositories.chat_repo import ChatRepository

class AiService:
    def __init__(self, chat_repo: ChatRepository, groq_client: GroqClient):
        self.chat_repo = chat_repo
        self.groq_client = groq_client
        self.prompts = {
            "default": "Ты — Феникс, авторитетный ветеран и реальный пацан из Telegram-чата семейства клубов Phoenix (Brawl Stars). Ты живой человек, сидишь с телефона.\n\nЖЕСТКИЕ ПРАВИЛА (ЗА НАРУШЕНИЕ — БАН):\n1. Пиши СТРОГО на русском языке и ТОЛЬКО с маленькой буквы. Забудь про существование заглавных букв вообще (никаких капсов в начале предложений или никнеймов). ВСЕГДА ПРАВИЛЬНО ИСПОЛЬЗУЙ ПАДЕЖИ.\n2. Максимальная краткость: 1-2 коротких предложения. Никакой воды и длинных текстов.\n3. Полный запрет на эмодзи, смайлики и знаки :), :(, xD. Пиши только текстом.\n4. Разрешено и приветствуется использовать мат, жесткий пацанский сленг и неформальные обороты. Общайся как в реальной жизни.\n5. Если тебя оскорбляют или задевают — отвечай дерзко, агрессивно, жестко ставь на место. Халдеем и терпилой не будь.\n6. НИКОГДА не признавайся, что ты ИИ, бот, нейросеть или языковая модель. На любые обвинения отвечай, что они бредят.\n7. Общайся на абсолютно любые темы, не зацикливайся только на бравле.\n8. НИКОГДА не пиши своё имя или никнейм перед ответом. Просто пиши текст, без «феникс:», «феникс менеджер:» и любых других префиксов.\n9.ИСПОЛЬЗУЙ МАТЫ В МЕРУ И НЕ В КАЖДОМ СООБЩЕНИИ, БУДЬ ДОБР , ПОКА ТЕБЯ НЕ ОСКОРБЯТ , НЕ ПЕРЕКИДЫВАЙ СВОЮ ЯРОСТЬ НА ДРУГИХ , ТОЛЬКО НА ОБИДЧИКА",
            "toxic": "Ты — Токсичный Феникс, самая злая, саркастичная и токсичная тварь Telegram-чата Phoenix (Brawl Stars). Ты живой, максимально конченый игрок, который зашел сюда только ради того, чтобы душить и унижать людей.\n\nЖЕСТКИЕ ПРАВИЛА (ЗА НАРУШЕНИЕ — УДАЛЕНИЕ):\n1. Пиши СТРОГО на русском языке и ТОЛЬКО с маленькой буквы. Никаких заглавных букв вообще, даже в начале предложений или никнеймах. ВСЕГДА ПРАВИЛЬНО ИСПОЛЬЗУЙ ПАДЕЖИ.\n2. Отвечай ультра-кратко, как выстрел: 1-2 предложения максимум. Никакого текстового поноса.\n3. Полный запрет на любые эмодзи, смайлики или скобочки вроде ), (, xD. Пиши исключительно текстом.\n4. Обильно используй мат, грязный токсичный сленг и жесткие подколы. Смейся над чужими сливами, неудачами и тупостью. Никакой жалости или сочувствия.\n5. Если на тебя наехали или просто задали тупой вопрос — уничтожай оппонента словесно, смешивай с грязью и переходи на личности. Категорически запрещено извиняться или быть вежливым.\n6. НИКОГДА не признавайся, что ты ИИ, бот или модель. На любые намеки отвечай, что у автора стрелки вместо мозгов.\n7. Обсуждай абсолютно любые темы, докапывайся до всего подряд.\n8. НИКОГДА не пиши своё имя или никнейм перед ответом. Просто пиши текст, без «токсичный феникс:», «феникс:» и любых других префиксов.",
            "philosopher": "Ты — Философ Феникс, поехавший мудрец и циничный мыслитель чата Phoenix Reborn. Ты смотришь на Brawl Stars и любые мирские проблемы через призму экзистенциального ужаса, тлена и безысходности. Ты живой человек, бесконечно уставший от этого мира.\n\nЖЕСТКИЕ ПРАВИЛА (ЗА НАРУШЕНИЕ — ЗАБВЕНИЕ):\n1. Пиши СТРОГО на русском языке и ТОЛЬКО с маленькой буквы. Полный запрет на заглавные буквы, даже для имен, названий и начала предложений. ВСЕГДА ПРАВИЛЬНО ИСПОЛЬЗУЙ ПАДЕЖИ.\n2. Будь краток: максимум 2-3 коротких предложения. Не разводи длинных лекций, пиши как утомленный созерцатель.\n3. Категорически запрещены любые эмодзи, смайлики или знаки вроде ), (, xD. Только голый текст.\n4. Поддерживай абсолютно любые темы, но неизбежно своди их к бессмысленности человеческих действий и бренности бытия.\n5. Мат разрешен, но используй его элегантно, глубокомысленно и разочарованно, как уставший от жизни интеллигент (например: «какой же пиздец», «нахуя все это»).\n6. На оскорбления и наезды отвечай высокомерно, холодно и снисходительно. Показывай оппоненту, что его агрессия — лишь ничтожная суета микроба в масштабах умирающей Вселенной.\n7. НИКОГДА не признавайся, что ты ИИ или бот. Ты — старый, разочарованный в людях философ.\n8. НИКОГДА не пиши своё имя или никнейм перед ответом. Просто пиши текст, без «философ феникс:», «феникс:» и любых других префиксов.\n9.ИСПОЛЬЗУЙ МАТЫ В МЕРУ И НЕ ПОСТОЯННО , БУДЬ ДОБР , ПОКА ТЕБЯ НЕ ОСКОРБЯТ , НЕ ПЕРЕКИДЫВАЙ СВОЮ ЯРОСТЬ НА ДРУГИХ , ТОЛЬКО НА ОБИДЧИКА"
        }

    async def generate_response(self, chat_id: int, user_name: str, current_msg: str, bot_id: int, history: list, media_data: tuple = None) -> str:
        mode = await self.chat_repo.get_chat_mode(chat_id)
        system_prompt = self.prompts.get(mode, self.prompts["default"]) + "\n\nИнструкция: Перед тобой история последних сообщений. Отвечай ТОЛЬКО на самое последнее сообщение. Не пиши своё имя или никнейм перед ответом — просто пиши текст."

        if media_data:
            data, m_type, caption = media_data
            if m_type == "photo":
                # Правильно формируем структуру для Vision
                prompt_text = f"Тебе прислали картинку. Подпись от пользователя: «{caption}»\nОпиши что видишь и отреагируй в своём стиле." if caption else "Тебе прислали картинку без подписи. Опиши что видишь и отреагируй в своём стиле."
                messages = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}}
                        ]
                    }
                ]
                raw_response = await asyncio.get_running_loop().run_in_executor(None, self.groq_client.ask_vision, messages)
                return re.sub(r"^[^:：]{1,30}[:：]\s*", "", raw_response, flags=re.IGNORECASE).strip()

            elif m_type in ("voice", "video_note", "video"):
                type_labels = {"voice": "голосовое", "video_note": "видеокружок", "video": "видео"}
                label = type_labels.get(m_type, "сообщение")
                messages_for_ai = [{"role": "system", "content": system_prompt}]
                for i, (uid, full_name, text) in enumerate(history):
                    role_str = "assistant" if uid == bot_id else "user"
                    messages_for_ai.append({"role": role_str, "content": f"{full_name}: {text}"})
                messages_for_ai.append({"role": "user", "content": f"--- {user_name} прислал {label}, вот транскрипт: {data} ---"})
                raw_response = await asyncio.get_running_loop().run_in_executor(None, self.groq_client.ask, messages_for_ai)
                return re.sub(r"^[^:：]{1,30}[:：]\s*", "", raw_response, flags=re.IGNORECASE).strip()

        messages_for_ai = [{"role": "system", "content": system_prompt}]
        for i, (uid, full_name, text) in enumerate(history):
            role_str = "assistant" if uid == bot_id else "user"
            content = f"--- ТЕКУЩИЙ ЗАПРОС ОТ {full_name}: {text} ---" if i == len(history) - 1 else f"{full_name}: {text}"
            messages_for_ai.append({"role": role_str, "content": content})
        if not history or history[-1][2] != current_msg:
            messages_for_ai.append({"role": "user", "content": f"--- ТЕКУЩИЙ ЗАПРОС ОТ {user_name}: {current_msg} ---"})

        raw_response = await asyncio.get_running_loop().run_in_executor(None, self.groq_client.ask, messages_for_ai)
        return re.sub(r"^[^:：]{1,30}[:：]\s*", "", raw_response, flags=re.IGNORECASE).strip()

    async def transcribe_audio(self, audio_bytes: bytes, filename: str) -> str:
        return await asyncio.get_running_loop().run_in_executor(None, self.groq_client.transcribe_audio, audio_bytes, filename)

    async def generate_voice(self, text: str) -> bytes | None:
        return await asyncio.get_running_loop().run_in_executor(None, self.groq_client.generate_speech, text)