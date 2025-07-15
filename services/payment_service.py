from yookassa import Configuration, Payment
from config import YOOKASSA_ACCOUNT_ID, YOOKASSA_SECRET_KEY

Configuration.account_id = YOOKASSA_ACCOUNT_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

pending_payments = {}

def create_payment(user_id, amount, user_email=None):
    try:
        if amount < 0:
            raise ValueError("Сумма не может быть отрицательной")

        payment_data = {
            "amount": {"value": str(amount), "currency": "RUB"},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": "https://t.me/pieno_bot"},
            "description": f"Пополнение баланса пользователя {user_id}",
            "metadata": {"order_id": str(user_id)},
            "receipt": {
                "customer": {
                    "email": user_email or f"{user_id}@telegram.com"
                },
                "items": [
                    {
                        "description": f"Пополнение баланса",
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
        pending_payments[payment.id] = {"user_id": user_id, "amount": amount}

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