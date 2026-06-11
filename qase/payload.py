from core.utils import is_valid
from qase.payload import PRIORITY_MAP  # если у тебя в этом же файле — не импортируй


def build_payload(kiwi, qase, mode, kiwi_url):

    wipe = (mode == "3")

    payload = {
        "steps": kiwi["steps"] if not wipe else [],
        "description": "" if wipe else build_description(kiwi, kiwi_url)
    }

    if mode == "1":
        payload["title"] = kiwi["title"]
    else:
        payload["title"] = qase.get("title") or kiwi["title"]

    if mode != "3":
        payload["preconditions"] = kiwi.get("preconditions", "")

    # =========================
    # FIX: PRIORITY MAPPING
    # =========================
    priority_raw = kiwi.get("priority")

    if isinstance(priority_raw, str):
        priority = PRIORITY_MAP.get(priority_raw.strip().lower())
    else:
        priority = priority_raw

    payload["priority"] = priority

    return payload