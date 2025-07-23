from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import (
    get_or_create_user,
    assign_referrer,
    create_bonus,
    get_user_referrer,
    increment_paid_referrals,
    count_successful_payments,
    get_bonus_balance,
    use_all_bonuses,
    get_all_keys,
    get_key_by_id,
    update_key_expiry,
    reset_notified_level,
    get_key_owner,
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



async def list_bonuses(update: Update, context: CallbackContext):
    tg_id = str(update.effective_user.id)
    user_id, _ = get_or_create_user(tg_id)
    balance = get_bonus_balance(user_id)
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="referral")]]
    if balance:
        keyboard.insert(0, [InlineKeyboardButton("➕ Использовать", callback_data="use_bonus")])
        text = f"Ваш бонус-баланс: {balance} дн."
    else:
        text = "У вас нет бонусных дней."

    markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        await update.callback_query.answer()
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")


async def choose_bonus_key(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    tg_id = str(query.from_user.id)
    user_id, _ = get_or_create_user(tg_id)
    balance = get_bonus_balance(user_id)
    if balance <= 0:
        await query.edit_message_text("Бонусов нет.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="show_bonuses")]]))
        return
    keys = get_all_keys(user_id)
    if not keys:
        await query.edit_message_text("У вас нет ключей.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="show_bonuses")]]))
        return
    keyboard = []
    for key_id, email, *_ in keys:
        keyboard.append([InlineKeyboardButton(email, callback_data=f"apply_bonus_{key_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="show_bonuses")])
    await query.edit_message_text("Выберите ключ, к которому добавить бонусы:", reply_markup=InlineKeyboardMarkup(keyboard))


async def apply_bonus_button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    key_id = int(query.data.split("_")[2])
    tg_id = str(query.from_user.id)
    user_id, _ = get_or_create_user(tg_id)
    days = use_all_bonuses(user_id)
    if days <= 0:
        await query.edit_message_text("Бонусов нет.")
        return
    owner = get_key_owner(key_id)
    if owner != user_id:
        await query.edit_message_text("Ключ не найден.")
        return
    key = get_key_by_id(key_id)
    if not key:
        await query.edit_message_text("Ключ не найден.")
        return
    email, _, expiry_ms, client_id, active = key
    result = extend_key(email, client_id, active, expiry_ms, days)
    if result:
        update_key_expiry(key_id, result)
        reset_notified_level(key_id)
        await query.edit_message_text(f"✅ Бонусы на {days} дн. применены!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back")]]))
    else:
        await query.edit_message_text("❌ Ошибка при продлении.")


async def referral_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    tg_id = str(query.from_user.id)
    link = generate_referral_link(context.bot.username, tg_id)

    keyboard = [
        [InlineKeyboardButton("🎁 Мои бонусы", callback_data="show_bonuses")],
        [InlineKeyboardButton("🔙 В меню", callback_data="back")],
    ]

    text = (
        "🤝 *Реферальная программа*\n\n"
        "Приглашайте друзей и получайте бонусы за регистрацию и оплату.\n\n"
        f"🔗 *Ваша ссылка:*\n`{link}`"
    )

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def show_bonuses(update: Update, context: CallbackContext):
    await list_bonuses(update, context)

