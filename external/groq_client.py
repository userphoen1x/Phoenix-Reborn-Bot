import logging
from groq import Groq
from core.config import settings

class GroqClient:
    def __init__(self):
        self.smart_model = "llama-3.3-70b-versatile"
        self.cheap_model = "llama-3.1-8b-instant"
        self._key_index = 0

    def ask(self, messages: list, max_tokens: int = 150) -> str:
        keys = settings.GROQ_KEYS
        if not keys: return "Ошибка: В Railway не указаны ключи Groq!"
        for model in [self.smart_model, self.cheap_model]:
            for _ in range(len(keys)):
                try:
                    client = Groq(api_key=keys[self._key_index])
                    res = client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens, temperature=0.85)
                    return res.choices[0].message.content
                except Exception as e:
                    logging.warning(e)
                    self._key_index = (self._key_index + 1) % len(keys)
        return "❌ Все ключи API сейчас перегружены. Попробуй позже."