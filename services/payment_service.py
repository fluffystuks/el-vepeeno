from yookassa import Configuration, Payment
from uuid import uuid4
from config import YOOKASSA_ACCOUNT_ID, YOOKASSA_SECRET_KEY
from db import get_or_create_user, update_payment_status

Configuration.configure(YOOKASSA_ACCOUNT_ID, YOOKASSA_SECRET_KEY)

pending_payments = {}

def create_payment(tg_id, amount, user_email=None):
    try:
        if amount < 0:
            raise ValueError("Сумма не может быть отрицательной")

        user_id, _ = get_or_create_user(str(tg_id))

        payment_data = {
            "amount": {"value": str(amount), "currency": "RUB"},
            "capture": False,
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

        payment = Payment.create(payment_data, idempotency_key=uuid4())
        pending_payments[payment.id] = {"user_id": user_id, "tg_id": tg_id, "amount": amount}

        return payment.confirmation.confirmation_url, payment.id

    except Exception as e:
        print(f"Ошибка при создании платежа: {e}")
        return None, None

def check_payment(payment_id):
    try:
        payment = Payment.find_one(payment_id)
        return payment.status
    except Exception as e:
        print(f"Ошибка при проверке платежа: {e}")
        return None


def cancel_payment(payment_id):
    """Cancel a pending payment via the YooKassa API."""
    try:
        result = Payment.cancel(payment_id, idempotency_key=uuid4())
        if getattr(result, "status", None) == "canceled":
            update_payment_status(payment_id, "canceled")
            pending_payments.pop(payment_id, None)
            return True
        print(f"Не удалось отменить платёж {payment_id}: статус {getattr(result, 'status', 'unknown')}")
        return False
    except Exception as e:
        print(f"Ошибка при отмене платежа: {e}")
        return False
