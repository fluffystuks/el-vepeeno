import json
import os
import requests
import uuid
import random
import string
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext

# Файл для хранения данных
DATA_FILE = "users.json"

# API 3x-ui
API_URL = "http://109.120.184.34:57189"
USERNAME = os.getenv("API_USERNAME")
PASSWORD = os.getenv("API_PASSWORD")
SESSION_KEY = None

# Функция загрузки данных
def load_user_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
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

# Функция генерации ключа
# Функция генерации ключа
def generate_key(user_id):
    if not SESSION_KEY:
        return "❌ Ошибка авторизации в API."

    client = generate_client()
    client_id = client.get('id')

    expiry_datetime = datetime.utcnow() + timedelta(days=3, hours=3)
    expiry_time_str = expiry_datetime.strftime("%Y-%m-%d %H:%M")  # Сохраняем дату с временем в формате YYYY-MM-DD HH:MM
    client["expiryTime"] = expiry_time_str

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
            
            # Сохраняем email, срок действия и статус пробного периода в структуру данных пользователя
            if user_id not in user_data:
                user_data[user_id] = {}

            # Обновляем данные пользователя: добавляем пробный период и срок действия
            user_data[user_id]["email"] = client['email']
            user_data[user_id]["expiryTime"] = expiry_time_str
            user_data[user_id]["trial_used"] = True  # Отмечаем, что пробной период использован

            save_user_data(user_data)

            return f"🔑 Ключ успешно создан!\n📧 Email: {client['email']}\n🔗 Ссылка: {link}"
        else:
            return f"❌ Ошибка при генерации ключа: {response.text}"
    except Exception as e:
        return f"❌ Ошибка соединения с API: {e}"

# Функция обработки команды /start
async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("Подключить", callback_data='connect')],
        [InlineKeyboardButton("Инструкция по подключению", callback_data='instruction')],
        [InlineKeyboardButton("Мой аккаунт", callback_data='account')],
        [InlineKeyboardButton("Помощь", callback_data='help')],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Добро пожаловать! Выберите один из вариантов:', reply_markup=reply_markup)

# Функция обработки кнопки "Инструкция по подключению"
async def handle_instruction(update, context):
    await update.callback_query.answer()
    await update.callback_query.message.edit_text(
        "📜 **Инструкция по подключению для всех устройств:**\n"
        "👉 [Открыть инструкцию](https://telegra.ph/Instrukciya-po-ispolzovaniyu-klyucha-BLESS-01-30)",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([ 
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ])
    )

# Функция обработки выбора "Подключить"
async def handle_connect(update, context):
    user_id = str(update.callback_query.from_user.id)
    trial_disabled = user_data.get(user_id, {}).get("trial_used", False)

    keyboard = [
        [InlineKeyboardButton("Пробный - 3 дня", callback_data='trial')] if not trial_disabled else [],
        [InlineKeyboardButton("100 рублей - 1 месяц", callback_data='100rub')],
        [InlineKeyboardButton("500 рублей - 6 месяцев", callback_data='500rub')],
        [InlineKeyboardButton("Назад", callback_data='back')],
    ]
    
    keyboard = [row for row in keyboard if row]  # Убираем пустые строки
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.edit_text('Выберите тариф для подключения:', reply_markup=reply_markup)

# Функция обработки выбора тарифа
async def handle_tariff(update, context):
    query = update.callback_query
    user_id = str(query.from_user.id)
    choice = query.data

    if user_id not in user_data:
        user_data[user_id] = {}

    if choice == 'trial':
        # Проверяем, использовал ли пользователь пробный период
        if user_data[user_id].get("trial_used", False):
            await query.answer("Вы уже использовали пробный период!", show_alert=True)
            return
        
        # Отмечаем, что пробный период был использован
        user_data[user_id]["trial_used"] = True

        # Генерируем ключ для пользователя
        key_info = generate_key(user_id)

        # Сохраняем обновленные данные пользователя в users.json
        save_user_data(user_data)

        await query.edit_message_text(f"Вы выбрали тариф 'Пробный - 3 дня'.\n\n{key_info}")
    
    elif choice == '100rub':
        await query.edit_message_text('Вы выбрали тариф "100 рублей - 1 месяц".')
    
    elif choice == '500rub':
        await query.edit_message_text('Вы выбрали тариф "500 рублей - 6 месяцев".')
    
    elif choice == 'back':
        await query.answer()
        await start(query, context)

# Функция обработки кнопки "Помощь"
async def handle_help(update, context):
    await update.callback_query.answer()
    await update.callback_query.message.edit_text(
        "Если вам необходима помощь с пополнением или настройкой VPN, обратитесь сюда: [@othrwise](https://t.me/othrwise)",
        parse_mode="Markdown"
    )

# Функция обработки "Мой аккаунт"
async def handle_account(update, context):
    user_id = str(update.callback_query.from_user.id)

    # Проверяем, есть ли данные у пользователя
    if user_id not in user_data or "email" not in user_data[user_id]:
        await update.callback_query.answer("У вас еще нет активного аккаунта!", show_alert=True)
        return

    # Получаем email и дату окончания
    user_email = user_data[user_id]["email"]
    expiry_time = user_data[user_id].get("expiryTime", "Не указано")

    # Если дата в строковом формате, пытаемся конвертировать её в datetime
    if isinstance(expiry_time, str):
        try:
            # Пробуем распарсить дату в формате "YYYY-MM-DD HH:MM"
            expiry_datetime = datetime.strptime(expiry_time, "%Y-%m-%d %H:%M")
            expiry_time = expiry_datetime.strftime("%d-%m-%Y %H:%M")
        except ValueError:
            expiry_time = "Неверный формат даты"

    await update.callback_query.message.edit_text(
        f"Ваш аккаунт:\n\n"
        f"📧 Email: {user_email}\n"
        f"⏳ Срок действия: {expiry_time}"
    )



# Основная функция для запуска бота
def main():
    TOKEN = '7618148235:AAFGTnPyYnPf82EPGoYocndpXMl12yRYpVw'
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_connect, pattern='^connect$'))
    application.add_handler(CallbackQueryHandler(handle_tariff, pattern='^(trial|100rub|500rub|back)$'))
    application.add_handler(CallbackQueryHandler(handle_help, pattern='^help$'))  
    application.add_handler(CallbackQueryHandler(handle_instruction, pattern='^instruction$')) 
    application.add_handler(CallbackQueryHandler(handle_account, pattern='^account$'))  # Добавляем обработчик для "Мой аккаунт"

    login()  # Логинимся в API перед запуском
    application.run_polling()

if __name__ == '__main__':
    main()
