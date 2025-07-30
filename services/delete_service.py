import requests
from services import session
from config import API_URL

INBOUND_ID = 2


def delete_client(client_id: str, inbound_id: int = INBOUND_ID) -> bool:
    if not session.SESSION_KEY:
        print("❌ SESSION_KEY пустой!")
        return False

    url = f"{API_URL}/panel/api/inbounds/{inbound_id}/delClient/{client_id}"
    resp = requests.post(url, headers={"Cookie": f"3x-ui={session.SESSION_KEY}"})

    if resp.status_code == 200:
        try:
            data = resp.json()
        except ValueError:
            print(f"❌ Ответ не JSON: {resp.text!r}")
            return False
        if data.get("success"):
            return True
        else:
            print(f"❌ API success=false: {data}")
            return False
    else:
        print(f"❌ Код {resp.status_code}, ответ: {resp.text}")
        return False
