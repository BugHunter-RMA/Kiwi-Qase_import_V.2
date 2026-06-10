# STABLE BLOCK
# Approved. Payload builder layer is structurally correct.

from core.utils import is_valid

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

    if mode == "1":
        payload["title"] = kiwi["title"]
    else:
        payload["title"] = qase.get("title") or kiwi["title"]

    if mode != "3":
        payload["preconditions"] = kiwi.get("preconditions", "")

    payload["priority"] = kiwi.get("priority")

    return payload