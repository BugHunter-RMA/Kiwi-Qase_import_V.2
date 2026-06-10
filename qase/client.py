# APPROVED
# Clean Qase API client layer (production-safe for migration tool)

import requests
from pathlib import Path

from config import PROJECT_CODE


def get_headers():
    return {
        "Content-Type": "application/json",
        "Token": Path("qase_token.txt").read_text().strip()
    }


def get_case(case_id):
    r = requests.get(
        f"https://api.qase.io/v1/case/{PROJECT_CODE}/{case_id}",
        headers=get_headers(),
        timeout=30
    )
    r.raise_for_status()
    return r.json()["result"]


def update_case(case_id, payload):
    r = requests.patch(
        f"https://api.qase.io/v1/case/{PROJECT_CODE}/{case_id}",
        headers=get_headers(),
        json=payload,
        timeout=30
    )

    if not r.ok:
        raise RuntimeError(r.text)

    return r.json()