# PRODUCTION-STABLE
# No circular imports
# Safe payload generation
# API-compatible priority mapping
# validation-resilient builder layer

from core.utils import is_valid


# =========================
# PRIORITY MAPPING
# =========================
PRIORITY_MAP = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
    "minor": 0,
    "normal": 1,
    "major": 2,
    "blocker": 3
}


def build_description(kiwi, kiwi_url):

    parts = [f"Kiwi TC: {kiwi_url}{kiwi['id']}/"]

    if is_valid(kiwi.get("requirement")):
        parts.append(f"Requirements: {kiwi['requirement'].strip()}")

    if is_valid(kiwi.get("extra_link")):
        parts.append(f"Reference link: {kiwi['extra_link'].strip()}")

    if is_valid(kiwi.get("notes")):
        parts.append(f"Notes: {kiwi['notes'].strip()}")

    return "\n".join(parts)


def build_payload(kiwi, qase, mode, kiwi_url):

    wipe = (mode == "3")

    payload = {
        "steps": kiwi["steps"] if not wipe else [],
        "description": "" if wipe else build_description(kiwi, kiwi_url)
    }

    # =========================
    # TITLE LOGIC
    # =========================
    if mode == "1":
        payload["title"] = kiwi["title"]
    else:
        payload["title"] = qase.get("title") or kiwi["title"]

    # =========================
    # PRECONDITIONS
    # =========================
    if mode != "3":
        payload["preconditions"] = kiwi.get("preconditions", "")

    # =========================
    # PRIORITY (SAFE MAPPING)
    # =========================
    priority_raw = kiwi.get("priority")

    if isinstance(priority_raw, str):
        priority = PRIORITY_MAP.get(priority_raw.strip().lower())
    else:
        priority = priority_raw

    # fallback to safe default (medium)
    if priority not in (0, 1, 2, 3):
        priority = 1

    payload["priority"] = priority

    return payload