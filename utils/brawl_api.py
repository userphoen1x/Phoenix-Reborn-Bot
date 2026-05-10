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


async def check_api_connection():
    if not CURRENT_API_KEY:
        return False, "❌ Ошибка: API ключ не установлен."
    if not CLAN_TAGS:
        return False, "❌ Ошибка: Теги кланов не настроены."

    tag = CLAN_TAGS[0].replace("#", "")
    url = f"https://api.brawlstars.com/v1/clubs/%23{tag}"
    headers = {"Authorization": f"Bearer {CURRENT_API_KEY}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    return True, "✅ Соединение с Supercell API установлено (200 OK). IP-адрес разрешен."
                elif resp.status == 403:
                    return False, "❌ Ошибка 403 (Forbidden): Доступ запрещен! Зайдите на портал разработчиков и обновите IP-адрес для ключа."
                else:
                    return False, f"⚠️ Неизвестная ошибка: Код {resp.status}"
    except Exception as e:
        return False, f"❌ Ошибка сетевого соединения: {e}"


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
                    club_data = data.get("club", {})
                    club_tag = club_data.get("tag", "Без клуба")
                    club_name = club_data.get("name", "Phoenix Reborn")

                    if club_tag in CLAN_TAGS:
                        return {"success": True, "status": "member", "name": player_name, "club_name": club_name}
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


async def get_player_stats(player_tag: str):
    if not CURRENT_API_KEY:
        return None

    clean_tag = player_tag.replace("#", "").upper()
    url = f"https://api.brawlstars.com/v1/players/%23{clean_tag}"
    headers = {"Authorization": f"Bearer {CURRENT_API_KEY}"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "trophies": data.get("trophies", 0),
                        "solo_wins": data.get("soloVictories", 0),
                        "duo_wins": data.get("duoVictories", 0),
                        "wins_3v3": data.get("3vs3Victories", 0),
                        "rank_current": data.get("highestTrophies", 0),
                        "rank_highest": data.get("highestTrophies", 0)
                    }
                return None
        except Exception:
            return None


async def get_all_club_members(specific_club: str = None):
    if not CURRENT_API_KEY:
        return []

    all_members = []
    headers = {"Authorization": f"Bearer {CURRENT_API_KEY}"}

    tags_to_check = CLAN_TAGS
    if specific_club and specific_club != "ALL":
        tags_to_check = [specific_club]

    async with aiohttp.ClientSession() as session:
        for c_tag in tags_to_check:
            clean_tag = c_tag.replace("#", "")
            url = f"https://api.brawlstars.com/v1/clubs/%23{clean_tag}"
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        members = data.get("memberList", [])
                        for m in members:
                            all_members.append({
                                "name": m.get("name"),
                                "tag": m.get("tag"),
                                "trophies": m.get("trophies"),
                                "club": data.get("name")
                            })
            except Exception:
                continue
    return all_members