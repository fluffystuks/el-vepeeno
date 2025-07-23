from yookassa import Configuration, Payment
from config import (
    YOOKASSA_ACCOUNT_ID,
    YOOKASSA_SECRET_KEY,
    ADMIN_TG_ID,
    TELEGRAM_TOKEN,
)
from telegram import Bot
from db import get_or_create_user

Configuration.account_id = YOOKASSA_ACCOUNT_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

pending_payments = {}

def create_payment(tg_id, amount, user_email=None):
    try:
        if amount < 0:
            raise ValueError("Сумма не может быть отрицательной")

        user_id, _ = get_or_create_user(str(tg_id))

        payment_data = {
            "amount": {"value": str(amount), "currency": "RUB"},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": "https://t.me/pieno_bot"},
            "description": f"Пополнение баланса пользователя {tg_id}",
            "metadata": {"order_id": str(tg_id)},
            "receipt": {
                "customer": {
                    "email": user_email or f"{tg_id}@telegram.com"
                },
                "items": [
                    {
                        "description": "Пополнение баланса",
                        "quantity": 1,
                        "amount": {
                            "value": str(amount),
                            "currency": "RUB"
                        },
                        "vat_code": 1
                    }
                ]
            }
        }

        payment = Payment.create(payment_data)
        pending_payments[payment.id] = {"user_id": user_id, "tg_id": tg_id, "amount": amount}

        return payment.confirmation.confirmation_url, payment.id

    except Exception as e:
        error_msg = f"Ошибка при создании платежа: {e}"
        print(error_msg)
        if ADMIN_TG_ID:
            try:
                Bot(token=TELEGRAM_TOKEN).send_message(chat_id=ADMIN_TG_ID, text=error_msg)
            except Exception:
                pass
        return None, None

def check_payment(payment_id):
    try:
        payment = Payment.find_one(payment_id)
        return payment.status
    except Exception as e:
        error_msg = f"Ошибка при проверке платежа: {e}"
        print(error_msg)
        if ADMIN_TG_ID:
            try:
                Bot(token=TELEGRAM_TOKEN).send_message(chat_id=ADMIN_TG_ID, text=error_msg)
            except Exception:
                pass
        return None
