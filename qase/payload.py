# PRODUCTION-STABLE
# No circular imports
# Safe payload generation
# API-compatible priority mapping (numeric Kiwi keys)
# Supports per-step attachments

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

    # Steps: strip internal _raw_chunk, include attachments if present
    steps = []
    for s in (kiwi["steps"] if not wipe else []):
        step = {k: v for k, v in s.items() if k != "_raw_chunk"}
        steps.append(step)

    payload = {
        "steps": steps,
        "steps_type": "classic",
        "description": "" if wipe else build_description(kiwi, kiwi_url),
        "preconditions": "" if wipe else kiwi.get("preconditions", ""),
        "priority": kiwi.get("priority", 0),
        "automation": kiwi.get("automation", 0),
        "tags": kiwi.get("tags", []),
        "behavior": 0 if wipe else kiwi.get("behavior", 0),
        "type": 1 if wipe else kiwi.get("type", 2),
    }

    if mode == "1":
        payload["title"] = kiwi["title"]
    else:
        payload["title"] = qase.get("title") or kiwi["title"]

    return payload