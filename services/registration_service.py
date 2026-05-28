from external.brawl_api import BrawlAPIClient
from database.repositories.user_repo import UserRepository
from core.exceptions import BotBaseException

class RegistrationService:
    def __init__(self, user_repo: UserRepository, brawl_client: BrawlAPIClient):
        self.user_repo = user_repo
        self.brawl_client = brawl_client

    async def register_player(self, user_id: int, tag: str) -> dict:
        player_data = await self.brawl_client.check_player(tag)
        if not player_data["success"]:
            if player_data.get("error") == "api_error": raise BotBaseException("❌ Игрок с таким тегом не найден в Brawl Stars.")
            raise BotBaseException("❌ Проблема с подключением к API игры. Попробуйте позже.")
        player_name = player_data.get("name", "Неизвестно")
        club_name = player_data.get("club_name", "Без клуба")
        is_in_club = player_data.get("status") == "member"
        clean_tag = "#" + tag.replace("#", "").upper()
        await self.user_repo.add_user(user_id, clean_tag, player_name, club_name)
        return {"name": player_name, "club": club_name, "tag": clean_tag, "is_in_club": is_in_club}