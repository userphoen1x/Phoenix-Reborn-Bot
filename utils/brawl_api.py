import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

CURRENT_API_KEY = os.getenv("BS_API_KEY", "")

initial_tags = os.getenv("CLAN_TAGS", "")
CLAN_TAGS = [tag.strip().replace("%23", "#") for tag in initial_tags.split(",") if tag.strip()]


def update_api_key(new_key: str):
    global CURRENT_API_KEY
    CURRENT_API_KEY = new_key


async def check_player(player_tag: str):
    if not CURRENT_API_KEY:
        return {"success": False, "error": "api_key_missing"}

    clean_tag = player_tag.replace("#", "").upper()
    url = f"https://api.brawlstars.com/v1/players/%23{clean_tag}"
    headers = {"Authorization": f"Bearer {CURRENT_API_KEY}"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    player_name = data.get("name", "Неизвестно")
                    club_tag = data.get("club", {}).get("tag", "Без клуба")

                    if club_tag in CLAN_TAGS:
                        return {"success": True, "status": "member", "name": player_name}
                    else:
                        return {"success": True, "status": "not_member", "name": player_name}

                elif response.status == 404:
                    return {"success": False, "error": "not_found"}
                elif response.status == 403:
                    return {"success": False, "error": "forbidden_ip"}
                else:
                    return {"success": False, "error": "api_error"}
        except Exception:
            return {"success": False, "error": "connection_error"}