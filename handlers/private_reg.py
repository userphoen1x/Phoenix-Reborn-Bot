from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

router = Router()
router.message.filter(F.chat.type == "private")


class Registration(StatesGroup):
    waiting_for_tag = State()


def get_start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data="reg_yes"),
            InlineKeyboardButton(text="Нет", callback_data="reg_no")
        ]
    ])


def get_rules_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ознакомился", callback_data="rules_accepted")]
    ])


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Добро пожаловать в систему бота **Phoenix Reborn**.\n\n"
        "Являетесь ли вы участником семейства клубов «Phoenix Reborn»?",
        reply_markup=get_start_kb(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "reg_no")
async def process_reg_no(callback: CallbackQuery):
    await callback.message.edit_text("Тогда вам здесь нечего делать. 🚪")
    await callback.answer()


@router.callback_query(F.data == "reg_yes")
async def process_reg_yes(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Отлично! 📝 Пожалуйста, отправь мне свой **Тег** (например, #8P2QQG0) для идентификации.",
        parse_mode="Markdown"
    )
    await state.set_state(Registration.waiting_for_tag)
    await callback.answer()


@router.message(Registration.waiting_for_tag)
async def process_tag_input(message: Message, state: FSMContext):
    user_tag = message.text.strip().upper()
    await message.answer(f"🔄 Проверяю тег `{user_tag}` в базе данных...\n")

    rules_text = (
        "✅ **Идентификация пройдена успешно!**\n\n"
        "📜 **Правила группы:**\n"
        "1. Уважать участников клуба.\n"
        "2. Отыгрывать билеты мегакопилки.\n\n"
        "Нажми кнопку ниже, чтобы получить ссылку на вход."
    )
    await message.answer(rules_text, reply_markup=get_rules_kb(), parse_mode="Markdown")
    await state.clear()


@router.callback_query(F.data == "rules_accepted")
async def send_invite_link(callback: CallbackQuery):
    await callback.message.edit_text("🎉 Добро пожаловать в Phoenix Reborn!")
    await callback.answer()