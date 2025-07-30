import time
from db import get_active_keys_by_inbound, add_key, update_key_expiry
from services.key_service import login, create_key_with_expiry, update_client_expiry

GRACE_DAYS = 3


def migrate():
    if not login():
        print("Login failed")
        return

    keys = get_active_keys_by_inbound(2)
    for key_id, user_id, email, expiry, client_id in keys:
        result = create_key_with_expiry(expiry, inbound_id=1)
        if not result:
            print(f"Failed to create new key for {key_id}")
            continue

        add_key(user_id, result["email"], result["link"], expiry, result["client_id"], 1)

        new_expiry = int(time.time()) + GRACE_DAYS * 86400
        update_key_expiry(key_id, new_expiry)
        update_client_expiry(client_id, email, new_expiry, inbound_id=2)
        print(f"Migrated key {key_id} -> {result['client_id']}")


if __name__ == "__main__":
    migrate()
