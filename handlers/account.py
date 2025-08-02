from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import (
    get_or_create_user,
    get_all_keys,
    get_key_by_id,
    update_key_info,
)
import datetime,time

# ===============================================
# 📂 Профиль пользователя: список всех ключей
# ===============================================
async def account_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    tg_id = str(query.from_user.id)
    user_id, balance = get_or_create_user(tg_id)

    keys = get_all_keys(user_id)
    keyboard = []

    for key in keys:
        key_id, email, expiry, active, _ = key
        days_left = max(0, (expiry - int(time.time())) // 86400)
        expiry_date = datetime.datetime.fromtimestamp(expiry).strftime('%d.%m.%Y')
        status = "✅ Активен" if active else "❌ Не активен"
        text = f"{email} — {days_left} дн. {status}"

        keyboard.append([InlineKeyboardButton(text, callback_data=f"key_{key_id}")])

    keyboard.append([InlineKeyboardButton("🔙 В меню", callback_data="back")])
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=(
            "👤 *Ваш профиль*\n\n"
            f"💰 *Баланс:* {balance} RUB\n\n"
            "Ниже — список ваших ключей.\n"
            "Нажмите на любой, чтобы посмотреть детали или продлить срок действия ⏳\n\n"
            "Спасибо, что пользуетесь нашим сервисом! ❤️"
        ),
        parse_mode="Markdown",
        reply_markup=markup
    )



async def show_key_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    callback_data = query.data  # key_123
    key_id = int(callback_data.split("_")[1])

    key = get_key_by_id(key_id)
    if not key:
        await query.answer("Ключ не найден.", show_alert=True)
        return

    email, link, expiry, client_id, active, inbound_id = key

    expiry_date = datetime.datetime.fromtimestamp(expiry).strftime('%d-%m-%Y %H:%M')

    text = (
        "👤 *Детали ключа*\n\n"
        f"📧 *Email:* `{email}`\n"
        f"⏳ *Срок действия до:* {expiry_date}\n"
        f"🔑 *Ваш ключ:*\n`{link}`\n\n"
        "Просто скопируйте этот ключ и вставьте в приложение VPN.\n"
        "Если нужна помощь — мы рядом, загляните в раздел *Помощь* 💬"
    )

    if inbound_id == 2:
        keyboard = [[InlineKeyboardButton("🔄 Перенести", callback_data=f"transfer_{key_id}")],
                   [InlineKeyboardButton("🔙 Назад", callback_data="account")]]
        text += (
            "\n\n✨ *Сервис теперь работает только через новую систему.*\n"
            "🔄 Чтобы оставаться на связи без перебоев и проблем, пожалуйста, **перенесите ключ**.\n"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("⏳ Продлить на 30 дней — 100 RUB", callback_data=f"extend_{key_id}_30")],
            [InlineKeyboardButton("⏳ Продлить на 60 дней — 180 RUB", callback_data=f"extend_{key_id}_60")],
            [InlineKeyboardButton("🗑 Удалить ключ", callback_data=f"delete_{key_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="account")]
        ]
    markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=markup
    )


async def delete_key_prompt(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    key_id = int(query.data.split("_")[1])

    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_delete_{key_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"key_{key_id}")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Вы точно хотите удалить этот ключ?", reply_markup=markup
    )


async def delete_key_confirm(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    key_id = int(query.data.split("_")[2])
    key = get_key_by_id(key_id)
    if not key:
        await query.edit_message_text("Ключ не найден.")
        return

    _, _, _, client_id, _, inbound_id = key
    from services.delete_service import delete_client
    from db import delete_key as db_delete

    if delete_client(client_id, inbound_id):
        db_delete(key_id)
        await query.edit_message_text(
            "✅ Ключ удалён.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 В меню", callback_data="account")]]
            ),
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при удалении.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Назад", callback_data=f"key_{key_id}")]]
            ),
        )


async def transfer_key_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    key_id = int(query.data.split("_")[1])
    record = get_key_by_id(key_id)
    if not record:
        await query.answer("Ключ не найден.", show_alert=True)
        return
    email, link, expiry, client_id, active, inbound_id = record
    if inbound_id != 2:
        await query.answer("Ключ уже перенесён.", show_alert=True)
        return

    from services.key_service import create_key_with_expiry
    result = create_key_with_expiry(expiry * 1000, inbound_id=1)
    if not isinstance(result, dict):
        await query.answer("❌ Не удалось перенести ключ.", show_alert=True)
        return

    update_key_info(key_id, result["email"], result["link"], result["client_id"], 1)

    from services.delete_service import delete_client

    context.job_queue.run_once(lambda ctx: delete_client(client_id, 2), 30*60)

    await query.edit_message_text(
        "✅ Ключ успешно перенесён!\n\n"
        "⏳ Старый ключ перестанет работать через 30 минут.\n\n"
        f"🔑 Ваш новый ключ:\n`{result['link']}`\n\n"
        "🚀 Теперь вы подключены к обновлённой системе — "
        "она работает стабильнее и надёжнее даже там, "
        "где подключение ранее было проблемным.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 В меню", callback_data="account")]]
        ),
    )