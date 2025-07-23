from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import get_or_create_user, is_trial_used
from handlers.referral import process_signup

async def start(update: Update, context: CallbackContext):
    tg_id = str(update.effective_user.id)
    user_id, _ = get_or_create_user(tg_id)
    if update.message and context.args:
        ref_tg = context.args[0]
        await process_signup(update, context, ref_tg, user_id)
    trial = is_trial_used(user_id)

    if not trial:
        # 🆕 Первый запуск
        text = (
            "🎉 *Добро пожаловать!*\n\n"
            "🆓 У вас доступен *бесплатный пробный ключ на 3 дня*.\n\n"
            "Чтобы начать:\n"
            "1️⃣ Нажмите *«Пробный доступ»*\n"
            "2️⃣ Готовый ключ появится в *Аккаунте*\n"
            "3️⃣ Подключитесь по *Инструкции*\n\n"
            "Если будут вопросы — заходите в *Помощь* ❤️"
        )

        keyboard = [
            [InlineKeyboardButton("🎁 Пробный доступ", callback_data="trial")],
            [
                InlineKeyboardButton("📜 Инструкция", callback_data="instruction"),
                InlineKeyboardButton("💬 Поддержка", callback_data="help")
            ],
            [InlineKeyboardButton("🎁 Реферальная программа", callback_data="referral")]
        ]

    else:
        text = (
            "🌟 *Добро пожаловать!* 🌟\n\n"
            f"🔹 *Ваш TG ID:* `{tg_id}`\n"
            "⚙️ *Что можно сделать:* управление ключами, пополнение баланса и подключение — в пару касаний\n\n"
            "❓ *Нужна помощь?* Кнопка «Помощь» всегда рядом."
        )

        keyboard = [
            [
                InlineKeyboardButton("🔗 Выбрать подписку", callback_data='connect'),
                InlineKeyboardButton("📜 Инструкция", callback_data='instruction')
            ],
            [
                InlineKeyboardButton("👤 Аккаунт / Ключи", callback_data='account'),
                InlineKeyboardButton("💰 Пополнить баланс", callback_data='top_up')
            ],
            [
                InlineKeyboardButton("🤓 Помощь", callback_data='help'),
                InlineKeyboardButton("📌 Правила использования", callback_data="rules")
            ],
            [InlineKeyboardButton("🎁 Реферальная программа", callback_data="referral")]
        ]

    markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
