import os
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database.repositories.user_repo import UserRepository
from external.brawl_api import BrawlAPIClient
from core.config import settings

router = Router()
router.message.filter(F.chat.type == "private")


class RegState(StatesGroup):
    tag = State()


async def get_user_chat_status(bot: Bot, user_id: int):
    try:
        member = await bot.get_chat_member(settings.GROUP_ID, user_id)
        if member.status in ['kicked', 'left']:
            return False, member.status == 'kicked'
        return True, False
    except Exception:
        return False, False


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot: Bot, user_repo: UserRepository,
                    brawl_client: BrawlAPIClient):
    user_id = message.from_user.id
    in_chat, is_banned = await get_user_chat_status(bot, user_id)

    if is_banned:
        return await message.answer("❌ Вам запрещен доступ в группу.")

    is_reg = await user_repo.is_registered(user_id)

    if is_reg:
        user_data = await user_repo.get_user_data(user_id)
        bs_tag = user_data[2] if len(user_data) > 2 else ""

        clubs_members, _ = await brawl_client.get_all_club_members("ALL")
        in_club = any(m.get("tag") == bs_tag for m in clubs_members) if clubs_members else False

        if not in_club and not in_chat:
            await message.answer("Доступ запрещен: вы не являетесь участником клубов Phoenix Family.")
        elif not in_club and in_chat:
            await user_repo.set_user_role(user_id, "Гость", "Одобрен")
            await message.answer("Вы не в клубах семейства. Вам автоматически выдано звание 'Гость'.")
        elif in_club and not in_chat:
            link = await bot.create_chat_invite_link(settings.GROUP_ID, member_limit=1)
            await message.answer(f"Вы состоите в клубе! Вот ваша ссылка для входа: {link.invite_link}")
        elif in_club and in_chat:
            await message.answer("✅ Всё настроено идеально!")
        return

    if in_chat:
        await message.answer("Привяжите ваш игровой тег.")
    else:
        await message.answer("Для получения доступа в чат привяжите ваш игровой тег.")

    await state.set_state(RegState.tag)


@router.message(RegState.tag)
async def process_tag(message: Message, state: FSMContext, bot: Bot, user_repo: UserRepository,
                      brawl_client: BrawlAPIClient):
    tag = message.text.strip().upper()
    if not tag.startswith("#"):
        tag = "#" + tag

    user_id = message.from_user.id
    in_chat, is_banned = await get_user_chat_status(bot, user_id)

    if is_banned:
        await state.clear()
        return await message.answer("❌ Вам запрещен доступ в группу.")

    player_stats = await brawl_client.get_player_stats(tag)
    if not player_stats:
        return await message.answer("❌ Тег не найден. Попробуйте снова.")

    clubs_members, _ = await brawl_client.get_all_club_members("ALL")
    member_data = next((m for m in clubs_members if m.get("tag") == tag), None) if clubs_members else None
    in_club = member_data is not None

    if not in_club and not in_chat:
        await state.clear()
        return await message.answer("Доступ запрещен: вы не являетесь участником клубов Phoenix Family.")

    player_name = player_stats.get("name", "Игрок")
    await user_repo.register_user(user_id, tag, player_name, message.from_user.username or message.from_user.full_name)

    if not in_club and in_chat:
        await user_repo.set_user_role(user_id, "Гость", "Одобрен")
        await message.answer("Тег привязан. Так как вы не в клубе, вам выдано звание 'Гость'.")
    elif in_club and not in_chat:
        role_eng = member_data.get("role", "member")
        role_ru = {"president": "Президент", "vicePresident": "Вице-президент", "senior": "Ветеран",
                   "member": "Участник"}.get(role_eng, "Участник")
        r_status = "Ожидает" if role_ru in ["Президент", "Вице-президент"] else "Одобрен"
        await user_repo.set_user_role(user_id, role_ru, r_status)

        link = await bot.create_chat_invite_link(settings.GROUP_ID, member_limit=1)
        await message.answer(f"Тег привязан! Роль: {role_ru}. Ваша ссылка: {link.invite_link}")
    elif in_club and in_chat:
        role_eng = member_data.get("role", "member")
        role_ru = {"president": "Президент", "vicePresident": "Вице-президент", "senior": "Ветеран",
                   "member": "Участник"}.get(role_eng, "Участник")
        r_status = "Ожидает" if role_ru in ["Президент", "Вице-президент"] else "Одобрен"
        await user_repo.set_user_role(user_id, role_ru, r_status)
        await message.answer(f"Тег привязан! Ваше звание обновлено: {role_ru}.")

    await state.clear()