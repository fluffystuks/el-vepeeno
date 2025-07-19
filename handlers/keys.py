from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import get_or_create_user, update_balance, add_key, is_trial_used, mark_trial_used
from services.key_service import generate_key
import datetime


async def connect_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    tg_id = str(query.from_user.id)
    user_id, _ = get_or_create_user(tg_id)

    trial_used = is_trial_used(user_id)

    keyboard = []

    # 🟢 Добавляем пробный только если он ещё не использован
    
    if not trial_used:
        keyboard.append([InlineKeyboardButton("🆓 Пробный — 3 дня", callback_data='trial')])

    keyboard += [
        [InlineKeyboardButton("💳 100 RUB — 1 месяц", callback_data='100rub')],
        [InlineKeyboardButton("💳 250 RUB — 3 месяца", callback_data='250rub')],
        [InlineKeyboardButton("💳 500 RUB — 6 месяцев", callback_data='500rub')],
        [InlineKeyboardButton("🔙 В меню", callback_data='back')]
    ]

    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "💡 *Выберите тариф подключения:*\n\n"
        "Все ключи работают сразу после покупки.\n",
        parse_mode="Markdown",
        reply_markup=markup
    )

async def tariff_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    choice = query.data
    tg_id = str(query.from_user.id)
    user_id, balance = get_or_create_user(tg_id)

    prices = {'trial': 0, '100rub': 100, '250rub': 250, '500rub': 500}
    durations = {'trial': 3, '100rub': 30, '250rub': 90, '500rub': 180}

    if choice == 'back':
        from handlers.start import start
        await start(update, context)
        return

    if choice == 'trial':
        if is_trial_used(user_id):
            await query.answer("❌ Вы уже использовали пробный!", show_alert=True)
            return

        result = generate_key(user_id, durations[choice])
        if isinstance(result, dict):
            add_key(
                user_id,
                result['email'],
                result['link'],
                result['expiry_time'],
                result['client_id']
            )
            mark_trial_used(user_id)

            expiry_date = datetime.datetime.fromtimestamp(result['expiry_time'] // 1000).strftime('%d.%m.%Y')  # ✅ добавлено

            await query.edit_message_text(
                f"🎉 *Пробный ключ активирован!*\n\n"
                f"📧 *Email:* `{result['email']}`\n"
                f"🔑 *Ключ:*\n`{result['link']}`\n\n"
                f"⏳ *Действует до:* *{expiry_date}*\n\n"
                "🆓 Пробный ключ можно использовать один раз.\n"
                "📜 При необходимости откройте раздел *Инструкция*.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="back")]]
                )
            )
        else:
            await query.edit_message_text(f"{result}")
        return

    elif choice in prices:
        price = prices[choice]
        days = durations[choice]

        if balance < price:
            await query.answer(f"❌ Недостаточно средств! Баланс: {balance} RUB.", show_alert=True)
            return

        update_balance(user_id, balance - price)

        result = generate_key(user_id, days)
        if isinstance(result, dict) and 'email' in result:
            add_key(
                user_id,
                result['email'],
                result['link'],
                result['expiry_time'],
                result['client_id']
            )

            expiry_date = datetime.datetime.fromtimestamp(result['expiry_time'] // 1000).strftime('%d.%m.%Y')
            new_balance = balance - price

            await query.edit_message_text(
                f"🎉 *Тариф активирован!* 🎉\n\n"
                f"📧 *Email:* `{result['email']}`\n"
                f"🔑 *Ваш ключ:*\n`{result['link']}`\n\n"
                f"⏳ *Срок действия до:* *{expiry_date}*\n"
                f"💰 *Новый баланс:* *{new_balance} RUB*\n\n"
                f"✅ Скопируйте ключ и вставьте его в приложение VPN.\n"
                f"📜 При необходимости откройте раздел *Инструкция*.\n\n"
                f"Спасибо, что вы с нами! ❤️",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 В меню", callback_data="back")]]
                )
            )
        else:
            await query.edit_message_text(
                f"{result}",
                parse_mode="Markdown"
            )