from aiogram import Dispatcher
from . import registration, group_events, group_commands, founder, profile, economy, casino, ai_chat, tops

def setup_routers(dp: Dispatcher):
    dp.include_router(founder.router)
    dp.include_router(profile.router)
    dp.include_router(economy.router)
    dp.include_router(casino.router)
    dp.include_router(registration.router)
    dp.include_router(group_events.router)
    dp.include_router(group_commands.router)
    dp.include_router(tops.router)
    dp.include_router(ai_chat.router)