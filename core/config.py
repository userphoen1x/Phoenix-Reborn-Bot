import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    _dev_ids_raw = os.getenv("DEVELOPER_ID", "")
    DEVELOPER_IDS = [x.strip() for x in _dev_ids_raw.split(",") if x.strip()]

    FOUNDER_ID = os.getenv("FOUNDER_ID")
    TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

    _groq_keys_raw = [
        os.getenv("GROQ_API_KEY_1"),
        os.getenv("GROQ_API_KEY_2"),
        os.getenv("GROQ_API_KEY_3")
    ]
    GROQ_KEYS = [k for k in _groq_keys_raw if k]

    BS_API_KEY = os.getenv("BS_API_KEY", "")
    _clan_tags_raw = os.getenv("CLAN_TAGS", "")
    CLAN_TAGS = [tag.strip().replace("%23", "#") for tag in _clan_tags_raw.split(",") if tag.strip()]

    TOPIC_REG = os.getenv("TOPIC_REG")
    TOPIC_SESSION = os.getenv("TOPIC_SESSION")
    TOPIC_PUNISH = os.getenv("TOPIC_PUNISH")
    TOPIC_ARCHIVIST = os.getenv("TOPIC_ARCHIVIST")
    TOPIC_BACKUP = os.getenv("TOPIC_BACKUP")

    DB_PATH = "/app/data/bot_data_v3.db"


settings = Settings()