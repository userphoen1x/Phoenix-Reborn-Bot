from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database.repositories.user_repo import UserRepository
from external.brawl_api import BrawlAPIClient
from core.config import settings
from core.lexicon import LEXICON

router = Router()
router.message.filter(F.chat.type == "private")


class RegState(StatesGroup):
    tag = State()


async def get_user_chat_status(bot: Bot, user_id: int):
    try:
        member = await bot.get_chat_member(int(settings.TARGET_CHAT_ID), user_id)
        status = str(member.status).lower()
        if 'kicked' in status or 'banned' in status or 'left' in status:
            return False, True
        return True, False
    except Exception:
        return False, False


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot: Bot, user_repo: UserRepository,
                    brawl_client: BrawlAPIClient):
    user_id = message.from_user.id
    wait_msg = await message.answer(LEXICON["reg_wait"])

    try:
        in_chat, is_banned = await get_user_chat_status(bot, user_id)

        if is_banned:
            return await wait_msg.edit_text(LEXICON["reg_banned"])

        all_users = await user_repo.get_all_users_for_roles()
        current_user = next((u for u in all_users if u["user_id"] == user_id), None)

        if current_user is not None:
            bs_tag = current_user.get("tag", "")
            live_stats = await brawl_client.get_player_stats(bs_tag)

            player_club_tag = live_stats.get("club", {}).get("tag", "") if live_stats else ""
            in_club = player_club_tag in settings.CLAN_TAGS

            if not in_club and not in_chat:
                await wait_msg.edit_text(LEXICON["reg_not_in_club_deny"])
            elif not in_club and in_chat:
                await user_repo.set_user_role(user_id, "Гость", "Одобрен")
                await wait_msg.edit_text(LEXICON["reg_not_in_club_guest"])
            elif in_club and not in_chat:
                try:
                    link = await bot.create_chat_invite_link(int(settings.TARGET_CHAT_ID), member_limit=1)
                    await wait_msg.edit_text(LEXICON["reg_in_club_invite"].format(link=link.invite_link))
                except Exception as e:
                    await wait_msg.edit_text(LEXICON["reg_invite_error"].format(error=e))
            elif in_club and in_chat:
                await wait_msg.edit_text(LEXICON["reg_perfect"])
            return

        if in_chat:
            await wait_msg.edit_text(LEXICON["reg_prompt_tag_chat"])
        else:
            await wait_msg.edit_text(LEXICON["reg_prompt_tag_pm"])

        await state.set_state(RegState.tag)
    except Exception as e:
        await wait_msg.edit_text(LEXICON["error_generic"].format(error=e), parse_mode="HTML")


@router.message(RegState.tag)
async def process_tag(message: Message, state: FSMContext, bot: Bot, user_repo: UserRepository,
                      brawl_client: BrawlAPIClient):
    tag = message.text.strip().upper()
    if not tag.startswith("#"):
        tag = "#" + tag

    user_id = message.from_user.id
    wait_msg = await message.answer(LEXICON["reg_search_tag"])

    try:
        in_chat, is_banned = await get_user_chat_status(bot, user_id)

        if is_banned:
            await state.clear()
            return await wait_msg.edit_text(LEXICON["reg_banned"])

        player_stats = await brawl_client.get_player_stats(tag)
        if not player_stats:
            return await wait_msg.edit_text(LEXICON["reg_tag_not_found"])

        player_club_tag = player_stats.get("club", {}).get("tag", "")
        in_club = player_club_tag in settings.CLAN_TAGS

        if not in_club and not in_chat:
            await state.clear()
            return await wait_msg.edit_text(LEXICON["reg_not_in_club_deny"])

        player_name = player_stats.get("name", "Игрок")
        await user_repo.register_user(user_id, tag, player_name,
                                      message.from_user.username or message.from_user.full_name)

        if not in_club and in_chat:
            await user_repo.set_user_role(user_id, "Гость", "Одобрен")
            await wait_msg.edit_text(LEXICON["reg_success_guest"])
        elif in_club and not in_chat:
            role_ru = "Участник"
            r_status = "Одобрен"
            await user_repo.set_user_role(user_id, role_ru, r_status)

            try:
                link = await bot.create_chat_invite_link(int(settings.TARGET_CHAT_ID), member_limit=1)
                await wait_msg.edit_text(LEXICON["reg_success_invite"].format(role=role_ru, link=link.invite_link),
                                         parse_mode="HTML")
            except Exception as e:
                await wait_msg.edit_text(LEXICON["reg_invite_error"].format(error=e))
        elif in_club and in_chat:
            role_ru = "Участник"
            r_status = "Одобрен"
            await user_repo.set_user_role(user_id, role_ru, r_status)
            await wait_msg.edit_text(LEXICON["reg_success_update"].format(role=role_ru), parse_mode="HTML")

        await state.clear()

    except Exception as e:
        await wait_msg.edit_text(LEXICON["error_generic"].format(error=e), parse_mode="HTML")
        await state.clear()