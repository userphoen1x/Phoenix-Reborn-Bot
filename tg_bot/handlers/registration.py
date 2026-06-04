@router.message(RegState.tag)
async def process_tag(message: Message, state: FSMContext, bot: Bot, user_repo: UserRepository,
                      brawl_client: BrawlAPIClient):
    tag = message.text.strip().upper()
    if not tag.startswith("#"):
        tag = "#" + tag

    user_id = message.from_user.id
    wait_msg = await message.answer("⏳ Ищу ваш тег в базе Supercell...")

    try:
        in_chat, is_banned = await get_user_chat_status(bot, user_id)

        if is_banned:
            await state.clear()
            return await wait_msg.edit_text("❌ Вам запрещен доступ в группу.")

        player_stats = await brawl_client.get_player_stats(tag)
        if not player_stats:
            return await wait_msg.edit_text("❌ Тег не найден. Проверьте правильность и отправьте снова.")

        # ОШИБКА БЫЛА ЗДЕСЬ: Убрали слово "ALL" из скобок!
        clubs_members, _ = await brawl_client.get_all_club_members()
        member_data = next((m for m in clubs_members if m.get("tag") == tag), None) if clubs_members else None
        in_club = member_data is not None

        if not in_club and not in_chat:
            await state.clear()
            return await wait_msg.edit_text("⛔️ Доступ запрещен: этот тег не состоит в клубах Phoenix Family.")

        player_name = player_stats.get("name", "Игрок")
        await user_repo.register_user(user_id, tag, player_name,
                                      message.from_user.username or message.from_user.full_name)

        if not in_club and in_chat:
            await user_repo.set_user_role(user_id, "Гость", "Одобрен")
            await wait_msg.edit_text("✅ Тег привязан. Так как вы не состоите в клубах, вам выдано звание 'Гость'.")
        elif in_club and not in_chat:
            role_eng = member_data.get("role", "member")
            role_ru = {"president": "Президент", "vicePresident": "Вице-президент", "senior": "Ветеран",
                       "member": "Участник"}.get(role_eng, "Участник")
            r_status = "Ожидает" if role_ru in ["Президент", "Вице-президент"] else "Одобрен"
            await user_repo.set_user_role(user_id, role_ru, r_status)

            try:
                link = await bot.create_chat_invite_link(int(settings.TARGET_CHAT_ID), member_limit=1)
                await wait_msg.edit_text(
                    f"✅ Тег успешно привязан!\nВ игре у вас статус: <b>{role_ru}</b>.\n\nВот ваша ссылка для входа в чат:\n{link.invite_link}",
                    parse_mode="HTML")
            except Exception as e:
                await wait_msg.edit_text(
                    f"✅ Тег привязан!\n❌ Ошибка создания ссылки (нет прав). Попросите Лидера добавить вас вручную.\nДетали: {e}")
        elif in_club and in_chat:
            role_eng = member_data.get("role", "member")
            role_ru = {"president": "Президент", "vicePresident": "Вице-президент", "senior": "Ветеран",
                       "member": "Участник"}.get(role_eng, "Участник")
            r_status = "Ожидает" if role_ru in ["Президент", "Вице-президент"] else "Одобрен"
            await user_repo.set_user_role(user_id, role_ru, r_status)
            await wait_msg.edit_text(f"✅ Тег успешно привязан!\nВаше звание обновлено: <b>{role_ru}</b>.",
                                     parse_mode="HTML")

        await state.clear()

    except Exception as e:
        # Теперь, если возникнет ЛЮБАЯ ошибка, бот напишет об этом, а не зависнет!
        await wait_msg.edit_text(f"❌ Произошла системная ошибка:\n<code>{e}</code>\nСкиньте этот текст разработчику.",
                                 parse_mode="HTML")
        await state.clear()