import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("BS_API_KEY")
CLAN_TAG = os.getenv("CLAN_TAG")

async def check_player(player_tag: str):
    # Очищаем тег от решетки и делаем заглавным
    clean_tag = player_tag.replace("#", "").upper()
    url = f"https://api.brawlstars.com/v1/players/%23{clean_tag}"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    player_name = data.get("name", "Неизвестно")
                    club_tag = data.get("club", {}).get("tag", "")

                    # Сравниваем тег клуба игрока с нашим
                    if club_tag == CLAN_TAG:
                        return {"success": True, "status": "member", "name": player_name}
                    else:
                        return {"success": True, "status": "not_member", "name": player_name}
                elif response.status == 404:
                    return {"success": False, "error": "not_found"}
                else:
                    return {"success": False, "error": "api_error"}
        except Exception:
            return {"success": False, "error": "connection_error"}