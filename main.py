async def top_cup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    now = datetime.now()

    if chat_id in last_top_time:
        diff = (now - last_top_time[chat_id]).total_seconds()
        if diff < 180:  # Снизил кулдаун до 3 минут
            remaining = int(180 - diff)
            return await update.message.reply_text(f"⏳ Команда на перезарядке! Попробуй через {remaining} сек.")

    last_top_time[chat_id] = now
    status_msg = await update.message.reply_text("⏳ <i>Собираю данные... (это займет пару секунд)</i>", parse_mode="HTML")

    cursor.execute("SELECT user_id, last_nick, bs_tag, start_cups FROM players")
    players = cursor.fetchall()

    if not players:
        return await status_msg.edit_text("📭 В базе пока нет привязанных игроков.")

    # Строгий лимит: не более 5 запросов к API одновременно, чтобы избежать бана
    sem = asyncio.Semaphore(5)

    async def fetch_player(player_data):
        async with sem:
            uid, nick, tag, start_cups = player_data
            await asyncio.sleep(0.05)  # Микро-пауза для стабильности
            data = await get_bs_data(f"players/{tag.replace('#', '%23')}")
            if data:
                current = data.get('trophies', start_cups)
                gain = current - start_cups
                cursor.execute("UPDATE players SET current_cups=?, last_nick=? WHERE user_id=?",
                               (current, data.get('name', nick), uid))
                return (data.get('name', nick), gain)
            return (nick, 0)

    tasks = [fetch_player(p) for p in players]
    results = await asyncio.gather(*tasks)
    conn.commit()

    # Жесткий фильтр: в топ попадают ТОЛЬКО те, у кого результат больше нуля
    valid_results = [(n, g) for n, g in results if g > 0]
    valid_results.sort(key=lambda x: x[1], reverse=True)

    text = "🏆 <b>ТОП-10 ПУШЕРОВ ДНЯ</b>\n\n"
    for i, (nick, gain) in enumerate(valid_results[:10], 1):
        m = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"<b>{i}.</b>")
        text += f"{m} {nick} — <code>+{gain}</code> 🏆\n"

    if not valid_results:
        text += "📭 Пока никто не апнул кубки."

    await status_msg.edit_text(text, parse_mode="HTML")


async def top_cup_from_query(query, context: ContextTypes.DEFAULT_TYPE):
    chat_id = query.message.chat.id
    now = datetime.now()

    if chat_id in last_top_time:
        diff = (now - last_top_time[chat_id]).total_seconds()
        if diff < 180:
            remaining = int(180 - diff)
            await context.bot.send_message(chat_id, f"⏳ Команда на перезарядке! Попробуй через {remaining} сек.")
            return

    last_top_time[chat_id] = now
    status_msg = await context.bot.send_message(chat_id, "⏳ <i>Собираю данные... (это займет пару секунд)</i>", parse_mode="HTML")

    cursor.execute("SELECT user_id, last_nick, bs_tag, start_cups FROM players")
    players = cursor.fetchall()

    if not players:
        await status_msg.edit_text("📭 В базе пока нет привязанных игроков.")
        return

    sem = asyncio.Semaphore(5)

    async def fetch_player(player_data):
        async with sem:
            uid, nick, tag, start_cups = player_data
            await asyncio.sleep(0.05)
            data = await get_bs_data(f"players/{tag.replace('#', '%23')}")
            if data:
                current = data.get('trophies', start_cups)
                gain = current - start_cups
                cursor.execute("UPDATE players SET current_cups=?, last_nick=? WHERE user_id=?",
                               (current, data.get('name', nick), uid))
                return (data.get('name', nick), gain)
            return (nick, 0)

    tasks = [fetch_player(p) for p in players]
    results = await asyncio.gather(*tasks)
    conn.commit()

    valid_results = [(n, g) for n, g in results if g > 0]
    valid_results.sort(key=lambda x: x[1], reverse=True)

    text = "🏆 <b>ТОП-10 ПУШЕРОВ ДНЯ</b>\n\n"
    for i, (nick, gain) in enumerate(valid_results[:10], 1):
        m = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"<b>{i}.</b>")
        text += f"{m} {nick} — <code>+{gain}</code> 🏆\n"

    if not valid_results:
        text += "📭 Пока никто не апнул кубки."

    await status_msg.edit_text(text, parse_mode="HTML")