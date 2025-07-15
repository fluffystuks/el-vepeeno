from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("🔗 Подключить", callback_data='connect'),
            InlineKeyboardButton("📜 Инструкция", callback_data='instruction')
        ],
        [
            InlineKeyboardButton("👤 Аккаунт / Ключи", callback_data='account'),
            InlineKeyboardButton("💰 Пополнить баланс", callback_data='top_up')
        ],
        [
            InlineKeyboardButton("🤓 Помощь", callback_data='help'),
            InlineKeyboardButton("📌 Правила использования", callback_data="rules")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🌟 *Добро пожаловать!* 🌟\n\n"
        "Выберите действие 👇"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
