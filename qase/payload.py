# PRODUCTION-STABLE
# No circular imports
# Safe payload generation
# API-compatible priority mapping (numeric Kiwi keys)

from core.utils import is_valid


def build_description(kiwi, kiwi_url):
    parts = [f"Kiwi TC: {kiwi_url}{kiwi['id']}/"]

    if is_valid(kiwi.get("requirement")):
        parts.append(f"Requirements:\n{kiwi['requirement'].strip()}")

    if is_valid(kiwi.get("extra_link")):
        parts.append(f"Reference link:\n{kiwi['extra_link'].strip()}")

    if is_valid(kiwi.get("notes")):
        parts.append(f"Notes:\n{kiwi['notes'].strip()}")

    return "\n\n".join(parts)


def build_payload(kiwi, qase, mode, kiwi_url):
    wipe = (mode == "3")

    payload = {
        "steps": kiwi["steps"] if not wipe else [],
        "steps_type": "classic",
        "description": "" if wipe else build_description(kiwi, kiwi_url),
        "preconditions": "" if wipe else kiwi.get("preconditions", ""),
        # priority already mapped to Qase int in kiwi/parser.py
        "priority": kiwi.get("priority", 0),
        "automation": kiwi.get("automation", 0),
        "tags": kiwi.get("tags", []),
    }

    if mode == "1":
        payload["title"] = kiwi["title"]
    else:
        payload["title"] = qase.get("title") or kiwi["title"]

    return payload
