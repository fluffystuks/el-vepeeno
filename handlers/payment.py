from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler
from db import (
    get_or_create_user, has_pending_payment,
    save_payment, get_last_payment_id, update_payment_status,
    update_balance, get_payment_amount, get_pending_payment_ids
)
from services.payment_service import create_payment, check_payment, cancel_payment
from yookassa import Payment
from uuid import uuid4

PAYMENT_AMOUNT = 1

# ================================================
# /pay — старт оплаты
# ================================================
async def pay_handler(update: Update, context: CallbackContext) -> int:
    tg_id = str(update.effective_user.id)
    user_id, _ = get_or_create_user(tg_id)
    chat_id = update.effective_chat.id


    if has_pending_payment(user_id):
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отменить платёж", callback_data="cancel_payment")]
        ])

        if update.message:
            await update.message.reply_text(
                "❌ У вас уже есть незавершённый платёж!\n"
                "Если хотите отменить его и создать новый — нажмите кнопку ниже.",
                reply_markup=markup
            )
        else:
            await update.callback_query.message.reply_text(
                "❌ У вас уже есть незавершённый платёж!\n"
                "Если хотите отменить его и создать новый — нажмите кнопку ниже.",
                reply_markup=markup
            )
        return ConversationHandler.END

    if update.message:
        await update.message.reply_text("Введите сумму пополнения (мин. 50 RUB):")
    else:
        await update.callback_query.message.reply_text("Введите сумму пополнения (мин. 50 RUB):")

    return PAYMENT_AMOUNT 


# ================================================
# Ввод суммы
# ================================================
async def process_payment_amount(update: Update, context: CallbackContext) -> int:
    try:
        amount = float(update.message.text)
        if amount < 50:
            await update.message.reply_text("Сумма должна быть не менее 50 RUB.")
            return PAYMENT_AMOUNT

        tg_id = str(update.message.from_user.id)
        user_id, _ = get_or_create_user(tg_id)
        url, payment_id = create_payment(tg_id, amount)

        if not url:
            await update.message.reply_text("❌ Ошибка создания платежа.")
            return PAYMENT_AMOUNT

        save_payment(user_id, payment_id, amount)


        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Оплатить", url=url)],
            [InlineKeyboardButton("✅ Проверить платёж", callback_data="check_payment")]
        ])

        await update.message.reply_text(
            f"Перейдите по ссылке для оплаты <b>{amount} RUB</b>:\n\n"
            "После оплаты нажмите кнопку <b>✅ Проверить платёж</b>\n"
            "или введите команду <code>/check_payment</code>.",
            parse_mode="HTML",
            reply_markup=markup
        )
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Введите корректную сумму.")
        return PAYMENT_AMOUNT

async def timeout_handler(update, context):
    await update.message.reply_text(
        "⌛️ *Время ожидания истекло.*\n\nПопробуйте снова через /pay, когда будете готовы.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel_handler(update, context):
    await update.message.reply_text(
        "❌ Оплата отменена. Используйте /pay, когда будете готовы.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ================================================
# Проверка оплаты вручную
# ================================================
async def check_payment_handler(update: Update, context: CallbackContext):
    tg_id = str(update.effective_user.id)
    user_id, balance = get_or_create_user(tg_id)
    target = update.callback_query.message if update.callback_query else update.message

    if update.callback_query:
        await update.callback_query.answer()

    payment_id = get_last_payment_id(user_id)
    if not payment_id:
        await target.reply_text("Нет ожидающих платежей.")
        return

    status = check_payment(payment_id)
    if status == "waiting_for_capture":
        Payment.capture(payment_id, idempotency_key=uuid4())
        status = "succeeded"

    if status == "succeeded":
        update_payment_status(payment_id, "succeeded")
        amount = get_payment_amount(payment_id)
        new_balance = balance + amount
        update_balance(user_id, new_balance)

        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 В меню", callback_data="back")]]
        )
        await target.reply_text(
            f"✅ <b>Платёж успешно прошёл!</b>\n\n"
            f"💰 Пополнено: <b>{amount} RUB</b>\n"
            f"💳 Новый баланс: <b>{new_balance} RUB</b>\n\n"
            "Спасибо за поддержку сервиса! ❤️",
            parse_mode="HTML",
            reply_markup=markup,
        )


    elif status == "pending":
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отменить платёж", callback_data="cancel_payment")]
        ])
        await target.reply_text(
            "⏳ <i>Платёж ещё не подтверждён.</i>\n\n"
            "Попробуйте чуть позже или отмените платёж.",
            parse_mode="HTML",
            reply_markup=markup
        )

    elif status == "canceled":
        await target.reply_text(
            "❌ <b>Платёж был отменён.</b>\nВы можете создать новый через /pay.",
            parse_mode="HTML"
        )
    else:
        await target.reply_text(
            f"❌ <b>Статус платежа:</b> <code>{status}</code>\n"
            "Если есть вопросы — напишите в поддержку.",
            parse_mode="HTML"
        )

# ================================================
# Отмена вручную
# ================================================
async def cancel_payment_handler(update: Update, context: CallbackContext):
    tg_id = str(update.effective_user.id)
    user_id, _ = get_or_create_user(tg_id)
    payment_ids = get_pending_payment_ids(user_id)
    for pid in payment_ids:
        cancel_payment(pid)

    if update.callback_query:
        await update.callback_query.answer("✅ Платёж отменён!")
        await update.callback_query.edit_message_text(
            "✅ Ваш платёж отменён.\nТеперь вы можете создать новый через /pay."
        )
    elif update.message:
        await update.message.reply_text(
            "✅ Все незавершённые платежи отменены.\nТеперь вы можете создать новый через /pay."
        )
