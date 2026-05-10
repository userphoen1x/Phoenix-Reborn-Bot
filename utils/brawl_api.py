async def get_all_club_members():
    if not CURRENT_API_KEY:
        return []

    all_members = []
    headers = {"Authorization": f"Bearer {CURRENT_API_KEY}"}

    async with aiohttp.ClientSession() as session:
        for c_tag in CLAN_TAGS:
            clean_tag = c_tag.replace("#", "").upper()
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