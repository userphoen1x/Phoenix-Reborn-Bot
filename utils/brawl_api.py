import aiohttp
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

CURRENT_API_KEY = os.getenv("BS_API_KEY", "")
initial_tags = os.getenv("CLAN_TAGS", "")
CLAN_TAGS = [tag.strip().replace("%23", "#") for tag in initial_tags.split(",") if tag.strip()]

CLAN_NAMES_CACHE = {}


def update_api_key(new_key: str):
    global CURRENT_API_KEY
    CURRENT_API_KEY = new_key


async def get_clan_names():
    global CLAN_NAMES_CACHE
    if CLAN_NAMES_CACHE:
        return CLAN_NAMES_CACHE

    if not CURRENT_API_KEY:
        return {tag: tag for tag in CLAN_TAGS}

    names = {}
    headers = {"Authorization": f"Bearer {CURRENT_API_KEY}"}
    async with aiohttp.ClientSession() as session:
        for tag in CLAN_TAGS:
            clean_tag = tag.replace("#", "")
            url = f"https://api.brawlstars.com/v1/clubs/%23{clean_tag}"
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        names[tag] = data.get("name", tag)
                    else:
                        names[tag] = tag
            except:
                names[tag] = tag

    CLAN_NAMES_CACHE = names
    return names


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
                    return True, "✅ Соединение установлено (200 OK)."
                return False, f"⚠️ Ошибка: Код {resp.status}"
    except Exception as e:
        return False, f"❌ Ошибка: {e}"


async def check_player(player_tag: str):
    if not CURRENT_API_KEY: return {"success": False, "error": "api_key_missing"}
    clean_tag = player_tag.replace("#", "").upper()
    url = f"https://api.brawlstars.com/v1/players/%23{clean_tag}"
    headers = {"Authorization": f"Bearer {CURRENT_API_KEY}"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    club_data = data.get("club", {})
                    return {
                        "success": True,
                        "status": "member" if club_data.get("tag") in CLAN_TAGS else "not_member",
                        "name": data.get("name", "Неизвестно"),
                        "club_name": club_data.get("name", "Phoenix Reborn")
                    }
                return {"success": False, "error": "api_error"}
        except:
            return {"success": False, "error": "connection_error"}


async def get_player_stats(player_tag: str):
    if not CURRENT_API_KEY: return None
    clean_tag = player_tag.replace("#", "").upper()
    url = f"https://api.brawlstars.com/v1/players/%23{clean_tag}"
    headers = {"Authorization": f"Bearer {CURRENT_API_KEY}"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    ranked_curr = data.get("highestRankedElo", data.get("rankedElo", 0))
                    ranked_high = data.get("highestRankedElo", 0)
                    return {
                        "trophies": data.get("trophies", 0),
                        "solo_wins": data.get("soloVictories", 0),
                        "duo_wins": data.get("duoVictories", 0),
                        "wins_3v3": data.get("3vs3Victories", 0),
                        "exp_level": data.get("expLevel", 0),
                        "ranked_curr": ranked_curr,
                        "ranked_high": ranked_high
                    }
                return None
        except:
            return None


async def get_all_club_members(specific_club: str = None):
    if not CURRENT_API_KEY: return [], "Нет ключа"
    all_members = []
    errors = []
    headers = {"Authorization": f"Bearer {CURRENT_API_KEY}"}
    tags_to_check = [f"#{specific_club}"] if specific_club and specific_club != "ALL" else CLAN_TAGS
    async with aiohttp.ClientSession() as session:
        for c_tag in tags_to_check:
            clean_tag = c_tag.replace("#", "")
            url = f"https://api.brawlstars.com/v1/clubs/%23{clean_tag}"
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        members = data.get("members", [])
                        for m in members:
                            all_members.append(
                                {"name": m.get("name"), "tag": m.get("tag"), "trophies": m.get("trophies", 0)})
                    else:
                        errors.append(f"Код {response.status}")
            except Exception as e:
                errors.append(str(e))
            await asyncio.sleep(0.1)
    return all_members, " | ".join(errors) if errors else None


async def get_live_club_detailed_stats(specific_club: str = None):
    all_members, err = await get_all_club_members(specific_club)
    if not all_members: return [], err
    sem = asyncio.Semaphore(10)

    async def fetch_for_member(m):
        async with sem:
            await asyncio.sleep(0.1)
            stats = await get_player_stats(m["tag"])
            if stats:
                m.update(stats)
            else:
                m.update(
                    {"solo_wins": 0, "duo_wins": 0, "wins_3v3": 0, "exp_level": 0, "ranked_curr": 0, "ranked_high": 0})
            return m

    tasks = [fetch_for_member(m) for m in all_members]
    detailed_members = await asyncio.gather(*tasks)
    return detailed_members, err