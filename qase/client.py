import os
import requests
from pathlib import Path

from config import PROJECT_CODE


def get_headers():
    qase_token = os.environ.get("QASE_TOKEN", "").strip()
    if not qase_token:
        raise ValueError("QASE_TOKEN not found in environment. Please set it in .env file or as an environment variable.")
    return {
        "Content-Type": "application/json",
        "Token": qase_token
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