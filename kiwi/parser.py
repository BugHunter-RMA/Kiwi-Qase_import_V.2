from kiwi.steps import parse_steps
from kiwi.preconditions import extract_preconditions

def parse_kiwi_case(c):

    return {
        "id": c["id"],
        "title": c.get("summary", "").strip(),
        "preconditions": extract_preconditions(c.get("text")),
        "steps": parse_steps(c.get("text")),
        "requirement": c.get("requirement"),
        "extra_link": c.get("extra_link"),
        "notes": c.get("notes"),
        "priority": c.get("priority__value")
    }