import requests, json
from datetime import datetime
import services.key_service
from services.key_service import SESSION_KEY  
from services import session
from config import API_URL


INBOUND_ID = 2 
API_URL = API_URL
def extend_key(email, client_id, active, current_expiry_ms, add_days):
    if not session.SESSION_KEY:
        print("❌ SESSION_KEY пустой!")
        return False

    now_ms = int(datetime.utcnow().timestamp() * 1000)

    now_ms = int(datetime.utcnow().timestamp() * 1000)

    if current_expiry_ms > now_ms:
        base_time = current_expiry_ms
    else:
        base_time = now_ms

    new_expiry = base_time + add_days * 24 * 60 * 60 * 1000

    client_payload = {
        "id": client_id,
        "flow": "",
        "email": email,
        "limitIp": 0,
        "totalGB": 0,
        "expiryTime": new_expiry,
        "enable": True,
        "tgId": "",
        "subId": "",
        "reset": 0
    }

    payload = {
        "id": INBOUND_ID,
        "settings": json.dumps({"clients": [client_payload]})
    }

    url = f"{API_URL}/panel/api/inbounds/updateClient/{client_id}"


    resp = requests.post(
        url,
        json=payload,
        headers={"Cookie": f"3x-ui={session.SESSION_KEY}"}
    )

    if resp.status_code == 200:
        try:
            data = resp.json()
        except ValueError:
            print(f"❌ Ответ не JSON: {resp.text!r}")
            return False
        if data.get("success"):
            return new_expiry  
        else:
            print(f"❌ API success=false: {data}")
            return False
    else:
        print(f"❌ Код {resp.status_code}, ответ: {resp.text}")
        return False