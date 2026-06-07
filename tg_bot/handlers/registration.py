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
    wait_msg = await message.answer("⏳ Проверяю данные...")

    try:
        in_chat, is_banned = await get_user_chat_status(bot, user_id)

        if is_banned:
            return await wait_msg.edit_text("❌ Вам запрещен доступ в группу (бан).")

        all_users = await user_repo.get_all_users_for_roles()
        current_user = next((u for u in all_users if u["user_id"] == user_id), None)

        if current_user is not None:
            bs_tag = current_user.get("tag", "")
            live_stats = await brawl_client.get_player_stats(bs_tag)

            player_club_tag = live_stats.get("club", {}).get("tag", "") if live_stats else ""
            in_club = player_club_tag in settings.CLAN_TAGS

            if not in_club and not in_chat:
                await wait_msg.edit_text("⛔️ Доступ запрещен: вы не являетесь участником клубов Phoenix Family.")
            elif not in_club and in_chat:
                await user_repo.set_user_role(user_id, "Гость", "Одобрен")
                await wait_msg.edit_text("Вы не в клубах семейства. Вам автоматически выдано звание 'Гость'.")
            elif in_club and not in_chat:
                try:
                    link = await bot.create_chat_invite_link(int(settings.TARGET_CHAT_ID), member_limit=1)
                    await wait_msg.edit_text(
                        f"✅ Вы состоите в клубе!\nВот ваша индивидуальная ссылка для входа:\n{link.invite_link}")
                except Exception as e:
                    await wait_msg.edit_text(f"❌ Ошибка создания ссылки.\nДетали: {e}")
            elif in_club and in_chat:
                await wait_msg.edit_text("✅ Всё настроено идеально! Вы есть в клубе и в чате.")
            return

        if in_chat:
            await wait_msg.edit_text("Привяжите ваш игровой тег (напишите его следующим сообщением).")
        else:
            await wait_msg.edit_text("Для получения доступа в чат привяжите ваш игровой тег.")

        await state.set_state(RegState.tag)
    except Exception as e:
        await wait_msg.edit_text(f"❌ Произошла системная ошибка:\n<code>{e}</code>", parse_mode="HTML")


@router.message(RegState.tag)
async def process_tag(message: Message, state: FSMContext, bot: Bot, user_repo: UserRepository,
                      brawl_client: BrawlAPIClient):
    tag = message.text.strip().upper()
    if not tag.startswith("#"):
        tag = "#" + tag

    user_id = message.from_user.id
    wait_msg = await message.answer("⏳ Ищу ваш тег в базе Supercell...")

    try:
        in_chat, is_banned = await get_user_chat_status(bot, user_id)

        if is_banned:
            await state.clear()
            return await wait_msg.edit_text("❌ Вам запрещен доступ в группу.")

        player_stats = await brawl_client.get_player_stats(tag)
        if not player_stats:
            return await wait_msg.edit_text("❌ Тег не найден. Проверьте правильность и отправьте снова.")

        player_club_tag = player_stats.get("club", {}).get("tag", "")
        in_club = player_club_tag in settings.CLAN_TAGS

        if not in_club and not in_chat:
            await state.clear()
            return await wait_msg.edit_text("⛔️ Доступ запрещен: этот тег не состоит в клубах Phoenix Family.")

        player_name = player_stats.get("name", "Игрок")
        await user_repo.register_user(user_id, tag, player_name,
                                      message.from_user.username or message.from_user.full_name)

        if not in_club and in_chat:
            await user_repo.set_user_role(user_id, "Гость", "Одобрен")
            await wait_msg.edit_text("✅ Тег привязан. Так как вы не состоите в клубах, вам выдано звание 'Гость'.")
        elif in_club and not in_chat:
            role_ru = "Участник"
            r_status = "Одобрен"
            await user_repo.set_user_role(user_id, role_ru, r_status)

            try:
                link = await bot.create_chat_invite_link(int(settings.TARGET_CHAT_ID), member_limit=1)
                await wait_msg.edit_text(
                    f"✅ Тег успешно привязан!\nВ игре у вас статус: <b>{role_ru}</b>.\n\nВот ваша ссылка для входа в чат:\n{link.invite_link}",
                    parse_mode="HTML")
            except Exception as e:
                await wait_msg.edit_text(f"✅ Тег привязан!\n❌ Ошибка создания ссылки (нет прав).\nДетали: {e}")
        elif in_club and in_chat:
            role_ru = "Участник"
            r_status = "Одобрен"
            await user_repo.set_user_role(user_id, role_ru, r_status)
            await wait_msg.edit_text(f"✅ Тег успешно привязан!\nВаше звание обновлено: <b>{role_ru}</b>.",
                                     parse_mode="HTML")

        await state.clear()

    except Exception as e:
        await wait_msg.edit_text(f"❌ Произошла системная ошибка:\n<code>{e}</code>", parse_mode="HTML")
        await state.clear()