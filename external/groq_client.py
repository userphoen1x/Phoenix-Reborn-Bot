import logging
from groq import Groq
from core.config import settings

class GroqClient:
    def __init__(self):
        self.smart_model = "llama-3.3-70b-versatile"
        self.cheap_model = "llama-3.1-8b-instant"
        self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.whisper_model = "whisper-large-v3-turbo"
        self.tts_model = "canopylabs/orpheus-v1-english"
        self.tts_voice = "leo"
        self._key_index = 0

    def _get_client(self) -> Groq | None:
        keys = settings.GROQ_KEYS
        if not keys: return None
        return Groq(api_key=keys[self._key_index])

    def _rotate_key(self):
        keys = settings.GROQ_KEYS
        if keys: self._key_index = (self._key_index + 1) % len(keys)

    def ask(self, messages: list, max_tokens: int = 150) -> str:
        keys = settings.GROQ_KEYS
        if not keys: return "Ошибка: В Railway не указаны ключи Groq!"
        for model in [self.smart_model, self.cheap_model]:
            for _ in range(len(keys)):
                try:
                    client = self._get_client()
                    res = client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens, temperature=0.85)
                    return res.choices[0].message.content
                except Exception as e:
                    logging.warning(e)
                    self._rotate_key()
        return "❌ Все ключи API сейчас перегружены. Попробуй позже."

    def ask_vision(self, messages: list, max_tokens: int = 200) -> str:
        keys = settings.GROQ_KEYS
        if not keys: return "Ошибка: ключи Groq не найдены."
        for _ in range(len(keys)):
            try:
                client = self._get_client()
                res = client.chat.completions.create(model=self.vision_model, messages=messages, max_tokens=max_tokens, temperature=0.85)
                return res.choices[0].message.content
            except Exception as e:
                logging.warning(e)
                self._rotate_key()
        return "не могу разглядеть что там, качество говно наверное"

    def transcribe_audio(self, audio_bytes: bytes, filename: str) -> str:
        keys = settings.GROQ_KEYS
        if not keys: return ""
        for _ in range(len(keys)):
            try:
                client = self._get_client()
                transcription = client.audio.transcriptions.create(file=(filename, audio_bytes, "audio/ogg"), model=self.whisper_model, language="ru", response_format="text")
                return transcription.strip()
            except Exception as e:
                logging.warning(e)
                self._rotate_key()
        return ""

    def generate_speech(self, text: str) -> bytes | None:
        keys = settings.GROQ_KEYS
        if not keys: return None
        tts_text = text[:200]
        for _ in range(len(keys)):
            try:
                client = self._get_client()
                response = client.audio.speech.create(model=self.tts_model, voice=self.tts_voice, input=tts_text, response_format="wav")
                return response.read()
            except Exception as e:
                logging.warning(e)
                self._rotate_key()
        return None