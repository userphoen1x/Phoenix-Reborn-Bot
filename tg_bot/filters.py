from aiogram.filters import BaseFilter
from aiogram.types import Message
from core.config import settings

class IsTechAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user_id = str(message.from_user.id)
        return user_id == settings.FOUNDER_ID or user_id in settings.DEVELOPER_IDS

class IsFounder(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return str(message.from_user.id) == settings.FOUNDER_ID

class IsModerator(BaseFilter):
    async def __call__(self, message: Message, user_repo) -> bool:
        if str(message.from_user.id) == settings.FOUNDER_ID:
            return True
        role = await user_repo.get_user_role(message.from_user.id)
        if role in ["Основатель", "Президент", "Вице-президент", "Лидер"]:
            all_users = await user_repo.get_all_users_for_roles()
            user = next((u for u in all_users if u["user_id"] == message.from_user.id), None)
            return user is not None and user.get("role_status") == "Одобрен"
        return False