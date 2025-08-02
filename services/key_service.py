import requests
import uuid
import random
import string
import json  
from datetime import datetime, timedelta
from db import add_key
from services import session
from config import API_URL, USERNAME, PASSWORD

SESSION_KEY = None

def login():
    resp = requests.post(
        f"{API_URL}/login",
        data={"username": USERNAME, "password": PASSWORD},
    )
    if resp.status_code == 200:
        cookie = resp.cookies.get("3x-ui")
        if cookie:
            session.SESSION_KEY = cookie
            print(f"✅ SESSION_KEY получен: {cookie}")
            return True
        else:
            print("❌ Не удалось получить SESSION_KEY")
            return False
    else:
        print(f"❌ Логин неудачен: {resp.status_code} {resp.text}")

def generate_random_string(length=6):
    return ''.join(random.choices(string.ascii_uppercase, k=length))

def generate_client(tg_id: str):
    in_email_id = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=6))
    return {
        "id": f"Pieno_{in_email_id}",
        "flow": "xtls-rprx-vision",
        "email": f"🇩🇪 Германия ({in_email_id})",
        "limitIp": 2,
        "totalGB": 0,
        "expiryTime": 0,
        "enable": True,
        "tgId": str(tg_id),
        "subId": ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=12)),
        "reset": 0
    }

def get_client_link(client_id, email):
    return f"vless://{client_id}@45.150.32.79:443?type=tcp&security=reality&pbk=_Al8Epi5BZ5Jj2HmPd5dLoiS_gim1viw0LNbE9DztXc&fp=chrome&sni=github.com&sid=ffffffffff&spx=%2F&flow=xtls-rprx-vision#{email}"

def generate_key(user_id, days, tg_id, inbound_id: int = 1):
    if not session.SESSION_KEY:
        return "❌ Нет активной сессии!"

    client = generate_client(tg_id)
    client_id = client['id']  

    expiry = int((datetime.utcnow() + timedelta(days=days)).timestamp() * 1000)
    expiry+= 2*60*60*1000
    client['expiryTime'] = expiry

    payload = {
        "id": inbound_id,
        "settings": json.dumps({"clients": [client]})
    }

    headers = {"Cookie": f"3x-ui={session.SESSION_KEY}"}
    resp = requests.post(f"{API_URL}/panel/api/inbounds/addClient", json=payload, headers=headers)

    if resp.status_code == 200 and resp.json().get("success"):
        link = get_client_link(client_id, client['email'])

        return {
            "email": client['email'],
            "link": link,
            "expiry_time": expiry,
            "client_id": client_id 
        }
    else:
        return f"❌ Ошибка API: {resp.text}"


def create_key_with_expiry(expiry_time_s: int, tg_id, inbound_id: int = 1):
    if not session.SESSION_KEY:
        return None

    client = generate_client(tg_id)
    client_id = client["id"]
    client["flow"] = "xtls-rprx-vision"
    client["limitIp"] = "2"
    client["expiryTime"] = int(expiry_time_s)

    payload = {"id": inbound_id, "settings": json.dumps({"clients": [client]})}

    headers = {"Cookie": f"3x-ui={session.SESSION_KEY}"}
    resp = requests.post(f"{API_URL}/panel/api/inbounds/addClient", json=payload, headers=headers)
    if resp.status_code == 200 and resp.json().get("success"):
        link = get_client_link(client_id, client["email"])
        return {
            "email": client["email"],
            "link": link,
            "client_id": client_id,
        }
    return None