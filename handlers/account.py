from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import get_or_create_user, get_all_keys, get_key_by_id
import datetime,time

# ===============================================
# 📂 Профиль пользователя: список всех ключей
# ===============================================
async def account_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    tg_id = str(query.from_user.id)
    user_id, balance = get_or_create_user(tg_id)

    keys = get_all_keys(user_id)
    keyboard = []

    for key in keys:
        key_id, email, expiry_ms, active = key
        days_left = max(0, (expiry_ms // 1000 - int(time.time())) // 86400)
        expiry_date = datetime.datetime.fromtimestamp(expiry_ms // 1000).strftime('%d.%m.%Y')
        status = "✅ Активен" if active else "❌ Не активен"
        text = f"{email} — {days_left} дн. {status}"

        keyboard.append([InlineKeyboardButton(text, callback_data=f"key_{key_id}")])

    keyboard.append([InlineKeyboardButton("🔙 В меню", callback_data="back")])
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=(
            "👤 *Ваши ключи:*\n\n"
            f"💰 *Баланс:* {balance} RUB\n\n"
            "Выберите ключ, чтобы посмотреть детали или продлить ⏳"
        ),
        parse_mode="Markdown",
        reply_markup=markup
    )


# ===============================================
# 📂 Просмотр одного ключа: детали и кнопка Назад
# ===============================================
async def show_key_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    callback_data = query.data  # key_123
    key_id = int(callback_data.split("_")[1])

    from db import get_key_by_id
    key = get_key_by_id(key_id)
    if not key:
        await query.answer("Ключ не найден.", show_alert=True)
        return

    email, link, expiry_ms, client_id, *_ = key

    expiry_date = datetime.datetime.fromtimestamp(expiry_ms // 1000).strftime('%d-%m-%Y %H:%M')

    text = (
        "👤 *Детали ключа*\n\n"
        f"📧 *Email:* `{email}`\n"
        f"⏳ *Срок действия до:* {expiry_date}\n"
        f"🔑 *Ваш ключ:*\n`{link}`\n\n"
        "Скопируйте ключ и используйте его в приложении.\n"
        "Если возникнут вопросы, напишите в Помощь."
    )

    keyboard = [
        [InlineKeyboardButton("⏳ Продлить на 30 дней — 100 RUB", callback_data=f"extend_{key_id}_30")],
        [InlineKeyboardButton("⏳ Продлить на 60 дней — 180 RUB", callback_data=f"extend_{key_id}_60")],
        [InlineKeyboardButton("🔙 Назад", callback_data="account")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=markup
    )