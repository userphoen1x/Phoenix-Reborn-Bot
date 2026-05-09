import os
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from utils.brawl_api import check_player, update_api_key
from utils.database import add_user, get_user_data, save_link

router = Router()
router.message.filter(F.chat.type == "private")


class Registration(StatesGroup):
    waiting_for_tag = State()


def get_rules_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ознакомился", callback_data="rules_accepted")]
    ])


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user_id = message.from_user.id
    target_chat = os.getenv("TARGET_CHAT_ID")

    try:
        chat_member = await bot.get_chat_member(chat_id=target_chat, user_id=user_id)
        status = chat_member.status
    except:
        status = "left"

    if status == "kicked":
        await message.answer("⛔️ Доступ запрещен. Вы были забанены.")
        return

    user_data = await get_user_data(user_id)

    if status in ["member", "administrator", "creator"]:
        if user_data:
            await message.answer(f"✅ Твой профиль: <b>{user_data[0]}</b> из ({user_data[1]}).")
        else:
            await message.answer("👋 Привет! Ты уже в группе, но тег не привязан. Напиши свой <b>Тег</b>:")
            await state.set_state(Registration.waiting_for_tag)
        return

    if user_data:
        await message.answer(f"👋 С возвращением, <b>{user_data[0]}</b>!\nТвоя ссылка готова:",
                             reply_markup=get_rules_kb())
        return

    await message.answer("👋 Привет! Для входа в группу отправь мне свой <b>Тег Brawl Stars</b>:")
    await state.set_state(Registration.waiting_for_tag)


@router.message(Command("set_key"))
async def admin_set_api_key(message: Message):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or message.from_user.id != int(admin_id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Использование: /set_key <ключ>")
        return
    update_api_key(parts[1].strip())
    await message.answer("✅ API ключ успешно обновлен в памяти бота!")


@router.message(Registration.waiting_for_tag)
async def process_tag_input(message: Message, state: FSMContext, bot: Bot):
    user_tag = message.text.strip().upper()
    user_id = message.from_user.id
    target_chat = os.getenv("TARGET_CHAT_ID")

    wait_msg = await message.answer("🔄 Проверка...")
    result = await check_player(user_tag)

    if result["success"] and result["status"] == "member":
        p_name = result["name"]
        c_name = result.get("club_name", "Phoenix Reborn")
        await add_user(user_id, user_tag, p_name, c_name)

        try:
            chat_member = await bot.get_chat_member(chat_id=target_chat, user_id=user_id)
            status = chat_member.status
        except:
            status = "left"

        if status in ["member", "administrator", "creator"]:
            await wait_msg.edit_text(
                f"✅ <b>Идентификация пройдена!</b>\nТег {user_tag} успешно привязан к твоему профилю.")
        else:
            rules_text = (
                f"✅ Привет, <b>{p_name}</b> из <b>{c_name}</b>!\n"
                "Ознакомься с правилами клуба:\n"
                " Нельзя\n"
                "1. 18+ контент — любого формата\n"
                "2. Спам и флуд — включая войс-спам и стикеры подряд\n"
                "3. Целенаправленные оскорбления — потроллить можно, целенаправленно унижать нельзя\n"
                "4. Реклама — чужих клубов, каналов, сервисов без разрешения\n"
                "5. Политика и религия — обсуждать можно, но без перехода к срачу, уважайте других\n"
                "6. Доксинг — личные данные людей без их согласия\n"
                "7. Разжигание конфликтов между клубами — мы семейство, не арена\n"
                "8. Попрошайничество — гемы, аккаунты, донат — не клянчить\n\n"
                " Можно:\n"
                "- Материться — в меру, в шутку.\n"
                "- Мемы и приколы — лишь бы не переходили в пункт 3\n\n"
                " Наказания:\n"
                "Варн / Мут / Бан\n"
                "За грубые нарушения (доксинг, 18+) — сразу бан"
            )
            await wait_msg.edit_text(rules_text, reply_markup=get_rules_kb())

        await state.clear()
    else:
        await wait_msg.edit_text("❌ Ошибка или ты не в клубе.")
        await state.clear()


@router.callback_query(F.data == "rules_accepted")
async def send_invite_link(callback: CallbackQuery):
    target_chat = os.getenv("TARGET_CHAT_ID")
    try:
        invite_link = await callback.bot.create_chat_invite_link(
            chat_id=target_chat,
            member_limit=1,
            name=f"Link for {callback.from_user.id}"
        )
        await save_link(invite_link.invite_link, callback.from_user.id)
        await callback.message.edit_text(f"Твоя ссылка:\n{invite_link.invite_link}")
    except:
        await callback.message.edit_text("⚠️ Ошибка прав.")
    await callback.answer()