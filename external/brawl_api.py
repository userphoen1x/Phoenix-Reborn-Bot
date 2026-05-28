import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple
from core.config import settings

class BrawlAPIClient:
    def __init__(self):
        self._clan_names_cache = {}

    @property
    def headers(self):
        return {"Authorization": f"Bearer {settings.BS_API_KEY}"}

    async def get_clan_names(self) -> Dict[str, str]:
        if self._clan_names_cache: return self._clan_names_cache
        if not settings.BS_API_KEY: return {tag: tag for tag in settings.CLAN_TAGS}
        names = {}
        async with aiohttp.ClientSession() as session:
            for tag in settings.CLAN_TAGS:
                clean_tag = tag.replace("#", "")
                url = f"https://api.brawlstars.com/v1/clubs/%23{clean_tag}"
                try:
                    async with session.get(url, headers=self.headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            names[tag] = data.get("name", tag)
                        else: names[tag] = tag
                except Exception:
                    names[tag] = tag
        self._clan_names_cache = names
        return names

    async def check_player(self, player_tag: str) -> Dict:
        if not settings.BS_API_KEY: return {"success": False, "error": "api_key_missing"}
        clean_tag = player_tag.replace("#", "").upper()
        url = f"https://api.brawlstars.com/v1/players/%23{clean_tag}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        club_data = data.get("club", {})
                        is_member = club_data.get("tag") in settings.CLAN_TAGS
                        return {"success": True, "status": "member" if is_member else "not_member", "name": data.get("name", "Неизвестно"), "club_name": club_data.get("name", "Phoenix Reborn")}
                    return {"success": False, "error": "api_error"}
            except Exception:
                return {"success": False, "error": "connection_error"}

    async def get_player_stats(self, player_tag: str) -> Optional[Dict]:
        if not settings.BS_API_KEY: return None
        clean_tag = player_tag.replace("#", "").upper()
        url = f"https://api.brawlstars.com/v1/players/%23{clean_tag}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"trophies": data.get("trophies", 0), "solo_wins": data.get("soloVictories", 0), "duo_wins": data.get("duoVictories", 0), "wins_3v3": data.get("3vs3Victories", 0), "highest_trophies": data.get("highestTrophies", 0), "ranked_curr_rank": data.get("rankedRank", 0), "ranked_curr_elo": data.get("currentRankedElo", data.get("rankedElo", 0)), "ranked_high_rank": data.get("highestRankedRank", data.get("highestRank", 0)), "ranked_high_elo": data.get("highestRankedElo", 0)}
                    return None
            except Exception:
                return None

    async def get_all_club_members(self, specific_club: str = None) -> Tuple[List[Dict], Optional[str]]:
        if not settings.BS_API_KEY: return [], "Нет ключа"
        all_members = []
        errors = []
        tags_to_check = [f"#{specific_club}"] if specific_club and specific_club != "ALL" else settings.CLAN_TAGS
        async with aiohttp.ClientSession() as session:
            for c_tag in tags_to_check:
                clean_tag = c_tag.replace("#", "")
                url = f"https://api.brawlstars.com/v1/clubs/%23{clean_tag}"
                try:
                    async with session.get(url, headers=self.headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            for m in data.get("members", []):
                                all_members.append({"name": m.get("name"), "tag": m.get("tag"), "trophies": m.get("trophies", 0), "role": m.get("role", "member")})
                        else: errors.append(f"Код {response.status}")
                except Exception as e: errors.append(str(e))
                await asyncio.sleep(0.05)
        return all_members, " | ".join(errors) if errors else None

    async def get_live_club_detailed_stats(self, specific_club: str = None) -> Tuple[List[Dict], Optional[str]]:
        all_members, err = await self.get_all_club_members(specific_club)
        if not all_members: return [], err
        sem = asyncio.Semaphore(20)
        async def fetch_for_member(m):
            async with sem:
                await asyncio.sleep(0.05)
                stats = await self.get_player_stats(m["tag"])
                if stats: m.update(stats)
                else: m.update({"solo_wins": 0, "duo_wins": 0, "wins_3v3": 0, "highest_trophies": 0, "ranked_curr_rank": 0, "ranked_curr_elo": 0, "ranked_high_rank": 0, "ranked_high_elo": 0})
                return m
        tasks = [fetch_for_member(m) for m in all_members]
        detailed_members = await asyncio.gather(*tasks)
        return detailed_members, err