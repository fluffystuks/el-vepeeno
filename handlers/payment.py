from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler
from db import (
    get_or_create_user, has_pending_payment, cancel_pending_payment,
    get_last_payment_id, update_payment_status,
    update_balance, get_payment_amount
)
from services.payment_service import check_payment

PAYMENT_AMOUNT = 1
PAYMENT_DISABLED_NOTICE = (
    "🚧 *Пополнение временно недоступно.*\n\n"
    "Мы приостановили оплату до восстановления работы сервиса."
)


# ================================================
# /pay — старт оплаты
# ================================================
async def pay_handler(update: Update, context: CallbackContext) -> int:
    tg_id = str(update.effective_user.id)
    user_id, _ = get_or_create_user(tg_id)
    target = update.callback_query.message if update.callback_query else update.message

    if has_pending_payment(user_id):
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отменить платёж", callback_data="cancel_payment")]
        ])
        await target.reply_text(
            PAYMENT_DISABLED_NOTICE
            + "\n\nУ вас есть незавершённый платёж — при желании вы можете отменить его ниже.",
            parse_mode="Markdown",
            reply_markup=markup,
        )
        return ConversationHandler.END

    await target.reply_text(PAYMENT_DISABLED_NOTICE, parse_mode="Markdown")

    return ConversationHandler.END


# ================================================
# Ввод суммы
# ================================================
async def process_payment_amount(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(PAYMENT_DISABLED_NOTICE, parse_mode="Markdown")
    return ConversationHandler.END


def _disabled_reply(update):
    return update.message.reply_text(
        PAYMENT_DISABLED_NOTICE,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )


async def timeout_handler(update, context):
    await _disabled_reply(update)
    return ConversationHandler.END


async def cancel_handler(update, context):
    await _disabled_reply(update)
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
            "❌ <b>Платёж был отменён.</b>\nПополнение будет доступно после восстановления сервиса.",
            parse_mode="HTML"
        )
    else:
        await target.reply_text(
            f"❌ <b>Статус платежа:</b> <code>{status}</code>\n"
            "Если есть вопросы — напишите в поддержку.",
            parse_mode="HTML"
        )


async def cancel_payment_handler(update: Update, context: CallbackContext):
    tg_id = str(update.effective_user.id)
    user_id, _ = get_or_create_user(tg_id)
    cancel_pending_payment(user_id)

    if update.callback_query:
        await update.callback_query.answer("✅ Платёж отменён!")
        await update.callback_query.edit_message_text(
            "✅ Ваш платёж отменён. Ожидайте возобновления сервиса для новых пополнений."
        )
    elif update.message:
        await update.message.reply_text(
            "✅ Все незавершённые платежи отменены. Ожидайте возобновления сервиса для новых пополнений."
        )
