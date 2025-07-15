from db import get_key_by_id, update_key_expiry, activate_key, get_or_create_user, update_balance
from services.extend_service import extend_key  



async def extend_key_handler(update, context):
    query = update.callback_query
    data = query.data  # пример: extend_1_30
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

    email, link, expiry_ms, client_id, active = key

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
        current_expiry_ms=expiry_ms,
        add_days=add_days
    )

    if result:
        update_key_expiry(key_id, result)
        activate_key(key_id)
        update_balance(user_id, balance - price)
        await query.answer(f"✅ Ключ продлён на {add_days} дней!\n💰 Списано {price} RUB.", show_alert=True)
    else:
        await query.answer("❌ Ошибка при продлении!", show_alert=True)
