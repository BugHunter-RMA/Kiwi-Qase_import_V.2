#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests


SCRIPT_VERSION = "1.0.34"

PROJECT_CODE = "TP"

HEADERS = {
    "Content-Type": "application/json",
    "Token": Path("qase_token.txt").read_text(encoding="utf-8").strip()
}


# =========================================================
# STABLE CORE: TIME
# =========================================================

def get_runtime_timestamps():
    now_utc = datetime.now(timezone.utc)
    now_pl = now_utc.astimezone(ZoneInfo("Europe/Warsaw"))

    return {
        "utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "pl": now_pl.strftime("%Y-%m-%d %H:%M:%S Europe/Warsaw"),
    }


# =========================================================
# CLEAN VALUE CHECK (NEW FIX)
# =========================================================

def is_valid(value):
    if value is None:
        return False
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ["", "none", "null", "nan"]:
            return False
    return True


# =========================================================
# MODE SELECTION (SIMPLIFIED UX)
# =========================================================

def select_mode():
    print("\nChoose update mode:\n")

    print("1 - Replace everything in test case")
    print("    (title, steps, description will be overwritten)")

    print("\n2 - Replace data except title")
    print("    (steps + description will be overwritten, title stays same)")

    print("\n3 - Clear all text fields")
    print("    (steps and description will be deleted, title stays, drop-downs unchanged)\n")

    while True:
        m = input("Mode [1/2/3]: ").strip()
        if m in ["1", "2", "3"]:
            return m


# =========================================================
# CONFIRM (A2-LEVEL UX)
# =========================================================

def confirm(mode):
    if mode == "1":
        msg = "replace ALL data in this test case"
    elif mode == "2":
        msg = "replace steps and description, keep title"
    else:
        msg = "delete all text fields (steps and description), keep title"

    return input(f"Do you really want to {msg}? [y/n]: ").strip().lower() == "y"


# =========================================================
# STEP PARSER (unchanged safe zone)
# =========================================================

def parse_steps(text):
    text = (text or "").replace("\r\n", "\n")
    matches = list(re.finditer(r"(\d+)\.\s*", text))

    steps = []

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        chunk = re.sub(r"\s+", " ", text[start:end]).strip()

        expected = ""
        action = chunk

        if "ожидаемый" in chunk.lower() or "ор" in chunk.lower():
            parts = re.split(r"(ожидаемый результат|ор)\s*[:\-]?", chunk, flags=re.I)
            action = parts[0].strip()
            expected = parts[-1].strip()

        if action:
            step = {"action": action}
            if expected:
                step["expected_result"] = expected
            steps.append(step)

    return steps


# =========================================================
# KIWI PARSER
# =========================================================

def parse_kiwi_case(c):
    return {
        "id": c["id"],
        "title": c.get("summary", "").strip(),
        "steps": parse_steps(c.get("text")),
        "requirement": c.get("requirement"),
        "extra_link": c.get("extra_link"),
        "notes": c.get("notes"),
        "priority": c.get("priority__value")
    }


# =========================================================
# DESCRIPTION BUILDER (FIXED None FILTER)
# =========================================================

def build_description(kiwi, wipe=False):

    if wipe:
        return ""

    parts = []

    parts.append(f"Kiwi TC: https://kiwi.takeprofit.team/case/{kiwi['id']}/")

    if is_valid(kiwi.get("requirement")):
        parts.append(f"Requirements: {kiwi['requirement'].strip()}")

    if is_valid(kiwi.get("extra_link")):
        parts.append(f"Reference link: {kiwi['extra_link'].strip()}")

    if is_valid(kiwi.get("notes")):
        parts.append(f"Notes: {kiwi['notes'].strip()}")

    return "\n".join(parts)


# =========================================================
# PAYLOAD
# =========================================================

def build_payload(kiwi, qase, mode):

    wipe = (mode == "3")

    payload = {
        "steps": kiwi["steps"] if not wipe else [],
        "description": build_description(kiwi, wipe)
    }

    if mode == "1":
        payload["title"] = kiwi["title"]
    else:
        payload["title"] = qase.get("title")

    return payload


# =========================================================
# DIFF
# =========================================================

def compare_fields(payload, qase):
    print("\n📊 KIWI vs QASE DIFF REPORT\n")

    order = ["title", "priority", "steps"]

    for k in order:
        if payload.get(k) == qase.get(k):
            print(f"✅ {k}: MATCH")
        else:
            print(f"❌ {k}: DIFF")

    print()


# =========================================================
# API
# =========================================================

def get_qase_case(case_id):
    r = requests.get(
        f"https://api.qase.io/v1/case/{PROJECT_CODE}/{case_id}",
        headers=HEADERS
    )
    r.raise_for_status()
    return r.json()["result"]


def update_qase(case_id, payload):
    r = requests.patch(
        f"https://api.qase.io/v1/case/{PROJECT_CODE}/{case_id}",
        headers=HEADERS,
        json=payload
    )

    if not r.ok:
        raise RuntimeError(r.text)

    return r.json()


# =========================================================
# MAIN (STABLE FLOW)
# =========================================================

def main():

    ts = get_runtime_timestamps()
    print(f"\nv{SCRIPT_VERSION}")
    print(ts["utc"])
    print(ts["pl"])

    kiwi_id = input("Kiwi ID: ").strip()
    qase_id = input("Qase ID: ").strip()

    kiwi_raw = json.loads(Path("kiwi_export.json").read_text(encoding="utf-8"))
    kiwi = parse_kiwi_case(next(x for x in kiwi_raw if str(x["id"]) == kiwi_id))

    qase = get_qase_case(qase_id)

    preview = build_payload(kiwi, qase, "2")
    compare_fields(preview, qase)

    mode = select_mode()

    if not confirm(mode):
        print("Canceled")
        return

    payload = build_payload(kiwi, qase, mode)

    print("\nSending...\n")
    update_qase(qase_id, payload)

    print("DONE")


if __name__ == "__main__":
    main()