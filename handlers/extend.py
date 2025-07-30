from db import get_key_by_id, update_key_expiry, activate_key, get_or_create_user, update_balance,reset_notified_level


async def extend_key_handler(update, context):
    query = update.callback_query
    data = query.data 
    print("🔍 query.data:", data)

    parts = data.split("_")
    key_id = int(parts[1])
    add_days = int(parts[2]) if len(parts) > 2 else 30  # дефолт если что

    prices = {30: 100, 60: 180}
    price = prices.get(add_days, 100)

    key = get_key_by_id(key_id)
    if not key:
        await query.answer("❌ Ключ не найден!", show_alert=True)
        return

    email, link, expiry, client_id, active, inbound_id = key

    if inbound_id == 2:
        await query.answer("Ключ устарел. Перенесите его на новый сервер.", show_alert=True)
        return

    tg_id = str(query.from_user.id)
    user_id, balance = get_or_create_user(tg_id)

    if balance < price:
        await query.answer(f"❌ Недостаточно средств! Баланс: {balance} RUB.", show_alert=True)
        return

    from services.extend_service import extend_key, SESSION_KEY
    result = extend_key(
        email=email,
        client_id=client_id,
        active=active,
        current_expiry=expiry,
        add_days=add_days,
        inbound_id=1,
    )

    if result:
        update_key_expiry(key_id, result)
        activate_key(key_id)
        update_balance(user_id, balance - price)
        reset_notified_level(key_id)     
        await query.answer(
            f"✅ Готово!\n\n"
            f"🔐 Ключ продлён на {add_days} дней\n"
            f"💰 Списано: {price} RUB\n\n"
            "Спасибо, что остаетесь с нами! ❤️",
            show_alert=True
        )
    else:
        await query.answer("❌ Ошибка при продлении!", show_alert=True)
