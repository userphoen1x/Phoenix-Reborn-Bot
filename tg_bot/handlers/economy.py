import re
from aiogram import Router, F
from aiogram.types import Message
from dishka import inject
from dishka.integrations.aiogram import FromDishka

from services.economy_service import EconomyService
from database.repositories.user_repo import UserRepository
from tg_bot.filters.role_filters import IsModerator
from utils.resolvers import resolve_target
from core.garbage_collector import schedule_delete
from core.lexicon import LEXICON
from core.constants import DELAYS

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

def is_cmd(text: str, cmds: list) -> bool:
    if not text: return False
    t = text.lower().strip()
    for c in cmds:
        pattern = r'^' + re.escape(c) + r'(?:\s|$|[.,!?\n])'
        if re.match(pattern, t): return True
    return False

@router.message(F.text.func(lambda text: is_cmd(text, ["баланс", "б", "bal"])))
@inject
async def cmd_balance(message: Message, eco_service: FromDishka[EconomyService], user_repo: FromDishka[UserRepository]):
    target_id, target_name = await resolve_target(message, user_repo)
    if not target_id:
        target_id = message.from_user.id
        target_name = "Ваш"
    else:
        target_name = f"Пользователя {target_name}"

    try:
        bal = await eco_service.get_balance(target_id)
        sent = await message.answer(LEXICON["eco_balance"].format(target=target_name, balance=bal), parse_mode="HTML")
        schedule_delete(sent, DELAYS["default"])
    except Exception as e:
        sent = await message.answer(LEXICON["error_generic"].format(error=e))
        schedule_delete(sent, DELAYS["default"])

@router.message(F.text.func(lambda text: is_cmd(text, ["перевод", "pay", "give"])))
@inject
async def cmd_transfer(message: Message, eco_service: FromDishka[EconomyService], user_repo: FromDishka[UserRepository]):
    parts = message.text.split()
    amount = next((int(p) for p in parts[1:] if p.isdigit()), None)
    target_id, target_name = await resolve_target(message, user_repo)

    if not amount or not target_id:
        sent = await message.answer(LEXICON["eco_err_format_transfer"], parse_mode="HTML")
        schedule_delete(sent, DELAYS["default"])
        return

    if target_id == message.from_user.id:
        return await message.answer(LEXICON["eco_err_self_transfer"])

    try:
        await eco_service.transfer(message.from_user.id, target_id, amount)
        sent = await message.answer(LEXICON["eco_success_transfer"].format(amount=amount, target=target_name), parse_mode="HTML")
        schedule_delete(sent, DELAYS["short"])
    except Exception as e:
        sent = await message.answer(LEXICON["error_generic"].format(error=e))
        schedule_delete(sent, DELAYS["default"])

@router.message(F.text.func(lambda text: is_cmd(text, ["начислить", "addmoney"])), IsModerator())
@inject
async def cmd_add_money(message: Message, eco_service: FromDishka[EconomyService], user_repo: FromDishka[UserRepository]):
    parts = message.text.split()
    amount = next((int(p) for p in parts[1:] if p.isdigit()), None)
    target_id, target_name = await resolve_target(message, user_repo)

    if not amount or not target_id:
        sent = await message.answer(LEXICON["eco_err_format_add"], parse_mode="HTML")
        schedule_delete(sent, DELAYS["default"])
        return

    try:
        await eco_service.add_money(target_id, amount)
        sent = await message.answer(LEXICON["eco_success_add"].format(amount=amount, target=target_name), parse_mode="HTML")
        schedule_delete(sent, DELAYS["short"])
    except Exception as e:
        sent = await message.answer(LEXICON["error_generic"].format(error=e))
        schedule_delete(sent, DELAYS["default"])

@router.message(F.text.func(lambda text: is_cmd(text, ["штраф", "removemoney"])), IsModerator())
@inject
async def cmd_remove_money(message: Message, eco_service: FromDishka[EconomyService], user_repo: FromDishka[UserRepository]):
    parts = message.text.split()
    amount = next((int(p) for p in parts[1:] if p.isdigit()), None)
    target_id, target_name = await resolve_target(message, user_repo)

    if not amount or not target_id:
        sent = await message.answer(LEXICON["eco_err_format_remove"], parse_mode="HTML")
        schedule_delete(sent, DELAYS["default"])
        return

    try:
        await eco_service.add_money(target_id, -amount)
        sent = await message.answer(LEXICON["eco_success_remove"].format(amount=amount, target=target_name), parse_mode="HTML")
        schedule_delete(sent, DELAYS["short"])
    except Exception as e:
        sent = await message.answer(LEXICON["error_generic"].format(error=e))
        schedule_delete(sent, DELAYS["default"])