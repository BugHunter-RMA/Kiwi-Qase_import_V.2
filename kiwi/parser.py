# STABLE BLOCK
# Approved. Kiwi case normalization layer.

from kiwi.steps import parse_steps
from kiwi.preconditions import extract_preconditions

# =========================================================
# PRIORITY MAPPING
# Kiwi: 1=КРИТИЧЕСКИЙ, 2=ВЫСОКИЙ, 3=СРЕДНИЙ, 4=НИЗКИЙ, 5=НИЗШИЙ
# Qase: 0=Not set, 1=Critical, 2=High, 3=Medium, 4=Low
# =========================================================
PRIORITY_MAP = {
    "1": 1,  # Critical
    "2": 2,  # High
    "3": 3,  # Medium
    "4": 4,  # Low
    "5": 4,  # Low (no "Lowest" in Qase)
}

# =========================================================
# STATUS MAPPING
# Kiwi case_status: 1=ОЖИДАЕТ АПРУВА, 2=СОГЛАСОВАН
# Qase status: 0=Actual, 1=Draft, 2=Deprecated
# =========================================================
STATUS_MAP = {
    "1": 1,  # Draft
    "2": 0,  # Actual
}


def map_automation(is_automated):
    """
    Kiwi is_automated: "True"/"False"
    Qase automation: 0=Not automated, 1=To be automated, 2=Automated
    """
    if str(is_automated).strip().lower() == "true":
        return 2
    return 0


def parse_kiwi_case(c):
    tags = []
    category = (c.get("category__name") or "").strip()
    if category:
        tags.append(category)

    return {
        "id": c["id"],
        "title": (c.get("summary") or "").strip(),
        "preconditions": extract_preconditions(c.get("text")),
        "steps": parse_steps(c.get("text")),
        "requirement": c.get("requirement"),
        "extra_link": c.get("extra_link"),
        "notes": c.get("notes"),
        # numeric priority key for correct mapping
        "priority": PRIORITY_MAP.get(str(c.get("priority", "")), 0),
        "status": STATUS_MAP.get(str(c.get("case_status", "")), 0),
        "automation": map_automation(c.get("is_automated", "False")),
        "tags": tags,
    }
