from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

async def instruction_handler(update: Update, context: CallbackContext):
    await update.callback_query.answer()
    tg_id = str(update.effective_user.id)
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
    await update.callback_query.answer()
    text = (
        "📌 *Правила использования Pien VPN* 📌\n\n"
        "1️⃣ *Конфиденциальность* — наша главная ценность. Мы не ведём журналы подключений, не сохраняем историю посещений и не передаём ваши личные данные третьим лицам.\n\n"
        "2️⃣ *Используйте VPN законно.* Pien VPN предназначен для защиты ваших данных и безопасности, но не для доступа к запрещённым ресурсам или обхода блокировок.\n\n"
        "3️⃣ *Безопасность и шифрование.* Мы применяем современные алгоритмы защиты, чтобы ваш трафик оставался закрытым от взломщиков, провайдеров и посторонних.\n\n"
        "4️⃣ *Анонимность и самостоятельность.* Мы не отслеживаем активность, поэтому вы сами отвечаете за то, как используете VPN.\n\n"
        "5️⃣ *Честная нагрузка и стабильность.* Лимит — не более *2 IP‑адресов на ключ*. Если один юзер перегружает сеть (например, скачивает гигабайты без остановки), нам придётся ограничить доступ ради стабильности для всех.\n\n"
        "🚫 Обратите внимание: Pien VPN *не позиционируется* как средство обхода блокировок или доступа к заблокированным ресурсам. Любая реклама в таком ключе противоречит российскому закону и может повлечь юридические последствия.\n"
    )

    keyboard = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back")]]
    markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)

async def help_handler(update: Update, context: CallbackContext):
    await update.callback_query.answer()
    tg_id = str(update.effective_user.id)
    keyboard = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data='back')]]
    markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        "🤝 *Раздел поддержки*\n\n"
        "Если у вас возникли вопросы или требуется помощь, вы можете напрямую связаться с администратором.\n\n"
        "📲 [Написать администратору](https://t.me/othrwise)\n"
        f"Ваш TG ID: `{tg_id}`",
        parse_mode="Markdown",
        reply_markup=markup
    )