from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from db import (
    get_or_create_user, has_pending_payment, cancel_pending_payment,
    save_payment, get_last_payment_id, update_payment_status,
    update_balance, get_payment_amount
)
from services.payment_service import create_payment, check_payment

PAYMENT_AMOUNT = 1

# ================================================
# /pay — ждёт сумму + ставит автоотмену через JobQueue
# ================================================
async def pay_handler(update: Update, context: CallbackContext) -> int:
    if update.message:
        user_id, _ = get_or_create_user(str(update.message.from_user.id))
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_id, _ = get_or_create_user(str(update.callback_query.from_user.id))
        chat_id = update.callback_query.message.chat_id
        await update.callback_query.answer()
    else:
        return ConversationHandler.END

    if has_pending_payment(user_id):
        keyboard = [[InlineKeyboardButton("❌ Отменить платёж", callback_data="cancel_payment")]]
        markup = InlineKeyboardMarkup(keyboard)
        text = (
            "❌ У вас уже есть незавершённый платёж!\n"
            "Если хотите отменить его и создать новый — нажмите кнопку ниже."
        )
        if update.message:
            await update.message.reply_text(text, reply_markup=markup)
        else:
            await update.callback_query.message.reply_text(text, reply_markup=markup)
        return ConversationHandler.END

    if update.message:
        await update.message.reply_text("Введите сумму пополнения (мин. 50 RUB):")
    else:
        await update.callback_query.message.reply_text("Введите сумму пополнения (мин. 50 RUB):")

    # 🟢 Ставим задачу автоотмены — даём имя, чтобы потом снять
    context.job_queue.run_once(
        cancel_waiting_amount,
        120,
        chat_id=chat_id,
        name=f"cancel_{chat_id}"
    )

    return PAYMENT_AMOUNT

# ================================================
# Таймер автоотмены
# ================================================
async def cancel_waiting_amount(context: CallbackContext):
    context.chat_data["expired"] = True  # ставим флаг
    await context.bot.send_message(
        context.job.chat_id,
        "⏰ Время на ввод суммы истекло. Попробуйте снова через /pay. Если же /pay не работает, попробуйте ввести любое число, возможно, бот ожидает число."
    )


# ================================================
# Обработка введённой суммы + отключение таймера
# ================================================
async def process_payment_amount(update: Update, context: CallbackContext) -> int:
    if context.chat_data.get("expired"):
        await update.message.reply_text(
            "⏰ Время на ввод суммы истекло. Попробуйте снова через /pay. Если же /pay не работает, попробуйте ввести любое число, возможно, бот ожидает число."
        )
        return ConversationHandler.END
    
    try:
        amount = float(update.message.text)
        if amount < 50:
            await update.message.reply_text("Сумма должна быть не менее 50 RUB.")
            return PAYMENT_AMOUNT

        user_id, _ = get_or_create_user(str(update.message.from_user.id))
        url, payment_id = create_payment(user_id, amount)

        if not url:
            await update.message.reply_text("Ошибка создания платежа.")
            return PAYMENT_AMOUNT

        save_payment(user_id, payment_id, amount)

        # 🟢 Снимаем задачу таймера, если пользователь всё ввёл вовремя
        for job in context.job_queue.jobs():
            if job.name == f"cancel_{update.effective_chat.id}":
                job.schedule_removal()

        keyboard = [
            [InlineKeyboardButton("💰 Оплатить", url=url)],
            [InlineKeyboardButton("✅ Проверить платёж", callback_data="check_payment")]
        ]
        markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Перейдите по ссылке для оплаты {amount} RUB:\n\n"
            "После оплаты обязательно нажмите кнопку ✅ Проверить платёж "
            "или введите команду /check_payment — чтобы бот подтвердил и пополнил ваш баланс!"
        ,
            reply_markup=markup
        )
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Введите корректную сумму.")
        return PAYMENT_AMOUNT

# ================================================
# Проверка оплаты вручную
# ================================================
async def check_payment_handler(update: Update, context: CallbackContext):
    if update.callback_query:
        user_id, balance = get_or_create_user(str(update.callback_query.from_user.id))
        await update.callback_query.answer()
        target = update.callback_query.message
    else:
        user_id, balance = get_or_create_user(str(update.message.from_user.id))
        target = update.message

    payment_id = get_last_payment_id(user_id)

    if not payment_id:
        await target.reply_text("Нет ожидающих платежей.")
        return

    status = check_payment(payment_id)
    if status == "succeeded":
        update_payment_status(payment_id, "succeeded")
        amount = get_payment_amount(payment_id)
        new_balance = balance + amount
        update_balance(user_id, new_balance)

        await target.reply_text(
            f"✅ *Платёж подтверждён!*\n\n"
            f"💰 Баланс пополнен на {amount} RUB.\n"
            f"💰 Новый баланс: {new_balance} RUB.",
            parse_mode="Markdown"
        )

    elif status == "pending":
        keyboard = [[InlineKeyboardButton("❌ Отменить платёж", callback_data="cancel_payment")]]
        markup = InlineKeyboardMarkup(keyboard)
        await target.reply_text(
            f"⏳ *Платёж ещё не подтверждён.*\n\n"
            f"Пожалуйста, попробуйте чуть позже или отмените платёж кнопкой ниже.",
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif status == "canceled":
        await target.reply_text(
            f"❌ *Платёж был отменён.*\n\n"
            f"Вы можете создать новый через /pay.",
            parse_mode="Markdown"
        )

    else:
        await target.reply_text(
            f"❌ *Статус платежа:* `{status}`\n"
            f"Если есть вопросы, напишите в Поддержку.",
            parse_mode="Markdown"
        )

# ================================================
# Отмена платежа вручную
# ================================================
async def cancel_payment_handler(update: Update, context: CallbackContext):
    if update.callback_query:
        user_id, _ = get_or_create_user(str(update.callback_query.from_user.id))
        cancel_pending_payment(user_id)
        await update.callback_query.answer("✅ Платёж отменён!")
        await update.callback_query.edit_message_text(
            "✅ Ваш незавершённый платёж отменён.\nТеперь вы можете создать новый через /pay."
        )
    elif update.message:
        user_id, _ = get_or_create_user(str(update.message.from_user.id))
        cancel_pending_payment(user_id)
        await update.message.reply_text(
            "✅ Все незавершённые платежи отменены.\nТеперь вы можете создать новый через /pay."
        )