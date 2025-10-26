from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import get_or_create_user, add_key, is_trial_used, mark_trial_used
from services.key_service import generate_key
import datetime

PURCHASE_DISABLED_NOTICE = (
    "🚧 Покупка подписок временно недоступна.\n"
    "Мы сообщим, когда сервис возобновит работу."
)


async def connect_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
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
    balance = int(get_or_create_user(tg_id)[1])
    await query.edit_message_text(
        "💡 *Выберите тариф подключения:*\n\n"
        f"💰 *Ваш баланс:* *{balance} RUB*\n\n"
        "⚠️ Оплачиваемые тарифы временно недоступны. Пробный ключ работает как обычно.",
        parse_mode='Markdown',
        reply_markup=markup
    )


async def tariff_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
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

        result = generate_key(user_id, durations[choice], tg_id)
        if isinstance(result, dict):
            add_key(
                user_id,
                result['email'],
                result['link'],
                result['expiry_time'] // 1000,
                result['client_id'],
                1,
            )
            mark_trial_used(user_id)

            expiry_date = datetime.datetime.fromtimestamp(result['expiry_time'] // 1000).strftime('%d.%m.%Y')

            await query.edit_message_text(
                f"🎉 *Пробный ключ активирован!*\n\n"
                f"📧 *Email:* `{result['email']}`\n"
                f"🔑 *Ключ:*\n`{result['link']}`\n\n"
                f"⏳ *Действует до:* *{expiry_date}*\n\n"
                "⚠️ *Ограничение:* до *2 устройств одновременно*.\n\n"
                "📜 При необходимости откройте раздел *Инструкция*.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="back")]]
                )
            )
        else:
            await query.edit_message_text(f"{result}")
        return

    if choice in prices:
        await query.answer(PURCHASE_DISABLED_NOTICE, show_alert=True)
        return

    await query.answer("❌ Некорректный выбор.", show_alert=True)
