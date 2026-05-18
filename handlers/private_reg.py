import os
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from utils.brawl_api import check_player, update_api_key, check_api_connection
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
        await message.answer("Доступ запрещен. Вы были забанены.")
        return
    user_data = await get_user_data(user_id)
    if status in ["member", "administrator", "creator"]:
        if user_data:
            await message.answer(f"Твой профиль: <b>{user_data[0]}</b> из <b>{user_data[1]}</b>.")
        else:
            await message.answer("Привет! Ты уже в группе, но тег не привязан. Напиши свой <b>Тег</b>:")
            await state.set_state(Registration.waiting_for_tag)
        return
    if user_data:
        await message.answer(f"С возвращением, <b>{user_data[0]}</b>!\nТвоя ссылка готова:", reply_markup=get_rules_kb())
        return
    await message.answer("Привет! Для входа в группу отправь мне свой <b>Тег Brawl Stars</b>:")
    await state.set_state(Registration.waiting_for_tag)

@router.message(Command("set_key"))
async def admin_set_api_key(message: Message):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or message.from_user.id != int(admin_id): return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /set_key <ключ>")
        return

    new_key = parts[1].strip()
    update_api_key(new_key)

    wait_msg = await message.answer("Ключ обновлен. Проверяю связь...")
    ok, text = await check_api_connection()
    await wait_msg.edit_text(f"Статус нового ключа:\n{text}")

@router.message(Command("ping"))
async def admin_ping(message: Message):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or message.from_user.id != int(admin_id): return
    wait_msg = await message.answer("Проверяю связь с серверами Supercell...")
    ok, text = await check_api_connection()
    await wait_msg.edit_text(text)

@router.message(Command("get_db"))
async def admin_get_db(message: Message):
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id or message.from_user.id != int(admin_id): return
    db_path = "/app/data/bot_data_v3.db"
    if os.path.exists(db_path): await message.answer_document(document=FSInputFile(db_path), caption="База данных")
    else: await message.answer("Файл не найден")

@router.message(Registration.waiting_for_tag)
async def process_tag_input(message: Message, state: FSMContext, bot: Bot):
    user_tag = message.text.strip().upper()
    user_id = message.from_user.id
    target_chat = os.getenv("TARGET_CHAT_ID")
    wait_msg = await message.answer("Проверка...")
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
            await wait_msg.edit_text(f"<b>Идентификация пройдена!</b>\nТег {user_tag} привязан.")
        else:
            rules = (
                f"Привет, <b>{p_name}</b> из <b>{c_name}</b>!\n\n"
                f"<b>ПРАВИЛА СЕМЕЙСТВА</b>\n\n"
                f"<u>НЕЛЬЗЯ:</u>\n"
                f"1. 18+ контент\n"
                f"2. Спам\n"
                f"3. Оскорбления\n"
                f"4. Реклама\n"
                f"5. Политика\n"
                f"6. Доксинг\n"
                f"7. Конфликты\n"
                f"8. Попрошайничество\n\n"
                f"<u>МОЖНО:</u>\n"
                f"— <i>Материться</i>\n"
                f"— <i>Подколы</i>"
            )
            await wait_msg.edit_text(rules, reply_markup=get_rules_kb())
        await state.clear()
    else:
        await wait_msg.edit_text("Ошибка или ты не в клубе. Проверь синтаксис и введи тег еще раз:")