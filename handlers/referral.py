from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from datetime import datetime
import time
from db import (
    get_or_create_user,
    assign_referrer,
    create_bonus,
    get_user_referrer,
    increment_paid_referrals,
    get_bonus_balance,
    get_user_active_bonuses,
    get_user_bonuses,
    use_all_bonuses,
    get_all_keys,
    get_key_by_id,
    update_key_expiry,
    reset_notified_level,
    get_key_owner,
    has_bonus,
    get_user_tg,
)
from services.extend_service import extend_key

SIGNUP_REFERRER_BONUS = 3
SIGNUP_USER_BONUS = 3
PURCHASE_REFERRER_PERCENT = 0.2
MILESTONE_BONUSES = {3: 10, 5: 15}

REASON_TEXTS = {
    "signup_owner": "🎉 за приглашение друга",
    "signup_user": "🎁 за регистрацию по ссылке",
    "purchase_referrer": "💸 за покупку вашим рефералом",
    "milestone_3": "🏅 за 3 платящих реферала",
    "milestone_5": "🥇 за 5 платящих рефералов",
}

BONUS_MESSAGES = {
    "signup_owner": "🥳 Ваш друг зарегистрировался по вашей ссылке!\nВам начислено +{days} дн.",
    "signup_user": "🎁 Спасибо за регистрацию по ссылке!\nВы получили +{days} дн.",
    "purchase_referrer": "💸 Ваш реферал совершил покупку.\nНачислено +{days} дн.",
    "milestone_3": "🏅 У вас уже 3 платящих друга!\nПолучаете +{days} дн.",
    "milestone_5": "🥇 Фантастика! 5 друзей оплатили.\n+{days} дн. в подарок!",
}

async def notify_bonus(context: CallbackContext, tg_id: str, days: int, reason: str):
    msg = BONUS_MESSAGES.get(reason)
    if not msg or days <= 0:
        return
    try:
        await context.bot.send_message(chat_id=tg_id, text=msg.format(days=days))
    except Exception:
        pass


def generate_referral_link(bot_username: str, tg_id: str) -> str:
    return f"https://t.me/{bot_username}?start={tg_id}"


async def process_signup(update: Update, context: CallbackContext, ref_tg_id: str, user_id: int):
    ref_user_id, _ = get_or_create_user(ref_tg_id)
    if assign_referrer(user_id, ref_user_id):
        create_bonus(ref_user_id, SIGNUP_REFERRER_BONUS, "signup_owner")
        create_bonus(user_id, SIGNUP_USER_BONUS, "signup_user")
        await notify_bonus(context, ref_tg_id, SIGNUP_REFERRER_BONUS, "signup_owner")
        await notify_bonus(context, str(update.effective_user.id), SIGNUP_USER_BONUS, "signup_user")


async def process_purchase(context: CallbackContext, user_id: int, days: int, price: int):
    referrer_id = get_user_referrer(user_id)

    if referrer_id:
        ref_days = max(1, int(days * PURCHASE_REFERRER_PERCENT))
        create_bonus(referrer_id, ref_days, "purchase_referrer")
        tg_id = get_user_tg(referrer_id)
        if tg_id:
            await notify_bonus(context, tg_id, ref_days, "purchase_referrer")

        if not has_bonus(user_id, "first_paid"):
            create_bonus(user_id, 0, "first_paid")
            count = increment_paid_referrals(referrer_id)
            bonus_days = MILESTONE_BONUSES.get(count)
            if bonus_days:
                create_bonus(referrer_id, bonus_days, f"milestone_{count}")
                if tg_id:
                    await notify_bonus(context, tg_id, bonus_days, f"milestone_{count}")

async def list_bonuses(update: Update, context: CallbackContext):
    tg_id = str(update.effective_user.id)
    user_id, _ = get_or_create_user(tg_id)
    balance = get_bonus_balance(user_id)
    bonuses = get_user_active_bonuses(user_id)
    lines = []
    for _, days, reason, expiry in bonuses:
        if days <= 0:
            continue
        reason_text = REASON_TEXTS.get(reason, reason.replace('_', '\\_'))
        exp = datetime.fromtimestamp(expiry).strftime("%d.%m")
        lines.append(f"+{days} дн. — {reason_text} (до {exp})")

    history = "\n".join(lines) if lines else "Нет активных бонусов."

    text = (
        "🎁 *Ваши активные бонусы:*\n\n"
        f"{history}\n\n"
        f"💰 *Бонусный баланс:* *{balance} дн.*\n\n"
        "🔧 Используйте бонусы, чтобы продлить ключ доступа к VPN."
    )

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="referral")]]
    if balance:
        keyboard.insert(0, [InlineKeyboardButton("➕ Использовать", callback_data="use_bonus")])

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
    for key_id, email, expiry, active in keys:
        days_left = max(0, (expiry - int(time.time())) // 86400)
        status = "✅ Активен" if active else "❌ Не активен"
        text = f"{email} — {days_left} дн. {status}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"apply_bonus_{key_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="show_bonuses")])
    await query.edit_message_text(
        "Выберите ключ, к которому применить бонусы:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


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
    email, _, expiry, client_id, active, inbound_id = key
    if inbound_id == 1:
        await query.edit_message_text("Старый ключ нельзя продлить, перенесите его на новый.")
        return
    result = extend_key(email, client_id, active, expiry, days, inbound_id=2)
    if result:
        update_key_expiry(key_id, result)
        reset_notified_level(key_id)
        await query.edit_message_text(
            f"✅ Бонусы (+{days} дн.) успешно применены!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back")]]),
        )
    else:
        await query.edit_message_text("❌ Ошибка при продлении.")


async def referral_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    tg_id = str(query.from_user.id)
    link = generate_referral_link(context.bot.username, tg_id)

    keyboard = [
        [InlineKeyboardButton("🎁 Мои бонусы", callback_data="show_bonuses")],
        [InlineKeyboardButton("📲 Поделиться", url=f"https://t.me/share/url?url={link}")],
        [InlineKeyboardButton("🔙 В меню", callback_data="back")],
    ]

    text = (
        "🏆 *Реферальная программа*\n\n"
        "Зови друзей — и получи классные бонусы:\n\n"
        "• 🎉 +3 дня — за регистрацию друга\n"
        "• 💸 +20% бонуса от его каждой покупки (например, покупка на 30\u202fдн → ты получаешь 6\u202fдн, на 90\u202f → 18\u202fдн)\n"
        "• 🏅 +10 дней — за 3 платящих друга\n"
        "• 🥇 +15 дней — за 5 платящих\n\n"
        f"🔗 *Ваша ссылка:* `{link}`\n\n"
        "👉 Нажми \u00abПоделиться\u00bb, чтобы отправить ссылку друзьям и начать собирать бонусы!"
    )

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def show_bonuses(update: Update, context: CallbackContext):
    await list_bonuses(update, context)

