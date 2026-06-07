LEXICON = {
    "error_generic": "❌ {error}",

    # Экономика
    "eco_balance": "💰 Баланс {target}: <b>{balance} ₣</b>",
    "eco_err_format_transfer": "❌ Формат: <code>/перевод [сумма] [@user или реплай]</code>",
    "eco_err_self_transfer": "❌ Нельзя перевести самому себе.",
    "eco_success_transfer": "✅ Успешный перевод!\n💸 Вы отправили <b>{amount} ₣</b> пользователю {target}.",
    "eco_err_format_add": "❌ Формат: <code>/начислить [сумма] [@user или реплай]</code>",
    "eco_success_add": "🏦 Администратор начислил <b>{amount} ₣</b> пользователю {target}.",
    "eco_err_format_remove": "❌ Формат: <code>/штраф [сумма] [@user или реплай]</code>",
    "eco_success_remove": "⚖️ Администратор выписал штраф <b>{amount} ₣</b> пользователю {target}.",

    # Модерация
    "mod_err_no_target": "❌ Укажите @username или ответьте на сообщение пользователя.",
    "mod_err_not_in_db": "❌ Ответьте на сообщение пользователя или укажите его @username (игрок должен быть в базе).",
    "mod_success_demote": "⬇️ <b>{target}</b> понижен до Гостя и лишен системных полномочий в боте.",
    "mod_success_restore": "✅ Полномочия <b>{target}</b> восстановлены.",
    "mod_err_fail": "❌ Ошибка выполнения: боту не хватает прав или цель имеет иммунитет.",
    "mod_punish_public": "{emoji} Пользователь {target} был {action} администратором {admin}.\n📝 Причина: {reason}",
    "mod_log_punish": "🚨 <b>ЛОГ НАКАЗАНИЯ</b>\n\n👮‍♂️ Модератор: {admin}\n👤 Нарушитель: {target}\n🛠 Действие: <b>{action}</b>\n📝 Причина: {reason}",

    # События
    "event_kick_unreg": "🚫 <b>ЗАЙЧИК КИКНУТ</b>\n\nПользователь <a href='tg://user?id={user_id}'>{name}</a> попытался войти без регистрации.\n\nПройдите регистрацию в личных сообщениях со мной!",
    "event_welcome": "👋 Добро пожаловать, <a href='tg://user?id={user_id}'>{name}</a>!",

    # Профиль
    "profile_not_found_db": "❌ Пользователь {target} не найден в базе данных.",
    "profile_not_linked": "❌ Профиль не найден. Игрок не привязал тег.",
    "profile_api_error": "❌ Ошибка получения данных из API Brawl Stars.",
    "profile_loading": "⏳ Загружаю данные...",
    "profile_text": (
        "👤 <b>ПРОФИЛЬ УЧАСТНИКА</b>\n\n"
        "┌ 📱 Ник: {name_link}\n"
        "├ 🪪 {role_label}: {role_str}\n"
        "├ 🏰 Клуб: {club_display}\n"
        "├ 🏆 Общие: {trophies_str}\n"
        "├ 🎖 Ранкед: {rank_name} ({rank_elo})\n"
        "├ ⚔️ 3 на 3: {wins3v3}\n"
        "├ 🌵 ШД: {sd_wins}\n"
        "└ 💰 Баланс: {balance} ₣"
    ),

    # Регистрация
    "reg_wait": "⏳ Проверяю данные...",
    "reg_banned": "❌ Вам запрещен доступ в группу (бан).",
    "reg_not_in_club_deny": "⛔️ Доступ запрещен: вы не являетесь участником клубов Phoenix Family.",
    "reg_not_in_club_guest": "Вы не в клубах семейства. Вам автоматически выдано звание 'Гость'.",
    "reg_in_club_invite": "✅ Вы состоите в клубе!\nВот ваша индивидуальная ссылка для входа:\n{link}",
    "reg_invite_error": "❌ Ошибка создания ссылки.\nДетали: {error}",
    "reg_perfect": "✅ Всё настроено идеально! Вы есть в клубе и в чате.",
    "reg_prompt_tag_chat": "Привяжите ваш игровой тег (напишите его следующим сообщением).",
    "reg_prompt_tag_pm": "Для получения доступа в чат привяжите ваш игровой тег.",
    "reg_search_tag": "⏳ Ищу ваш тег в базе Supercell...",
    "reg_tag_not_found": "❌ Тег не найден. Проверьте правильность и отправьте снова.",
    "reg_success_guest": "✅ Тег привязан. Так как вы не состоите в клубах, вам выдано звание 'Гость'.",
    "reg_success_invite": "✅ Тег успешно привязан!\nВ игре у вас статус: <b>{role}</b>.\n\nВот ваша ссылка для входа в чат:\n{link}",
    "reg_success_update": "✅ Тег успешно привязан!\nВаше звание обновлено: <b>{role}</b>."
}