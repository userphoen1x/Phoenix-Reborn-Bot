import os
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, \
    LinkPreviewOptions
from dishka.integrations.aiogram import inject, FromDishka

from database.repositories.user_repo import UserRepository
from external.brawl_api import BrawlAPIClient
from core.config import settings
from core.constants import DELAYS
from core.lexicon import LEXICON
from core.garbage_collector import schedule_delete

router = Router()


def is_tech_admin(user_id: int) -> bool:
    return str(user_id) == settings.FOUNDER_ID or str(user_id) in settings.DEVELOPER_IDS


@router.message(Command("unlink"))
@inject
async def cmd_unlink_tag(message: Message, user_repo: FromDishka[UserRepository]):
    if not is_tech_admin(message.from_user.id): return
    parts = message.text.split()
    target_name = None
    if len(parts) > 1 and parts[1].startswith("@"):
        target_name = parts[1]
    elif message.reply_to_message:
        u = message.reply_to_message.from_user
        target_name = f"@{u.username}" if u.username else u.full_name
    if not target_name:
        await message.answer(LEXICON["mod_err_no_target"])
        return
    res = await user_repo.unlink_user_tag(target_name)
    if res:
        await message.answer(LEXICON["fnd_unlink_success"].format(target=target_name))
    else:
        await message.answer(LEXICON["profile_not_found_db"].format(target=target_name))


@router.message(Command("set_key"))
@inject
async def cmd_set_key(message: Message, brawl_client: FromDishka[BrawlAPIClient]):
    if not is_tech_admin(message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer(LEXICON["fnd_err_no_key"], parse_mode="HTML")
    new_key = parts[1].strip()
    settings.BS_API_KEY = new_key
    wait_msg = await message.answer(LEXICON["fnd_key_check"])
    is_valid, status_msg = await brawl_client.check_api_connection()
    if is_valid:
        await wait_msg.edit_text(LEXICON["fnd_key_ok"], parse_mode="HTML")
    else:
        await wait_msg.edit_text(LEXICON["fnd_key_fail"].format(error=status_msg), parse_mode="HTML")
    try:
        await message.delete()
    except:
        pass


@router.message(Command("ping"))
@inject
async def admin_ping(message: Message, brawl_client: FromDishka[BrawlAPIClient]):
    if not is_tech_admin(message.from_user.id): return
    wait_msg = await message.answer(LEXICON["fnd_ping_check"])
    ok, text = await brawl_client.check_api_connection()
    await wait_msg.edit_text(LEXICON["fnd_ping_res"].format(text=text))


@router.message(Command("get_db"))
async def admin_get_db(message: Message):
    if not is_tech_admin(message.from_user.id): return
    if os.path.exists(settings.DB_PATH):
        await message.answer_document(document=FSInputFile(settings.DB_PATH), caption=LEXICON["fnd_db_caption"])
    else:
        await message.answer(LEXICON["fnd_db_fail"])


@router.message(Command("force_roles"))
async def cmd_force_roles(message: Message, bot: Bot):
    if not is_tech_admin(message.from_user.id): return
    await message.answer(LEXICON["fnd_force_roles_start"])
    from scheduler.jobs import check_roles
    await check_roles(bot)
    await message.answer(LEXICON["fnd_force_roles_ok"])


@router.callback_query(F.data.startswith("role_approve:"))
@inject
async def approve_role(callback: CallbackQuery, bot: Bot, user_repo: FromDishka[UserRepository]):
    if str(callback.from_user.id) != settings.FOUNDER_ID:
        return await callback.answer(LEXICON["fnd_no_rights"], show_alert=True)

    _, uid_str, role_eng = callback.data.split(":")
    user_id = int(uid_str)
    role_ru = {"president": "Президент", "vicePresident": "Вице-президент"}.get(role_eng, "Участник")

    user_data = await user_repo.get_user_data(user_id)
    if not user_data:
        return await callback.message.edit_text(LEXICON["fnd_role_err_db"])

    try:
        await user_repo.set_user_role(user_id, role_ru, "Одобрен")
        await callback.message.edit_text(LEXICON["fnd_role_ok"].format(role=role_ru, user_id=user_id),
                                         parse_mode="HTML")
    except Exception as e:
        await callback.message.edit_text(LEXICON["fnd_role_db_err"].format(error=e))


@router.callback_query(F.data.startswith("role_reject:"))
@inject
async def reject_role(callback: CallbackQuery, user_repo: FromDishka[UserRepository]):
    if str(callback.from_user.id) != settings.FOUNDER_ID: return await callback.answer(LEXICON["fnd_no_rights"],
                                                                                       show_alert=True)
    _, uid_str = callback.data.split(":")
    user_id = int(uid_str)
    await user_repo.set_user_role(user_id, "Участник", "Отклонен")
    await callback.message.edit_text(LEXICON["fnd_role_reject"].format(user_id=user_id))


@router.message(F.text.lower().startswith(("запросы", "/запросы")))
@inject
async def cmd_resend_requests(message: Message, bot: Bot, user_repo: FromDishka[UserRepository],
                              brawl_client: FromDishka[BrawlAPIClient]):
    if not is_tech_admin(message.from_user.id): return

    db_users = await user_repo.get_all_users_for_roles()
    pending_users = [u for u in db_users if u["role_status"] == "Ожидает"]

    if not pending_users:
        sent = await message.answer(LEXICON["fnd_req_empty"])
        schedule_delete(sent, DELAYS["short"])
        return

    wait_msg = await message.answer(LEXICON["fnd_req_check"])
    members, _ = await brawl_client.get_all_club_members()

    role_translation = {"president": "Президент", "vicePresident": "Вице-президент", "senior": "Ветеран",
                        "member": "Участник"}
    api_roles = {m["tag"]: role_translation.get(m.get("role", "member"), "Участник") for m in members}

    count = 0
    for user in pending_users:
        u_id = user["user_id"]
        tag = user["tag"]
        tg_name = user["tg_name"]
        player_name = user["name"]
        club_name = user["club_name"]

        api_role = api_roles.get(tag)

        if not api_role or api_role not in ["Президент", "Вице-президент"]:
            await user_repo.set_user_role(u_id, api_role if api_role else "Гость", "Одобрен")
            continue

        display_tg = tg_name if tg_name and tg_name.startswith("@") else f"@{tg_name}" if tg_name else "Игрок"
        role_eng = "president" if api_role == "Президент" else "Вице-президент"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data=f"role_approve:{u_id}:{role_eng}")],
            [InlineKeyboardButton(text="Нет", callback_data=f"role_reject:{u_id}")]
        ])

        msg_text = LEXICON["fnd_req_resend"].format(display_tg=display_tg, u_id=u_id, player_name=player_name, tag=tag,
                                                    club_name=club_name, api_role=api_role)

        try:
            if settings.FOUNDER_ID:
                await bot.send_message(settings.FOUNDER_ID, msg_text, reply_markup=kb, parse_mode="HTML")
                count += 1
        except Exception:
            pass

    await wait_msg.edit_text(LEXICON["fnd_req_sent"].format(count=count))


@router.message(Command("force_scan"), F.chat.type == "private")
async def admin_force_scan(message: Message):
    if not is_tech_admin(message.from_user.id): return

    sent_msg = await message.answer(LEXICON["fnd_scan_start"])
    from scheduler.jobs import collect_daily_stats
    await collect_daily_stats()
    await sent_msg.edit_text(LEXICON["fnd_scan_ok"])


@router.message(Command("all_reg_list"), F.chat.type == "private")
@inject
async def cmd_all_reg_list(message: Message, user_repo: FromDishka[UserRepository]):
    a_role = await user_repo.get_user_role(message.from_user.id)
    if not is_tech_admin(message.from_user.id) and a_role not in ["Президент", "Вице-президент"]:
        return

    users = await user_repo.get_all_registered_users()
    if not users:
        await message.answer(LEXICON["fnd_reg_empty"])
        return

    lines = [LEXICON["fnd_reg_list_title"]]
    for i, (tg_name, tag, player_name) in enumerate(users, 1):
        name_str = tg_name if tg_name.startswith("@") else f"<b>{tg_name}</b>"
        lines.append(f"{i}. {name_str} привязан к тегу {tag} ({player_name})")

    text = "\n".join(lines)
    for x in range(0, len(text), 4000):
        await message.answer(
            text[x:x + 4000],
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )