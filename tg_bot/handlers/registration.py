import os
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import aiosqlite
from services.registration_service import RegistrationService
from database.repositories.economy_repo import EconomyRepository
from core.exceptions import BotBaseException
from utils.admin_logger import send_log
from core.config import settings

router = Router()
router.message.filter(F.chat.type == "private")

class RegFSM(StatesGroup):
    waiting_for_tag = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot, eco_repo: EconomyRepository):
    await state.clear()
    eco = await eco_repo.get_eco_data(message.from_user.id)
    
    if eco and eco.get("bs_tag"):
        try:
            member = await bot.get_chat_member(settings.TARGET_CHAT_ID, message.from_user.id)
            
            if member.status == "kicked":
                await message.answer("❌ Вы заблокированы в группе клуба. Доступ запрещен.")
                return
            elif member.status == "left":
                invite = await bot.create_chat_invite_link(
                    chat_id=settings.TARGET_CHAT_ID,
                    name=f"Invite_{message.from_user.id}",
                    creates_join_request=True
                )
                
                async with aiosqlite.connect(settings.DB_PATH) as db:
                    await db.execute(
                        "INSERT OR REPLACE INTO links (link, user_id) VALUES (?, ?)",
                        (invite.invite_link, message.from_user.id)
                    )
                    await db.commit()
                    
                await message.answer(
                    f"✅ Вы уже зарегистрированы!\n\n"
                    f"Мы заметили, что вас нет в группе.\n"
                    f"🔗 <b>Ваша новая ссылка для входа:</b>\n{invite.invite_link}\n\n"
                    f"⚠️ <i>Ссылка одноразовая и привязана к вашему аккаунту. При попытке передать её другому лицу сработает блокировка.</i>",
                    parse_mode="HTML"
                )
                return
            else:
                await message.answer("✅ Вы уже зарегистрированы и находитесь в группе клуба!")
                return
        except Exception:
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
        
        user_id = message.from_user.id
        invite = await bot.create_chat_invite_link(
            chat_id=settings.TARGET_CHAT_ID,
            name=f"Invite_{user_id}",
            creates_join_request=True
        )

        async with aiosqlite.connect(settings.DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO links (link, user_id) VALUES (?, ?)",
                (invite.invite_link, user_id)
            )
            await db.commit()

        success_text = (
            f"✅ <b>Регистрация успешна!</b>\n\n"
            f"👤 Имя: <b>{result['name']}</b>\n"
            f"🏷 Тег: <code>{result['tag']}</code>\n{status_text}\n\n"
            f"🔗 <b>Ваша ссылка для входа в клуб:</b>\n{invite.invite_link}\n\n"
            f"⚠️ <i>Ссылка одноразовая и привязана к вашему аккаунту. При попытке передать её другому лицу сработает блокировка.</i>"
        )
        await wait_msg.edit_text(success_text, parse_mode="HTML")
        await state.clear()
        
        username_str = f"@{message.from_user.username}" if message.from_user.username else "Без юзернейма"
        log_text = f"👤 <b>НОВАЯ РЕГИСТРАЦИЯ</b>\n\n🔗 Юзер: {username_str} (<code>{user_id}</code>)\n🏷 Тег: <code>{result['tag']}</code>\n🎮 Имя в игре: <b>{result['name']}</b>\n🏰 Клуб: {result['club']}"
        await send_log(bot, "TOPIC_REG", log_text)
    except BotBaseException as e:
        await wait_msg.edit_text(str(e))
