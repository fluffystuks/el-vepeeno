import os
import requests
import asyncio
import json
import uuid
import random
import string
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
API_URL = "http://109.120.184.34:57189"
USERNAME = os.getenv("API_USERNAME")
PASSWORD = os.getenv("API_PASSWORD")
SESSION_KEY = None
ALLOWED_USERS = set(map(int, os.getenv("ALLOWED_USERS", "").split(',')))

bot = Bot(token=TOKEN)
dp = Dispatcher()

def generate_random_string(length=6):
    return ''.join(random.choices(string.ascii_uppercase, k=length))

def generate_client():
    return {
        "id": str(uuid.uuid4()),  # Генерируем случайный UUID
        "flow": "",
        "email": f"Finland({generate_random_string(6)})",  # Генерируем email
        "limitIp": 0,
        "totalGB": 0,
        "expiryTime": 0,
        "enable": True,
        "tgId": "",
        "subId": generate_random_string(12),  # Генерируем случайный subId
        "reset": 0
    }

async def login():
    global SESSION_KEY
    try:
        response = requests.post(f"{API_URL}/login", data={"username": USERNAME, "password": PASSWORD})
        if response.status_code == 200 and response.json().get("success"):
            SESSION_KEY = response.cookies.get("3x-ui")
            if SESSION_KEY:
                print("✅ Сессионный ключ успешно получен!")
            else:
                print("⚠️ Сессионный ключ отсутствует в cookies.")
        else:
            print(f"Ошибка авторизации: {response.json()}")
    except Exception as e:
        print(f"Ошибка при логине: {e}")

def get_client_link(client_id,user_id: str):
    return f"vless://{client_id}@109.120.184.34:433?type=tcp&security=reality&pbk=eFC-ougLLf7VNPSagv1C1CHP8jBGvzVSGLmfww-9Cyg&fp=firefox&sni=www.ign.com&sid=14b4b5a9cbd5&spx=%2F#Buyers-{user_id}"

@dp.message(Command("generate"))

async def generate_key(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    if not SESSION_KEY:
        await message.answer("❌ Ошибка авторизации в API. Попробуйте снова.")
        return

    # Создаём нового клиента
    client = generate_client()
    client_id = client.get('id')
    
    # Устанавливаем время истечения ключа (через 3 дня)
    expiry_datetime = datetime.utcnow() + timedelta(days=3, hours=3)  # UTC +3 часа
    expiry_timestamp = int(expiry_datetime.timestamp() * 1000)  # Преобразуем в миллисекунды
    client["expiryTime"] = expiry_timestamp  # Добавляем в клиента

    expiry_str = expiry_datetime.strftime("%d-%m-%Y %H:%M")  # Форматируем время для вывода

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
        response = requests.post(
            f"{API_URL}/panel/api/inbounds/addClient",
            json=payload,
            headers=headers
        )
        if response.status_code == 200 and response.json().get("success"):
            user_id = client['email']
            link = get_client_link(client_id, user_id)  # Получаем ссылку ключа
            if link:
                await message.answer(
                    f"🔑 Ключ успешно создан!\n\n"
                    f"📧 Email: {user_id}\n"
                    f"⏳ Действителен до: {expiry_str}\n\n"
                    f"🔗 Ссылка: {link}"
                )
            else:
                await message.answer("❌ Не удалось получить ссылку для ключа.")
        else:
            await message.answer(f"❌ Ошибка при генерации ключа. Ответ API: {response.text}")
    except Exception as e:
        await message.answer("❌ Ошибка соединения с API")
        print(f"Ошибка: {e}")

async def main():
    await login()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
