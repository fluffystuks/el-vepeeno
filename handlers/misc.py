from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

async def instruction_handler(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data='back')]]
    markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "📜 *Инструкция по подключению VPN:*\n\n"
        "Для вашего удобства мы подготовили подробное руководство по подключению ключа.\n\n"
        "👉 [Перейти к инструкции](https://telegra.ph/Instrukciya-po-podklyucheniyu-VPN-klyucha-07-14)",
        parse_mode="Markdown",
        reply_markup=markup
    )

async def rules_handler(update: Update, context: CallbackContext):
    text = (
        "📌 *Правила использования Pien VPN* 📌\n\n"
        "1️⃣ Конфиденциальность — наша главная ценность. Мы не собираем журналы подключений, не сохраняем историю посещений и не передаём ваши личные данные кому-либо ещё. Всё, что вы делаете через наш VPN, остаётся только между вами и защищённым соединением.\n\n"
        "2️⃣ Мы просим всех клиентов использовать сервис в рамках закона. Pien VPN создан для безопасного и свободного интернета, а не для действий, которые могут нарушать права других людей или действующие нормы законодательства.\n\n"
        "3️⃣ Ваши данные и трафик надёжно защищены современным шифрованием. Независимо от того, где вы находитесь, Pien VPN помогает сохранить ваши данные в безопасности и скрыть вашу активность от посторонних глаз.\n\n"
        "4️⃣ Мы гарантируем пользователям анонимность и безопасность, но доверяем каждому, что сервис будет использоваться ответственно и без злоупотреблений.\n\n"
        "5️⃣ 🔄 *Честное использование:* Pien VPN работает для всех честных пользователей, но если кто-то будет перегружать сеть — например, скачивать огромные объёмы данных сутками напролёт — мы можем временно ограничить доступ для сохранения стабильной скорости для всех клиентов. Лимит IP на подключение для 1 ключа - 2. Для обычного использования это ограничение не актуально."
    )

    keyboard = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back")]]
    markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)

async def help_handler(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data='back')]]
    markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "🤝 *Раздел поддержки*\n\n"
        "Если у вас возникли вопросы или требуется помощь, вы можете напрямую связаться с администратором.\n\n"
        "📲 [Написать администратору](https://t.me/othrwise)",
        parse_mode="Markdown",
        reply_markup=markup
    )
