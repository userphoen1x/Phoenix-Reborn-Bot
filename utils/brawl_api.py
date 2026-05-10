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