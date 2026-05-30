import os
from aiogram import Router, F
from aiogram.types import Message
from database.repositories.economy_repo import EconomyRepository
from database.repositories.user_repo import UserRepository

# Создаем отдельный роутер для тестов
router = Router()

# ЖЕСТКИЙ ФИЛЬТР: Этот роутер перехватывает сообщения ТОЛЬКО из тестового чата
router.message.filter(lambda msg: str(msg.chat.id) == os.getenv("TEST_CHAT_ID"))


@router.message(F.text.lower() == "чит рег")
async def cmd_test_register(message: Message, user_repo: UserRepository):
    """Мгновенная фейковая регистрация для тестов без Brawl API"""
    fake_tag = f"#TEST{message.from_user.id}"
    player_name = message.from_user.first_name

    # Записываем в базу как полноценного игрока
    await user_repo.add_user(
        user_id=message.from_user.id,
        bs_tag=fake_tag,
        player_name=player_name,
        club_name="Test Sandbox"
    )
    # Сразу выдаем высшие права для тестов модерации
    await user_repo.set_user_role(message.from_user.id, "Президент", "Одобрен")

    await message.answer(
        f"✅ <b>[SANDBOX]</b> Профиль создан!\nТег: <code>{fake_tag}</code>\nРоль: Президент.\nТеперь тебе доступны все игры и экономика.",
        parse_mode="HTML")


@router.message(F.text.lower().startswith("чит деньги"))
async def cmd_test_money(message: Message, eco_repo: EconomyRepository):
    """Выдача любого количества Феников"""
    parts = message.text.split()
    amount = 1000000  # Миллион по умолчанию

    if len(parts) > 2 and parts[2].isdigit():
        amount = int(parts[2])

    try:
        await eco_repo.update_balance(message.from_user.id, amount)
        await message.answer(f"💰 <b>[SANDBOX]</b> Начислено <b>{amount} ₣</b>.", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ <b>[SANDBOX]</b> Ошибка: сначала пропиши 'чит рег'.\nЛог: {e}", parse_mode="HTML")


@router.message(F.text.lower() == "чит кд")
async def cmd_test_cooldown(message: Message, eco_repo: EconomyRepository):
    """Сброс кулдауна на работу"""
    try:
        await eco_repo.set_eco_data(message.from_user.id, "last_work", None)
        await message.answer("⏳ <b>[SANDBOX]</b> Кулдаун на /ворк сброшен.")
    except Exception as e:
        await message.answer(f"❌ <b>[SANDBOX]</b> Ошибка: {e}", parse_mode="HTML")