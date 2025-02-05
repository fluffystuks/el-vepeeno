import json
import os
import requests
import uuid
import random
import string
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, MenuButtonCommands, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, filters
from yookassa import Configuration, Payment

# Файл для хранения данных
DATA_FILE = "users.json"

# API 3x-ui
API_URL = "http://109.120.184.34:57189"
USERNAME = os.getenv("API_USERNAME")
PASSWORD = os.getenv("API_PASSWORD")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SESSION_KEY = None

Configuration.account_id = '1027685'
Configuration.secret_key = 'test_gSCcoBfzGAjni5SJA1vtH4RC9Y0nAVhpDakc6Itc1bY'


# Глобальный словарь для хранения ожидающих платежей
pending_payments = {}  # Формат: { payment_id: { "user_id": <id>, "amount": <сумма> } }

def create_payment(user_id, amount):
    payment = Payment.create({
        "amount": {"value": str(amount), "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": "https://твой-сайт.ру/success"},
        "description": f"Пополнение баланса пользователя {user_id} на {amount} RUB"
    })
    # Сохраняем информацию о платеже для последующей проверки
    pending_payments[payment.id] = {"user_id": str(user_id), "amount": amount}
    return payment.confirmation.confirmation_url, payment.id


# Функция загрузки данных
def load_user_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            # Добавляем поле balance, если его нет
            for user_id in data:
                if "balance" not in data[user_id]:
                    data[user_id]["balance"] = 0
            return data
    return {}

# Функция сохранения данных
def save_user_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

# Загружаем данные при запуске
user_data = load_user_data()

# Функция логина в API
def login():
    global SESSION_KEY
    try:
        response = requests.post(f"{API_URL}/login", data={"username": USERNAME, "password": PASSWORD})
        if response.status_code == 200 and response.json().get("success"):
            SESSION_KEY = response.cookies.get("3x-ui")
    except Exception as e:
        print(f"Ошибка при логине: {e}")

# Функция генерации случайного идентификатора
def generate_random_string(length=6):
    return ''.join(random.choices(string.ascii_uppercase, k=length))

# Функция создания клиента
def generate_client():
    return {
        "id": str(uuid.uuid4()),
        "flow": "",
        "email": f"Finland({generate_random_string(6)})",
        "limitIp": 0,
        "totalGB": 0,
        "expiryTime": 0,
        "enable": True,
        "tgId": "",
        "subId": generate_random_string(12),
        "reset": 0
    }

# Функция получения ссылки на ключ
def get_client_link(client_id, user_id: str):
    return f"vless://{client_id}@109.120.184.34:433?type=tcp&security=reality&pbk=eFC-ougLLf7VNPSagv1C1CHP8jBGvzVSGLmfww-9Cyg&fp=firefox&sni=www.ign.com&sid=14b4b5a9cbd5&spx=%2F#Buyers-{user_id}"

def generate_key(user_id, duration_days):
    if not SESSION_KEY:
        return "❌ Ошибка авторизации в API."

    client = generate_client()
    client_id = client.get('id')

    # Генерация срока действия без учета часового пояса
    utc_now = datetime.utcnow()
    expiry_datetime = utc_now + timedelta(days=duration_days, hours=3)
    
    expiry_timestamp = int(expiry_datetime.timestamp() * 1000)
    client["expiryTime"] = expiry_timestamp

    payload = {
        "id": 2,
        "settings": json.dumps({"clients": [client]})
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": f"3x-ui={SESSION_KEY}"
    }

    try:
        response = requests.post(f"{API_URL}/panel/api/inbounds/addClient", json=payload, headers=headers)
        if response.status_code == 200 and response.json().get("success"):
            link = get_client_link(client_id, client['email'])
            
            if user_id not in user_data:
                user_data[user_id] = {}

            user_data[user_id].update({
                "email": client['email'],
                "expiryTime": expiry_datetime.strftime("%d-%m-%Y %H:%M"),
                "trial_used": user_data[user_id].get("trial_used", False),
                "key": link
            })
            save_user_data(user_data)

            return f"📧 Email: {client['email']}\n🔑 Ключ: {link}"
        else:
            return f"❌ Ошибка при генерации ключа: {response.text}"
    except Exception as e:
        return f"❌ Ошибка соединения с API: {e}"


async def set_bot_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Запустить бота")
    ])

async def post_init(application: Application):
    await application.bot.set_my_commands([
        ("start", "Запустить бота"),
        ("pay", "Пополнить баланс"),
        ("balance", "Показать баланс")
    ])
    
    # Устанавливаем кнопку "Меню"
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def pay(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "⚠️ Автоматическая касса пока не настроена.\n"
        "Для оплаты, пожалуйста, свяжитесь с:[@othrwise](https://t.me/othrwise)",
        parse_mode="Markdown"
    )


async def process_amount(update: Update, context: CallbackContext):
    try:
        amount = float(update.message.text)
        if amount < 1:
            raise ValueError("Сумма должна быть больше 1 рубля.")
        
        user_id = update.message.from_user.id
        url, payment_id = create_payment(user_id, amount)
        
        # Можно сохранить payment_id для пользователя в user_data, если нужно отслеживать отдельно
        if str(user_id) not in user_data:
            user_data[str(user_id)] = {"balance": 0}
        user_data[str(user_id)]["last_payment_id"] = payment_id
        save_user_data(user_data)
        
        keyboard = [[InlineKeyboardButton("Оплатить", url=url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(f"Оплатите {amount} RUB по ссылке:", reply_markup=reply_markup)
        await update.message.reply_text("После оплаты введите команду /check_payment для проверки статуса платежа.")
    except ValueError:
        await update.message.reply_text("Некорректная сумма. Введите число больше 1.")

async def check_payment(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    # Проверяем, есть ли у пользователя ожидающий платёж
    user_payment_id = user_data.get(user_id, {}).get("last_payment_id")
    
    if not user_payment_id:
        await update.message.reply_text("Нет ожидающих платежей. Начните процесс оплаты командой /pay.")
        return

    # Получаем данные о платеже
    try:
        payment = Payment.find_one(user_payment_id)
    except Exception as e:
        await update.message.reply_text(f"Ошибка при проверке платежа: {e}")
        return

    if payment.status == "succeeded":
        # Пополняем баланс
        payment_info = pending_payments.get(user_payment_id)
        if payment_info:
            amount = payment_info["amount"]
            # Обновляем баланс пользователя в файле
            user_data[user_id]["balance"] = user_data[user_id].get("balance", 0) + amount
            save_user_data(user_data)
            # Удаляем запись об обработанном платеже
            del pending_payments[user_payment_id]
            # Можно удалить last_payment_id, чтобы избежать повторной проверки
            del user_data[user_id]["last_payment_id"]
            save_user_data(user_data)
            await update.message.reply_text(f"Платёж успешно подтверждён! Ваш баланс пополнен на {amount} RUB.")
        else:
            await update.message.reply_text("Платёж не найден в ожидающих. Возможно, он уже обработан.")
    else:
        await update.message.reply_text("Платёж ещё не подтверждён. Попробуйте позже.")


async def balance(update, context):
    user_id = str(update.message.from_user.id)
    
    if user_id not in user_data:
        user_data[user_id] = {"balance": 0}
        save_user_data(user_data)
    
    balance_amount = user_data[user_id].get("balance", 0)
    
    text = (
        "💰 *Ваш баланс:*\n"
        f"{balance_amount} рублей\n\n"
        "Чтобы пополнить баланс, используйте команду /pay."
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("🔗 Подключить", callback_data='connect')],
        [InlineKeyboardButton("📜 Инструкция по подключению", callback_data='instruction')],
        [InlineKeyboardButton("👤 Мой аккаунт", callback_data='account')],
        [InlineKeyboardButton("🤓Помощь", callback_data='help')],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🌟 *Добро пожаловать!* 🌟\n\n"
        "Выберите один из вариантов ниже:\n"
    )
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_instruction(update, context):
    await update.callback_query.answer()
    text = (
        "📜 *Инструкция по подключению для всех устройств:*\n\n"
        "👉 [Подробная инструкция](https://telegra.ph/Instrukciya-po-ispolzovaniyu-klyucha-BLESS-01-30)"
    )
    
    await update.callback_query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([ 
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ])
    )

async def handle_connect(update, context):
    user_id = str(update.callback_query.from_user.id)
    trial_disabled = user_data.get(user_id, {}).get("trial_used", False)

    keyboard = [
        [InlineKeyboardButton("🆓 Пробный - 3 дня", callback_data='trial')] if not trial_disabled else [],
        [InlineKeyboardButton("💳 100 рублей - 1 месяц", callback_data='100rub')],
        [InlineKeyboardButton("💳 250 рублей - 3 месяца", callback_data='250rub')],
        [InlineKeyboardButton("💳 500 рублей - 6 месяцев", callback_data='500rub')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back')],
    ]
    
    keyboard = [row for row in keyboard if row]  # Убираем пустые строки
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "💡 *Выберите тариф для подключения:*"

    )
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_tariff(update, context):
    query = update.callback_query
    user_id = str(query.from_user.id)
    choice = query.data

    if user_id not in user_data:
        user_data[user_id] = {"balance": 0}
        save_user_data(user_data)

    if choice == 'trial':
        if user_data[user_id].get("trial_used", False):
            await query.answer("Вы уже использовали пробный период!", show_alert=True)
            return
        
        user_data[user_id]["trial_used"] = True
        save_user_data(user_data)

        # Для пробного периода срок действия - 3 дня
        key_info = generate_key(user_id, duration_days=3)  # Передаем 3 дня для пробного периода
        key = user_data[user_id].get("key", "Не найдено")

        text = (
            "🎉 *Поздравляем! Вы успешно активировали пробный период.* 🎉\n\n"
            f" *Ваш ключ:*\n`{key}`\n\n"
            "\n*Нажмите на ключ, чтобы его скопировать*\n\n"
            "📝 *Что делать дальше?*\n"
            "1. Скачайте приложение Streisand - если у Вас IOS. Hiddify,V2RayNG - Если у Вас Android.\n"
            "2. Нажмите кнопку *Добавить ключ*.\n"
            "3. Вставьте ваш ключ и нажмите *Подключить*.\n"
            "4. Готово! Теперь вы защищены. 🛡️\n\n"
            "⏳ *Срок действия пробного периода:* 3 дня\n\n"
            "📜 Если возникнут вопросы, воспользуйтесь разделом *Помощь*."
        )

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📜 Инструкция по подключению", callback_data='instruction')],
                [InlineKeyboardButton("🤓 Помощь", callback_data='help')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back')]
            ])
        )
    
    elif choice == '100rub':
        if user_data[user_id].get("balance", 0) < 100:
            await query.answer("❌ Недостаточно средств на балансе. Пополните баланс через /pay.", show_alert=True)
            return
        
        user_data[user_id]["balance"] -= 100
        save_user_data(user_data)

        # Для тарифа на 1 месяц срок действия - 30 дней
        key_info = generate_key(user_id, duration_days=30)  # Передаем 30 дней для тарифа на 1 месяц
        key = user_data[user_id].get("key", "Не найдено")
        
        text = (
            "🎉 *Вы успешно активировали тариф на 1 месяц!* 🎉\n\n"
            f"🔑 *Ваш ключ:*\n`{key}`\n\n"
            "\n*Нажмите на ключ, чтобы его скопировать*\n\n"
            "📝 *Что делать дальше?*\n"
            "1. Скачайте приложение Streisand - если у Вас IOS. Hiddify,V2RayNG - Если у Вас Android .\n"
            "2. Нажмите кнопку *Добавить ключ*.\n"
            "3. Вставьте ваш ключ и нажмите *Подключить*.\n"
            "4. Готово! Теперь вы защищены. 🛡️\n\n"
            "⏳ *Срок действия тарифа:* 1 месяц\n\n"
            "📜 Если возникнут вопросы, воспользуйтесь разделом *Помощь*."
        )
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📜 Инструкция по подключению", callback_data='instruction')],
                [InlineKeyboardButton("🤓 Помощь", callback_data='help')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back')]
            ])
        )

    elif choice == '250rub':
        if user_data[user_id].get("balance", 0) < 250:
            await query.answer("❌ Недостаточно средств на балансе. Пополните баланс через /pay.", show_alert=True)
            return
        
        user_data[user_id]["balance"] -= 250
        save_user_data(user_data)

   
        key_info = generate_key(user_id, duration_days=90) 
        key = user_data[user_id].get("key", "Не найдено")

        text = (
            "🎉 *Вы успешно активировали тариф на 3 месяца!* 🎉\n\n"
            f"🔑 *Ваш ключ:*\n`{key}`\`n\n"
            "\n*Нажмите на ключ, чтобы его скопировать*\n\n"
            "📝 *Что делать дальше?*\n"
            "1. Скачайте приложение Streisand - если у Вас IOS. Hiddify,V2RayNG - Если у Вас Android .\n"
            "2. Нажмите кнопку *Добавить ключ*.\n"
            "3. Вставьте ваш ключ и нажмите *Подключить*.\n"
            "4. Готово! Теперь вы защищены. 🛡️\n\n"
            "⏳ *Срок действия тарифа:* 3 месяца\n\n"
            "📜 Если возникнут вопросы, воспользуйтесь разделом *Помощь*."
        )
        
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📜 Инструкция по подключению", callback_data='instruction')],
                [InlineKeyboardButton("🤓 Помощь", callback_data='help')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back')]
            ])
        )

    elif choice == '500rub':
        if user_data[user_id].get("balance", 0) < 500:
            await query.answer("❌ Недостаточно средств на балансе. Пополните баланс через /pay.", show_alert=True)
            return
        
        user_data[user_id]["balance"] -= 500
        save_user_data(user_data)

        # Для тарифа на 6 месяцев срок действия - 180 дней
        key_info = generate_key(user_id, duration_days=180)  # Передаем 180 дней для тарифа на 6 месяцев
        key = user_data[user_id].get("key", "Не найдено")

        text = (
            "🎉 *Вы успешно активировали тариф на 6 месяцев!* 🎉\n\n"
            f"🔑 *Ваш ключ:*\n`{key}`\n\n"
            "\n*Нажмите на ключ, чтобы его скопировать*\n\n"
            "📝 *Что делать дальше?*\n"
            "1. Скачайте приложение Streisand - если у Вас IOS. Hiddify,V2RayNG - Если у Вас Android .\n"
            "2. Нажмите кнопку *Добавить ключ*.\n"
            "3. Вставьте ваш ключ и нажмите *Подключить*.\n"
            "4. Готово! Теперь вы защищены. 🛡️\n\n"
            "⏳ *Срок действия тарифа:* 6 месяцев\n\n"
            "📜 Если возникнут вопросы, воспользуйтесь разделом *Помощь*."
        )
        
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📜 Инструкция по подключению", callback_data='instruction')],
                [InlineKeyboardButton("🤓 Помощь", callback_data='help')],
                [InlineKeyboardButton("🔙 Назад", callback_data='back')]
            ])
        )
    
    elif choice == 'back':
        await query.answer()
        await start(update, context)

async def handle_help(update, context):
    await update.callback_query.answer()
    text = (
        " *Помощь*\n\n"
        "Если вам нужна помощь с пополнением или настройкой VPN, обратитесь к нашему специалисту:\n"
        "[@othrwise](https://t.me/othrwise)\n\n"
        "_Мы всегда рады помочь!_ 😊"
    )
    
    await update.callback_query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ])
    )

async def handle_account(update, context):
    user_id = str(update.callback_query.from_user.id)

    if user_id not in user_data or "email" not in user_data[user_id]:
        await update.callback_query.answer("У вас еще нет активного аккаунта!", show_alert=True)
        return

    user_email = user_data[user_id]["email"]
    expiry_time = user_data[user_id].get("expiryTime", "Не указано")
    key_link = user_data[user_id].get("key", "Не найдено")
    user_balance = user_data[user_id].get("balance", 0)

    text = (
        "👤 *Ваш аккаунт*\n\n"
        f"📧 *Email:* `{user_email}`\n"
        f"⏳ *Срок действия:* `{expiry_time}`\n"
        f"🔑 *Ваш ключ:*\n `{key_link}` \n\n"
        "*Нажмите на ключ, чтобы его скопировать*\n"
        f"💰 *Баланс:* `{user_balance} рублей`\n\n"
        "_Скопируйте ключ и используйте его в приложении._\n"
        "Если возникнут вопросы, воспользуйтесь разделом *Помощь*."
    )
    
    await update.callback_query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤓 Помощь", callback_data='help')],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ])
    )

def main():

    application = Application.builder().token('7618148235:AAFGTnPyYnPf82EPGoYocndpXMl12yRYpVw').post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pay", pay))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("check_payment", check_payment))
    application.add_handler(CallbackQueryHandler(handle_connect, pattern='^connect$'))
    application.add_handler(CallbackQueryHandler(handle_tariff, pattern='^(trial|100rub|250rub|500rub|back)$'))
    application.add_handler(CallbackQueryHandler(handle_help, pattern='^help$'))
    application.add_handler(CallbackQueryHandler(handle_instruction, pattern='^instruction$'))
    application.add_handler(CallbackQueryHandler(handle_account, pattern='^account$'))
    
    # Добавляем обработчик для текстовых сообщений (без команд)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_amount))

    login()

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()