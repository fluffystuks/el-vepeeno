from telegram import Update
from telegram.ext import CallbackContext
from db import (
    get_or_create_user,
    assign_referrer,
    create_bonus,
    get_user_referrer,
    increment_paid_referrals,
    count_successful_payments,
    get_user_active_bonuses,
    mark_bonus_used,
    get_bonus,
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


def format_bonus(bonus):
    from datetime import datetime
    expiry = datetime.fromtimestamp(bonus[3]).strftime('%d.%m.%Y')
    return f"ID {bonus[0]} — +{bonus[1]} дн. до {expiry} ({bonus[2]})"


async def list_bonuses(update: Update, context: CallbackContext):
    tg_id = str(update.effective_user.id)
    user_id, _ = get_or_create_user(tg_id)
    bonuses = get_user_active_bonuses(user_id)
    if not bonuses:
        await update.message.reply_text("У вас нет активных бонусов.")
        return
    text = "Ваши бонусы:\n" + "\n".join(format_bonus(b) for b in bonuses)
    text += "\nИспользуйте /apply_bonus <bonus_id> <key_id>"
    await update.message.reply_text(text)


async def apply_bonus(update: Update, context: CallbackContext):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Использование: /apply_bonus <bonus_id> <key_id>")
        return
    try:
        bonus_id = int(args[0])
        key_id = int(args[1])
    except ValueError:
        await update.message.reply_text("ID должны быть числами")
        return
    tg_id = str(update.effective_user.id)
    user_id, _ = get_or_create_user(tg_id)
    bonus = get_bonus(bonus_id)
    from datetime import datetime
    now = int(datetime.now().timestamp())
    if not bonus or bonus[1] != user_id or bonus[5] != 'active' or bonus[4] <= now:
        await update.message.reply_text("Бонус не найден или недоступен")
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
    result = extend_key(email, client_id, active, expiry_ms, bonus[2])
    if result:
        update_key_expiry(key_id, result)
        reset_notified_level(key_id)
        mark_bonus_used(bonus_id)
        await update.message.reply_text(f"✅ Бонус применён, ключ продлён на {bonus[2]} дней")
    else:
        await update.message.reply_text("❌ Ошибка при продлении")

