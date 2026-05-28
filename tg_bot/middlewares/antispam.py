import time
import asyncio
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, ChatPermissions
from core.config import settings
from utils.admin_logger import send_log


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self):
        self.user_tracking = {}
        self.user_punishments = {}

        self.WINDOW_SECONDS = 7
        self.MAX_POINTS = 10
        self.ESCALATION_RESET = 3600

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message) or event.chat.type not in ["group", "supergroup"]:
            return await handler(event, data)

        if str(event.chat.id) == settings.ADMIN_CHAT_ID:
            return await handler(event, data)

        user_id = event.from_user.id
        user_repo = data.get("user_repo")
        if user_repo:
            role = await user_repo.get_user_role(user_id)
            if role in ["Основатель", "Программист", "Президент", "Вице-президент"]:
                return await handler(event, data)

        weight = 1
        is_sticker = False
        file_unique_id = None

        if event.sticker:
            weight = 3
            is_sticker = True
            file_unique_id = event.sticker.file_unique_id
        elif event.animation:
            weight = 2
        elif event.text:
            weight = 1

        if user_id not in self.user_tracking:
            self.user_tracking[user_id] = {"points": 0, "last_sticker": None, "dup_count": 0}

        track = self.user_tracking[user_id]

        if is_sticker:
            if file_unique_id == track["last_sticker"]:
                track["dup_count"] += 1
                if track["dup_count"] >= 2:
                    weight *= 2
            else:
                track["last_sticker"] = file_unique_id
                track["dup_count"] = 0
        else:
            track["last_sticker"] = None
            track["dup_count"] = 0

        track["points"] += weight

        asyncio.create_task(self._remove_points(user_id, weight, self.WINDOW_SECONDS))

        if track["points"] > self.MAX_POINTS:
            return await self._punish_user(event, user_id)

        return await handler(event, data)

    async def _remove_points(self, user_id: int, weight: int, delay: int):
        await asyncio.sleep(delay)
        if user_id in self.user_tracking:
            self.user_tracking[user_id]["points"] = max(0, self.user_tracking[user_id]["points"] - weight)

    async def _punish_user(self, message: Message, user_id: int):
        now = time.time()
        if user_id not in self.user_punishments:
            self.user_punishments[user_id] = {"level": 0, "last_violation": 0}

        punish = self.user_punishments[user_id]

        if now - punish["last_violation"] > self.ESCALATION_RESET:
            punish["level"] = 0

        punish["last_violation"] = now
        punish["level"] += 1
        level = punish["level"]

        try:
            await message.delete()
        except Exception:
            pass

        u_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        bot = message.bot

        if level == 1:
            pass
        elif level == 2:
            until = datetime.now() + timedelta(minutes=15)
            try:
                await bot.restrict_chat_member(
                    message.chat.id, user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until
                )
                warn_msg = await message.answer(
                    f"🔇 {u_name}, ты превысил лимит сообщений. Мут на 15 минут для охлаждения.")
                asyncio.create_task(self._delete_later(warn_msg, 30))
                await send_log(bot, "TOPIC_PUNISH",
                               f"🚨 <b>АВТО-АНТИСПАМ</b>\nПользователь: {u_name}\nНаказание: Мут 15 минут (Уровень 2)")
            except Exception:
                pass
        else:
            until = datetime.now() + timedelta(hours=24)
            try:
                await bot.restrict_chat_member(
                    message.chat.id, user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until
                )
                warn_msg = await message.answer(
                    f"⛔️ {u_name} отправлен в длительный мут на 24 часа за игнорирование предупреждений.")
                asyncio.create_task(self._delete_later(warn_msg, 60))
                await send_log(bot, "TOPIC_PUNISH",
                               f"🚨 <b>АВТО-АНТИСПАМ</b>\nПользователь: {u_name}\nНаказание: Мут 24 часа (Уровень 3+)")
            except Exception:
                pass

        return None

    async def _delete_later(self, message: Message, delay: int):
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except Exception:
            pass