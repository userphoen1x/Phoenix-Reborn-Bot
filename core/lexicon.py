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
    "reg_success_update": "✅ Тег успешно привязан!\nВаше звание обновлено: <b>{role}</b>.",

    # Казино
    "casino_welcome": "🎰 <b>КАЗИНО PHOENIX</b> 🎰\n\n💰 Твой баланс: <b>{balance}</b> ₣\n\nВыбери игру, чтобы испытать удачу:",
    "casino_bet_prompt": "{game_name}\n\nВыберите размер ставки:",
    "casino_min_bet": "❌ Минимальная ставка 10 ₣!",
    "casino_dice_guess": "🎲 Ставка: <b>{bet} ₣</b>\n\nНа какое число ставишь?",
    "casino_result": "{emoji} <b>РЕЗУЛЬТАТ: {dice_value}</b>\n\n{msg_result}\n💸 Выигрыш: <b>{win_amount} ₣</b>",
    "casino_no_money": "Недостаточно средств!",
    "casino_game_over": "Игра закончена!",
    "bj_state": "🃏 <b>БЛЭКДЖЕК</b>\n\n💸 Ставка: <b>{bet} ₣</b>\n\n🏦 Дилер: {d_card}, 🂠 (?)\n👤 Ты: {p_hand} <b>({pval})</b>\n\nТвой ход:",
    "bj_result": "🃏 <b>БЛЭКДЖЕК: ИТОГИ</b>\n\n🏦 Дилер: {d_hand} <b>({dval})</b>\n👤 Ты: {p_hand} <b>({pval})</b>\n\n{res_msg}\n💸 Выигрыш: <b>{win_amount} ₣</b>",
    "saper_bet_prompt": "💣 <b>САПЕР</b>\n\nВыберите сумму ставки (мин. 10 ₣):",
    "saper_diff_prompt": "💣 <b>САПЕР</b>\n\nСтавка: <b>{bet}</b> ₣\nВыберите сложность:",
    "saper_min_bet": "❌ Минимальная ставка в сапере — <b>10</b> ₣.",
    "saper_start": "💣 <b>САПЕР</b> 💣\n\n👤 Игрок: <b>{name}</b>\n🕹 Сложность: <b>{diff_name}</b>\n💸 Ставка: <b>{bet}</b> ₣\n\n<i>Открывай ячейки, но берегись мин!</i>",
    "saper_not_your_game": "❌ Это не ваша игра или она уже завершена!",
    "saper_chat_error": "❌ Ошибка чата!",
    "saper_cashout": "💰 <b>ДЕНЬГИ СНЯТЫ!</b>\n\n👤 Игрок: <b>{name}</b>\n🕹 Сложность: <b>{diff_name}</b>\n📥 Забрано: <b>{win_amount} ₣</b> (x{mult})",
    "saper_already_open": "Эта ячейка уже открыта!",
    "saper_boom": "💥 <b>БУМ! ВЫ ПРОИГРАЛИ!</b> 💥\n\n👤 Игрок: <b>{name}</b>\n💸 Потеряно: <b>{bet} ₣</b>\n<i>Мина оказалась прямо под ногой...</i>",
    "saper_win": "🏆 <b>ИДЕАЛЬНАЯ ПОБЕДА!</b> 🏆\n\n👤 Игрок: <b>{name}</b>\n🎉 Все безопасные ячейки найдены!\n🤑 Выигрыш: <b>{win_amount} ₣</b> (x{mult})",
    "saper_continue": "💣 <b>САПЕР</b> 💣\n\n👤 Игрок: <b>{name}</b>\n🕹 Сложность: <b>{diff_name}</b>\n💸 Ставка: <b>{bet}</b> ₣\n💰 Выигрыш: <b>{current_win} ₣</b> (x{mult})\n\n<i>Играем дальше или забираем?</i>",

    # Топы
    "top_choose_club": "📊 <b>Выберите клуб:</b>",
    "top_loading": "⏳ Собираю актуальные данные...",
    "top_api_error": "❌ Ошибка загрузки данных из API.",
    "top_push_title": "🏆 <b>Топ пушеров ({push_title})</b>\n\n",
    "top_empty": "📭 Пока нет данных для расчета (или никто не апнул кубки).",
    "top_calc_error": "❌ Ошибка вычислений: {error}",
    "top_category": "📂 <b>Категория:</b>",
    "top_msg_title": "💬 <b>Сообщения (Все клубы):</b>",
    "top_wins_title": "⚔️ <b>Победы (Все клубы):</b>",
    "top_eco_title": "🔥 <b>Топ богачей (₣)</b>\n\n",
    "top_cups_title": "🏆 <b>ТОП КУБКОВ</b>\n\n",
    "top_ranks_title": "🎖 <b>Ранкед</b>\n\n",
    "top_not_yours": "❌ Не твое меню",
    "top_msg_cat": "💬 <b>Сообщения:</b>",
    "top_cups_gain_cat": "📈 <b>Рост кубков:</b>",
    "top_wins_cat": "⚔️ <b>Победы:</b>",
    "top_wins_sd_cat": "🌵 <b>Столкновение (ШД):</b>",
    "top_eco_empty": "📭 Пока никого нет.",
    "top_api_err_details": "❌ Ошибка загрузки.\nДетали: {error}",
    "top_msg_res": "💬 <b>Топ сообщений чата</b>\n\n",
    "top_gain_res": "📈 <b>Рост кубков</b>\n\n",
    "top_wins_res": "<b>{title}</b>\n\n",

    # Основатель
    "fnd_unlink_success": "✅ Тег успешно отвязан от профиля {target}, пользователь переведен в Гости.",
    "fnd_err_no_key": "❌ Укажите новый ключ. Пример:\n<code>/set_key eyJhbGciOi...</code>",
    "fnd_key_check": "⏳ Проверяю новый ключ и IP-адрес...",
    "fnd_key_ok": "✅ <b>API ключ успешно обновлен!</b>\nСвязь с серверами Brawl Stars установлена (200 OK).",
    "fnd_key_fail": "⚠️ <b>Ключ сохранен, но API недоступно!</b>\nВозможно, вы не добавили новый IP в белый список Supercell.\nОшибка: <code>{error}</code>",
    "fnd_ping_check": "⏳ Проверяю связь с серверами Supercell...",
    "fnd_ping_res": "Статус API:\n{text}",
    "fnd_db_caption": "🗄 База данных",
    "fnd_db_fail": "❌ Файл не найден",
    "fnd_force_roles_start": "Запускаю ручную проверку ролей. Ждите...",
    "fnd_force_roles_ok": "✅ Проверка завершена.",
    "fnd_no_rights": "Нет прав",
    "fnd_role_err_db": "❌ Ошибка: Пользователь больше не найден в базе.",
    "fnd_role_ok": "✅ Внутренние права бота (<b>{role}</b>) успешно выданы пользователю (ID: <code>{user_id}</code>).",
    "fnd_role_db_err": "❌ Ошибка обновления базы данных: {error}",
    "fnd_role_reject": "Запрос на выдачу прав (ID: {user_id}) отклонен.",
    "fnd_req_empty": "✅ В базе нет пользователей, ожидающих подтверждения звания.",
    "fnd_req_check": "⏳ Проверяю актуальные звания в клубе...",
    "fnd_req_resend": "🔄 <b>ПОВТОРНЫЙ ЗАПРОС</b>\n\n👤 {display_tg} (ID: <code>{u_id}</code>)\n🎮 Игрок: <b>{player_name}</b> (<code>{tag}</code>)\n🏰 Клуб: <b>{club_name}</b>\n\nОжидает подтверждения звания <b>{api_role}</b>. Выдаем права модератора?",
    "fnd_req_sent": "✅ Актуальные запросы ({count} шт.) отправлены Главару в ЛС.",
    "fnd_scan_start": "⏳ Собираю данные...",
    "fnd_scan_ok": "✅ Готово. Сбор данных завершен.",
    "fnd_reg_empty": "📭 Список зарегистрированных пользователей пуст.",
    "fnd_reg_list_title": "📋 <b>Список зарегистрированных игроков:</b>\n"
}