import os
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from utils.brawl_api import check_player, update_api_key
from utils.database import add_user, is_user_approved

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

    if not target_chat:
        await message.answer("⚠️ Ошибка: ID группы не настроен.")
        return

    # 1. Получаем статус пользователя в группе
    try:
        chat_member = await bot.get_chat_member(chat_id=target_chat, user_id=user_id)
        status = chat_member.status
    except Exception:
        status = "left"  # Если бот его вообще не видит, считаем, что он не в группе

    # 2. Проверка на Черный Список (ЧС)
    if status == "kicked":
        await message.answer("⛔️ Доступ запрещен. Вы находитесь в черном списке группы.")
        return

    # 3. Проверка старых участников (кто уже в группе)
    if status in ["member", "administrator", "creator"]:
        if await is_user_approved(user_id):
            await message.answer("✅ Вы уже находитесь в группе и ваш тег привязан. Всё отлично!")
        else:
            await message.answer(
                "👋 Привет! Вижу, ты уже находишься в нашей группе, но твой игровой тег не привязан к базе.\n\n"
                "📝 Пожалуйста, отправь мне свой <b>Тег Brawl Stars</b> (например, #8P2QQG0), чтобы я внес тебя в реестр."
            )
            await state.set_state(Registration.waiting_for_tag)
        return

    # 4. Проверка тех, кто вышел сам, но уже есть в базе
    if status in ["left", "restricted"]:
        if await is_user_approved(user_id):
            await message.answer(
                "👋 С возвращением! Вы уже есть в нашей базе.\n"
                "Нажмите кнопку ниже, чтобы получить новую ссылку на вход.",
                reply_markup=get_rules_kb()
            )
            return
        else:
            # Полностью новый пользователь
            await message.answer(
                "👋 Привет! Добро пожаловать в систему бота <b>Phoenix Reborn</b>.\n\n"
                "📝 Для получения доступа в закрытую группу, пожалуйста, отправь мне свой <b>Тег Brawl Stars</b> (например, #8P2QQG0)."
            )
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

    wait_msg = await message.answer(f"🔄 Ищу игрока <code>{user_tag}</code> на серверах Supercell...")
    result = await check_player(user_tag)

    if not result["success"]:
        if result.get("error") == "not_found":
            await wait_msg.edit_text("❌ Игрок не найден. Проверь правильность тега и напиши его снова:")
            return
        else:
            await wait_msg.edit_text("⚠️ Ошибка связи с серверами Brawl Stars. Попробуй позже.")
            await state.clear()
            return

    if result["status"] == "member":
        # Заносим пользователя в белую базу данных!
        await add_user(user_id, user_tag)

        # Проверяем, в группе ли он уже (старичок)
        try:
            chat_member = await bot.get_chat_member(chat_id=target_chat, user_id=user_id)
            status = chat_member.status
        except:
            status = "left"

        if status in ["member", "administrator", "creator"]:
            await wait_msg.edit_text(
                f"✅ <b>Идентификация пройдена!</b>\nТег {user_tag} успешно привязан к твоему профилю. Спасибо!")
        else:
            rules_text = (
                f"✅ <b>Идентификация пройдена!</b>\n"
                f"Привет, <b>{result['name']}</b>! Рады видеть тебя.\n\n"
                "📜 <b>Правила группы:</b>\n"
                "1. Уважать участников клуба.\n"
                "2. Отыгрывать билеты мегакопилки.\n\n"
                "Нажми кнопку ниже, чтобы получить ссылку на вход."
            )
            await wait_msg.edit_text(rules_text, reply_markup=get_rules_kb())

        await state.clear()
    else:
        await wait_msg.edit_text(f"⛔️ Отказ в доступе.\nИгрок <b>{result['name']}</b> не состоит в нашем клубе.")
        await state.clear()


@router.callback_query(F.data == "rules_accepted")
async def send_invite_link(callback: CallbackQuery):
    target_chat = os.getenv("TARGET_CHAT_ID")
    if not target_chat:
        await callback.message.edit_text("⚠️ Ошибка системы: ID группы не настроен.")
        await callback.answer()
        return

    try:
        invite_link = await callback.bot.create_chat_invite_link(
            chat_id=target_chat,
            member_limit=1,
            name=f"Вход: {callback.from_user.first_name}"
        )
        await callback.message.edit_text(
            "🎉 <b>Добро пожаловать в Phoenix Reborn!</b>\n\n"
            "Твоя персональная ссылка для входа готова:\n"
            f"{invite_link.invite_link}\n\n"
            "<i>⚠️ Внимание: Ссылка сработает только 1 раз и привязана к твоему аккаунту. Если по ней попытается зайти кто-то другой — бот его заблокирует.</i>"
        )
    except Exception:
        await callback.message.edit_text("⚠️ Не удалось создать ссылку. Проверьте права бота!")
    await callback.answer()