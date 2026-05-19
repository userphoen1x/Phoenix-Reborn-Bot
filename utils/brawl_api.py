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
    if CLAN_NAMES_CACHE: return CLAN_NAMES_CACHE
    if not CURRENT_API_KEY: return {tag: tag for tag in CLAN_TAGS}
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
    if not CURRENT_API_KEY: return False, "Ошибка: API ключ не установлен."
    if not CLAN_TAGS: return False, "Ошибка: Теги кланов не настроены."
    tag = CLAN_TAGS[0].replace("#", "")
    url = f"https://api.brawlstars.com/v1/clubs/%23{tag}"
    headers = {"Authorization": f"Bearer {CURRENT_API_KEY}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    return True, "Соединение с Supercell API установлено (200 OK)."
                elif resp.status == 403:
                    return False, "Ошибка 403 (Forbidden): Обновите IP в ключе."
                elif resp.status == 429:
                    return False, "Ошибка 429: Временный бан за спам."
                return False, f"Ошибка: Код {resp.status}"
    except Exception as e:
        return False, f"Ошибка: {e}"


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
                    return {"success": True, "status": "member" if club_data.get("tag") in CLAN_TAGS else "not_member",
                            "name": data.get("name", "Неизвестно"),
                            "club_name": club_data.get("name", "Phoenix Reborn")}
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

                    # --- Парсинг скинов ---
                    skins_total = s_rare = s_srare = s_epic = s_mythic = s_leg = s_hyper = s_silver = s_gold = 0

                    for brawler in data.get("brawlers", []):
                        for skin in brawler.get("skins", []):
                            skins_total += 1
                            skin_name = skin.get("name", "").lower()

                            # Безопасное получение rarity (бывает dict, бывает строка, бывает None)
                            rarity_obj = skin.get("rarity")
                            if isinstance(rarity_obj, dict):
                                rarity_str = rarity_obj.get("name", "").lower()
                            else:
                                rarity_str = str(rarity_obj or "").lower()

                            if "true silver" in skin_name or "серебр" in skin_name:
                                s_silver += 1
                            elif "true gold" in skin_name or "золот" in skin_name:
                                s_gold += 1
                            elif "rare" in rarity_str or "редкий" in rarity_str:
                                s_rare += 1
                            elif "super rare" in rarity_str or "сверх" in rarity_str:
                                s_srare += 1
                            elif "epic" in rarity_str or "эпич" in rarity_str:
                                s_epic += 1
                            elif "mythic" in rarity_str or "мифич" in rarity_str:
                                s_mythic += 1
                            elif "legendary" in rarity_str or "легенд" in rarity_str:
                                s_leg += 1
                            elif "hyper" in rarity_str or "гипер" in rarity_str:
                                s_hyper += 1

                    return {
                        "trophies": data.get("trophies", 0),
                        "solo_wins": data.get("soloVictories", 0),
                        "duo_wins": data.get("duoVictories", 0),
                        "wins_3v3": data.get("3vs3Victories", 0),
                        "highest_trophies": data.get("highestTrophies", 0),
                        "ranked_curr_rank": data.get("rankedRank", 0),
                        "ranked_curr_elo": data.get("rankedElo", data.get("currentRankedElo", 0)),
                        # Новые поля ранкеда
                        "highestRankedLeagueSeason": data.get("highestRankedLeagueSeason",
                                                              data.get("highestRankedRank", 0)),
                        "highestRankedElo": data.get("highestRankedElo", 0),
                        # Новые поля скинов
                        "skins_total": skins_total,
                        "skins_rare": s_rare,
                        "skins_srare": s_srare,
                        "skins_epic": s_epic,
                        "skins_mythic": s_mythic,
                        "skins_leg": s_leg,
                        "skins_hyper": s_hyper,
                        "skins_silver": s_silver,
                        "skins_gold": s_gold
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
                            all_members.append({
                                "name": m.get("name"),
                                "tag": m.get("tag"),
                                "trophies": m.get("trophies", 0),
                                "role": m.get("role", "member")
                            })
                    else:
                        errors.append(f"Код {response.status}")
            except Exception as e:
                errors.append(str(e))
            await asyncio.sleep(0.05)
    return all_members, " | ".join(errors) if errors else None


async def get_live_club_detailed_stats(specific_club: str = None):
    all_members, err = await get_all_club_members(specific_club)
    if not all_members: return [], err
    sem = asyncio.Semaphore(20)

    async def fetch_for_member(m):
        async with sem:
            await asyncio.sleep(0.05)
            stats = await get_player_stats(m["tag"])
            if stats:
                m.update(stats)
            else:
                # Нулевые заглушки, если API недоступно
                m.update({"solo_wins": 0, "duo_wins": 0, "wins_3v3": 0, "highest_trophies": 0, "ranked_curr_rank": 0,
                          "ranked_curr_elo": 0, "highestRankedLeagueSeason": 0, "highestRankedElo": 0, "skins_total": 0,
                          "skins_rare": 0, "skins_srare": 0, "skins_epic": 0, "skins_mythic": 0, "skins_leg": 0,
                          "skins_hyper": 0, "skins_silver": 0, "skins_gold": 0})
            return m

    tasks = [fetch_for_member(m) for m in all_members]
    detailed_members = await asyncio.gather(*tasks)
    return detailed_members, err