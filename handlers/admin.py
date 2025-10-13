from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, ConversationHandler

from config import ADMIN_TG_ID
from db import get_active_users_tg_ids, get_all_user_tg_ids

SELECT_ACTION, WAITING_MESSAGE = range(2)


def _build_admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📡 Разослать всем", callback_data="admin_broadcast_all")],
        [InlineKeyboardButton("🛡️ Разослать активным", callback_data="admin_broadcast_active")],
        [InlineKeyboardButton("🚫 Отмена", callback_data="admin_cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def admin_panel(update: Update, context: CallbackContext) -> int:
    if update.effective_user.id != ADMIN_TG_ID:
        return ConversationHandler.END

    text = (
        "🔐 <b>Суперсекретная админ-панель</b>\n\n"
        "Выбери, кому улетит твоё сообщение. После выбора просто пришли текст — "
        "и бот сделает всё остальное."
    )

    markup = _build_admin_keyboard()

    if update.message:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")

    return SELECT_ACTION


async def admin_choose_audience(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    if query.from_user.id != ADMIN_TG_ID:
        await query.answer()
        return ConversationHandler.END

    target = "all" if query.data == "admin_broadcast_all" else "active"
    context.user_data["broadcast_target"] = target

    await query.answer()
    await query.edit_message_text(
        "✍️ Пришли сообщение для рассылки — можно отправить текст, фото, документы и т.д."
        " Мы разошлём его в точности в том виде, в каком ты его отправишь.",
    )

    return WAITING_MESSAGE


def _normalize_chat_ids(ids: List[str]) -> List[int]:
    normalized = []
    for value in ids:
        if value is None:
            continue
        try:
            normalized.append(int(value))
        except (TypeError, ValueError):
            continue
    return normalized


async def admin_broadcast_message(update: Update, context: CallbackContext) -> int:
    if update.effective_user.id != ADMIN_TG_ID:
        return ConversationHandler.END

    target = context.user_data.get("broadcast_target")
    if not target:
        await update.message.reply_text("Не выбрана аудитория для рассылки. Начни заново командой /admin.")
        return ConversationHandler.END

    recipients = (
        _normalize_chat_ids(get_all_user_tg_ids())
        if target == "all"
        else _normalize_chat_ids(get_active_users_tg_ids())
    )

    if not recipients:
        await update.message.reply_text("📭 Получателей не нашлось. Проверь базу и попробуй ещё раз позже.")
        context.user_data.pop("broadcast_target", None)
        return ConversationHandler.END

    sent = 0
    failed = 0
    for chat_id in recipients:
        try:
            await context.bot.copy_message(
                chat_id=chat_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
            )
            sent += 1
        except TelegramError:
            failed += 1

    context.user_data.pop("broadcast_target", None)

    await update.message.reply_text(
        f"✅ Рассылка завершена. Отправлено: {sent}. Ошибок: {failed}."
    )

    return ConversationHandler.END


async def admin_cancel(update: Update, context: CallbackContext) -> int:
    if update.effective_user.id == ADMIN_TG_ID and update.message:
        await update.message.reply_text("🚫 Рассылка отменена.")
    context.user_data.pop("broadcast_target", None)
    return ConversationHandler.END


async def admin_cancel_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    if query.from_user.id == ADMIN_TG_ID:
        await query.edit_message_text("🚫 Рассылка отменена.")
    context.user_data.pop("broadcast_target", None)
    return ConversationHandler.END
