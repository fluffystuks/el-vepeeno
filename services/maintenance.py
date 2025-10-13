import time
from typing import Dict, Set

from db import (
    delete_inactive_keys,
    get_keys_with_sni,
    update_key_expiry,
    update_key_link,
)

BONUS_DAY_SECONDS = 86400


def replace_sni_and_grant_bonus(target_sni: str, new_sni: str, bonus_days: int) -> Dict[str, object]:
    """Replace the SNI parameter in stored links and extend active keys."""

    keys = get_keys_with_sni(target_sni)
    notify_ids: Set[int] = set()

    metrics: Dict[str, object] = {
        "keys_found": len(keys),
        "links_updated": 0,
        "already_up_to_date": 0,
        "extended_keys": 0,
        "extension_api_failures": 0,
        "inactive_updated": 0,
        "invalid_tg_ids": 0,
    }

    bonus_seconds = bonus_days * BONUS_DAY_SECONDS

    for key in keys:
        link = key.get("key_link") or ""
        if not link or f"sni={target_sni}" not in link:
            metrics["already_up_to_date"] += 1
            continue

        new_link = link.replace(f"sni={target_sni}", f"sni={new_sni}")
        if new_link == link:
            metrics["already_up_to_date"] += 1
            continue

        update_key_link(key["id"], new_link)
        metrics["links_updated"] += 1

        is_active = bool(key.get("active"))
        if not is_active:
            metrics["inactive_updated"] += 1
            continue

        current_expiry = int(key.get("expiry_time") or 0)
        extend_success = False
        if key.get("client_id"):
            try:
                from services.extend_service import extend_key

                extend_result = extend_key(
                    email=key.get("email"),
                    client_id=key.get("client_id"),
                    active=key.get("active"),
                    current_expiry=current_expiry,
                    add_days=bonus_days,
                    inbound_id=key.get("inbound_id") or 1,
                )
            except Exception:
                extend_result = False

            if extend_result:
                update_key_expiry(key["id"], extend_result)
                extend_success = True

        if not extend_success:
            fallback_base = max(current_expiry, int(time.time()))
            update_key_expiry(key["id"], fallback_base + bonus_seconds)
            metrics["extension_api_failures"] += 1

        metrics["extended_keys"] += 1

        tg_id = key.get("tg_id")
        if tg_id is not None:
            try:
                notify_ids.add(int(tg_id))
            except (TypeError, ValueError):
                metrics["invalid_tg_ids"] += 1

    metrics["deleted_inactive"] = delete_inactive_keys()
    metrics["notify_ids"] = notify_ids

    return metrics
