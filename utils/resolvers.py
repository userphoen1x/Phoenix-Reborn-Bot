from aiogram.types import Message
from database.repositories.user_repo import UserRepository


async def resolve_target(message: Message, user_repo: UserRepository) -> tuple[int | None, str | None]:
    parts = message.text.split()
    target_username = next((word for word in parts[1:] if word.startswith("@")), None)

    if target_username:
        all_users = await user_repo.get_all_users_for_roles()
        for u in all_users:
            tg_name = u.get("tg_name", "")
            if tg_name:
                check_name = tg_name.lower() if tg_name.startswith("@") else f"@{tg_name.lower()}"
                if check_name == target_username.lower():
                    return u["user_id"], target_username
    elif message.reply_to_message:
        u = message.reply_to_message.from_user
        t_name = f"@{u.username}" if u.username else u.full_name
        return u.id, t_name

    return None, None