# services/admin_panel.py
import asyncio
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from config import ADMIN_TG_ID
from db import DB_NAME

# --- стадии диалога ---
WAITING_MESSAGE = 1
WAITING_TARGET = 2

# --- вспомогательные функции ---
def _is_admin(user_id: int) -> bool:
    return str(user_id) == str(ADMIN_TG_ID)

def _get_all_users():
    """tg_id всех из таблицы users"""
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT tg_id FROM users WHERE tg_id IS NOT NULL")
        return [row[0] for row in cur.fetchall()]

def _get_active_users():
    """tg_id всех, у кого есть хотя бы один активный ключ"""
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT u.tg_id
            FROM users u
            JOIN keys k ON u.id = k.user_id
            WHERE k.active = 1 AND u.tg_id IS NOT NULL
        """)
        return [row[0] for row in cur.fetchall()]

# --- /admin ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        await update.message.reply_text("⛔️ Доступ запрещён.")
        return ConversationHandler.END

    await update.message.reply_text("📝 Отправьте сообщение, которое хотите разослать:")
    return WAITING_MESSAGE


# --- шаг 1: получение текста ---
async def handle_message_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ Сообщение пустое. Введите снова.")
        return WAITING_MESSAGE

    context.user_data["broadcast_text"] = text
    kb = [
        [InlineKeyboardButton("✅ Активные пользователи (есть ключ)", callback_data="target:active")],
        [InlineKeyboardButton("👥 Все пользователи (из users)", callback_data="target:all")],
        [InlineKeyboardButton("❌ Отмена", callback_data="target:cancel")],
    ]
    await update.message.reply_text(
        "📣 Кому отправить сообщение?",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return WAITING_TARGET


# --- шаг 2: выбор аудитории ---
async def choose_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not _is_admin(user_id):
        await query.edit_message_text("⛔️ Доступ запрещён.")
        return ConversationHandler.END

    data = query.data
    text = context.user_data.get("broadcast_text", "")
    if data == "target:cancel":
        await query.edit_message_text("❌ Рассылка отменена.")
        return ConversationHandler.END

    if data == "target:active":
        targets = _get_active_users()
        group = "пользователям с активными ключами"
    elif data == "target:all":
        targets = _get_all_users()
        group = "всем пользователям"
    else:
        return ConversationHandler.END

    context.user_data["broadcast_targets"] = targets

    kb = [
        [InlineKeyboardButton("🚀 Подтвердить отправку", callback_data="target:send")],
        [InlineKeyboardButton("↩️ Отмена", callback_data="target:cancel")],
    ]
    await query.edit_message_text(
        f"✅ Сообщение готово к рассылке {group}.\n\n"
        f"Текст:\n{text}",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return WAITING_TARGET


# --- шаг 3: подтверждение и рассылка ---
async def perform_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not _is_admin(user_id):
        await query.edit_message_text("⛔️ Доступ запрещён.")
        return ConversationHandler.END

    targets = context.user_data.get("broadcast_targets", [])
    text = context.user_data.get("broadcast_text", "")
    if not targets or not text:
        await query.edit_message_text("❌ Нет данных для рассылки.")
        return ConversationHandler.END

    await query.edit_message_text("🚀 Начинаю рассылку...")
    sent, failed = 0, 0
    for tg in targets:
        try:
            await context.bot.send_message(chat_id=tg, text=text)
            sent += 1
        except Exception as e:
            print(f"Ошибка отправки {tg}: {e}")
            failed += 1
        await asyncio.sleep(0.05)  # не спамим

    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ Рассылка завершена!\nУспешно: {sent}\nОшибок: {failed}"
    )
    return ConversationHandler.END