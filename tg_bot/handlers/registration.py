import os
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from services.registration_service import RegistrationService
from database.repositories.economy_repo import EconomyRepository
from core.exceptions import BotBaseException
from utils.admin_logger import send_log

router = Router()
router.message.filter(F.chat.type == "private")

class RegFSM(StatesGroup):
    waiting_for_tag = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, eco_repo: EconomyRepository):
    await state.clear()
    eco = await eco_repo.get_eco_data(message.from_user.id)
    if eco and eco.get("bs_tag"):
        await message.answer("✅ Вы уже зарегистрированы и привязали свой игровой тег!")
        return
    await message.answer("👋 Привет! Отправь мне свой игровой тег Brawl Stars (например: <code>#2YYUG28QQ</code>), чтобы получить доступ к функциям.", parse_mode="HTML")
    await state.set_state(RegFSM.waiting_for_tag)

@router.message(RegFSM.waiting_for_tag)
async def process_tag_input(message: Message, state: FSMContext, bot: Bot, reg_service: RegistrationService):
    user_tag = message.text.strip().upper()
    wait_msg = await message.answer("⏳ Проверяю данные в игре...")
    try:
        result = await reg_service.register_player(message.from_user.id, user_tag)
        status_text = f"🏰 Клуб: {result['club']}\n🎖 Статус: Участник семейства" if result['is_in_club'] else f"🏰 Клуб: {result['club']}\n🗣️ Статус: Гость (Вне семейства)"
        await wait_msg.edit_text(f"✅ <b>Регистрация успешна!</b>\n\n👤 Имя: <b>{result['name']}</b>\n🏷 Тег: <code>{result['tag']}</code>\n{status_text}", parse_mode="HTML")
        await state.clear()
        username_str = f"@{message.from_user.username}" if message.from_user.username else "Без юзернейма"
        log_text = f"👤 <b>НОВАЯ РЕГИСТРАЦИЯ</b>\n\n🔗 Юзер: {username_str} (<code>{message.from_user.id}</code>)\n🏷 Тег: <code>{result['tag']}</code>\n🎮 Имя в игре: <b>{result['name']}</b>\n🏰 Клуб: {result['club']}"
        await send_log(bot, "TOPIC_REG", log_text)
    except BotBaseException as e:
        await wait_msg.edit_text(str(e))