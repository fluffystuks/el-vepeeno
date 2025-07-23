from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import (
    get_or_create_user,
    assign_referrer,
    create_bonus,
    get_user_referrer,
    increment_paid_referrals,
    count_successful_payments,
    get_user_active_bonuses,
    get_bonus_balance,
    consume_all_bonuses,
    get_key_by_id,
    update_key_expiry,
    reset_notified_level,
    get_key_owner,
    get_all_keys,
)
from services.extend_service import extend_key

SIGNUP_REFERRER_BONUS = 7
SIGNUP_USER_BONUS = 2
PAYMENT_BONUS_DAYS = 7
MILESTONE_BONUSES = {3: 10, 5: 15}


def generate_referral_link(bot_username: str, tg_id: str) -> str:
    return f"https://t.me/{bot_username}?start={tg_id}"


async def process_signup(update: Update, context: CallbackContext, ref_tg_id: str, user_id: int):
    ref_user_id, _ = get_or_create_user(ref_tg_id)
    if assign_referrer(user_id, ref_user_id):
        create_bonus(ref_user_id, SIGNUP_REFERRER_BONUS, "referral_signup")
        create_bonus(user_id, SIGNUP_USER_BONUS, "referral_signup")
        try:
            await context.bot.send_message(ref_tg_id, "🎉 Ваш друг зарегистрировался по вашей ссылке! Бонус +7 дней добавлен.")
        except Exception:
            pass
        try:
            await update.message.reply_text("🎁 Вам начислен бонус за регистрацию по ссылке (+2 дня)")
        except Exception:
            pass


async def process_first_payment(context: CallbackContext, user_id: int, amount: float):
    if amount < 100:
        return
    if count_successful_payments(user_id) != 1:
        return
    referrer_id = get_user_referrer(user_id)
    if not referrer_id:
        return
    create_bonus(referrer_id, PAYMENT_BONUS_DAYS, "referral_payment")
    create_bonus(user_id, PAYMENT_BONUS_DAYS, "first_payment")
    count = increment_paid_referrals(referrer_id)
    bonus_days = MILESTONE_BONUSES.get(count)
    if bonus_days:
        create_bonus(referrer_id, bonus_days, f"milestone_{count}")
    bot = context.bot
    try:
        await bot.send_message(chat_id=str(referrer_id), text="🎉 Ваш реферал совершил первую оплату. Бонус +7 дней добавлен!")
    except Exception:
        pass
    try:
        await bot.send_message(chat_id=str(user_id), text="🎁 Спасибо за оплату! Вам начислен бонус +7 дней")
    except Exception:
        pass


def format_bonus(bonus):
    from datetime import datetime
    expiry = datetime.fromtimestamp(bonus[3]).strftime('%d.%m.%Y')
    return f"+{bonus[1]} дн. до {expiry} ({bonus[2]})"


async def list_bonuses(update: Update, context: CallbackContext):
    tg_id = str(update.effective_user.id)
    user_id, _ = get_or_create_user(tg_id)
    balance = get_bonus_balance(user_id)
    bonuses = get_user_active_bonuses(user_id)
    if balance <= 0:
        text = "У вас нет бонусов."
    else:
        text = f"Ваш бонус-баланс: {balance} дн."  # Russian
        if bonuses:
            text += "\n\nАктивные бонусы:\n" + "\n".join(format_bonus(b) for b in bonuses)
    await update.message.reply_text(text)


async def apply_bonus(update: Update, context: CallbackContext):
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Использование: /apply_bonus <key_id>")
        return
    try:
        key_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID должны быть числами")
        return
    tg_id = str(update.effective_user.id)
    user_id, _ = get_or_create_user(tg_id)
    total_days = consume_all_bonuses(user_id)
    if total_days <= 0:
        await update.message.reply_text("У вас нет бонусов")
        return
    owner = get_key_owner(key_id)
    if owner != user_id:
        await update.message.reply_text("Ключ не найден")
        return
    key = get_key_by_id(key_id)
    if not key:
        await update.message.reply_text("Ключ не найден")
        return
    email, _, expiry_ms, client_id, active = key
    result = extend_key(email, client_id, active, expiry_ms, total_days)
    if result:
        update_key_expiry(key_id, result)
        reset_notified_level(key_id)
        await update.message.reply_text(f"✅ Бонус применён, ключ продлён на {total_days} дней")
    else:
        await update.message.reply_text("❌ Ошибка при продлении")


async def referral_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    tg_id = str(query.from_user.id)
    link = generate_referral_link(context.bot.username, tg_id)

    keyboard = [
        [InlineKeyboardButton("🎁 Мои бонусы", callback_data="show_bonuses")],
        [InlineKeyboardButton("🖊 Использовать", callback_data="use_bonus")],
        [InlineKeyboardButton("🔙 В меню", callback_data="back")],
    ]

    text = (
        "🤝 *Реферальная программа*\n\n"
        "Приглашайте друзей и получайте бонусы за регистрацию и оплату.\n\n"
        f"🔗 *Ваша ссылка:*\n`{link}`"
    )

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def show_bonuses(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    tg_id = str(query.from_user.id)
    user_id, _ = get_or_create_user(tg_id)
    balance = get_bonus_balance(user_id)
    bonuses = get_user_active_bonuses(user_id)
    if balance <= 0:
        text = "У вас нет бонусов."
    else:
        text = f"Ваш бонус-баланс: {balance} дн."
        if bonuses:
            text += "\n\nАктивные бонусы:\n" + "\n".join(format_bonus(b) for b in bonuses)

    keyboard = [
        [InlineKeyboardButton("🖊 Использовать", callback_data="use_bonus")],
        [InlineKeyboardButton("🔙 Назад", callback_data="referral")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def use_bonus_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    tg_id = str(query.from_user.id)
    user_id, _ = get_or_create_user(tg_id)
    balance = get_bonus_balance(user_id)
    if balance <= 0:
        keyboard = [[InlineKeyboardButton("\ud83d\udd19 \u041d\u0430\u0437\u0430\u0434", callback_data="referral")]]
        await query.edit_message_text("\u0423 \u0432\u0430\u0441 \u043d\u0435\u0442 \u0431\u043e\u043d\u0443\u0441\u043e\u0432.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    keys = get_all_keys(user_id)
    if not keys:
        keyboard = [[InlineKeyboardButton("\ud83d\udd19 \u041d\u0430\u0437\u0430\u0434", callback_data="referral")]]
        await query.edit_message_text("\u0423 \u0432\u0430\u0441 \u043d\u0435\u0442 \u043a\u043b\u044e\u0447\u0435\u0439.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    keyboard = [[InlineKeyboardButton(k[1], callback_data=f"use_bonus_key_{k[0]}")] for k in keys]
    keyboard.append([InlineKeyboardButton("\ud83d\udd19 \u041d\u0430\u0437\u0430\u0434", callback_data="show_bonuses")])
    await query.edit_message_text("\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043a\u043b\u044e\u0447:", reply_markup=InlineKeyboardMarkup(keyboard))


async def apply_bonus_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    key_id = int(parts[-1])
    tg_id = str(query.from_user.id)
    user_id, _ = get_or_create_user(tg_id)
    owner = get_key_owner(key_id)
    if owner != user_id:
        await query.edit_message_text("\u041a\u043b\u044e\u0447 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d.")
        return
    total_days = consume_all_bonuses(user_id)
    if total_days <= 0:
        await query.edit_message_text("\u0423 \u0432\u0430\u0441 \u043d\u0435\u0442 \u0431\u043e\u043d\u0443\u0441\u043e\u0432.")
        return
    key = get_key_by_id(key_id)
    if not key:
        await query.edit_message_text("\u041a\u043b\u044e\u0447 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d.")
        return
    email, _, expiry_ms, client_id, active = key
    result = extend_key(email, client_id, active, expiry_ms, total_days)
    if result:
        update_key_expiry(key_id, result)
        reset_notified_level(key_id)
        text = f"\u2705 \u0411\u043e\u043d\u0443\u0441 {total_days} \u0434\u043d. \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d \u043a \u043a\u043b\u044e\u0447\u0443 {email}"
    else:
        text = "\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043f\u0440\u043e\u0434\u043b\u0435\u043d\u0438\u0438"
    keyboard = [[InlineKeyboardButton("\ud83d\udd19 \u041c\u0435\u043d\u044e", callback_data="referral")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

