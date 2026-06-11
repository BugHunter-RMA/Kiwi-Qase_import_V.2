#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests


SCRIPT_VERSION = "2.0.0"

PROJECT_CODE = "TP"

HEADERS = {
    "Content-Type": "application/json",
    "Token": Path("qase_token.txt").read_text(encoding="utf-8").strip()
}


# =========================================================
# TIME
# =========================================================

def get_runtime_timestamps():
    now_utc = datetime.now(timezone.utc)
    now_pl = now_utc.astimezone(ZoneInfo("Europe/Warsaw"))
    return {
        "utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "pl": now_pl.strftime("%Y-%m-%d %H:%M:%S Europe/Warsaw"),
    }


# =========================================================
# UTILS
# =========================================================

def is_valid(value):
    if value is None:
        return False
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ["", "none", "null", "nan"]:
            return False
    return True


def clean(text):
    return (text or "").strip()


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
    "5": 4,  # Low (нет аналога "Lowest" в Qase)
}


# =========================================================
# STATUS MAPPING
# Kiwi case_status: 1=ОЖИДАЕТ АПРУВА, 2=СОГЛАСОВАН
# Qase status: 0=Actual, 1=Draft, 2=Deprecated
# =========================================================

STATUS_MAP = {
    "1": 1,  # Ожидает апрува -> Draft
    "2": 0,  # Согласован -> Actual
}


# =========================================================
# AUTOMATION MAPPING
# Kiwi is_automated: "True"/"False"
# Qase automation: 0=Not automated, 1=To be automated, 2=Automated
# =========================================================

def map_automation(is_automated):
    if str(is_automated).strip().lower() == "true":
        return 2  # Automated
    return 0  # Not automated


# =========================================================
# PRECONDITIONS + STEPS PARSER
#
# Kiwi text structure:
# #### **Предусловия:**
# - line1
# - line2
#
# #### **Шаги по воспроизведению:**
# 1. Step text
# **Ожидаемый результат:** Expected text
#
# 2. Step text
# **Ожидаемый результат:** Expected text
# =========================================================

def parse_text(text):
    """
    Returns (preconditions: str, steps: list[dict])
    """
    text = clean(text).replace("\r\n", "\n")

    preconditions = ""
    steps_text = text

    # Split on "Шаги по воспроизведению" header
    steps_header_pattern = re.compile(
        r"#{1,4}\s*\*{0,2}Шаги по воспроизведению\*{0,2}\s*:?\*{0,2}",
        re.IGNORECASE
    )
    precond_header_pattern = re.compile(
        r"#{1,4}\s*\*{0,2}Предусловия\*{0,2}\s*:?\*{0,2}",
        re.IGNORECASE
    )

    steps_match = steps_header_pattern.search(text)
    precond_match = precond_header_pattern.search(text)

    if precond_match and steps_match:
        # Extract preconditions block
        precond_start = precond_match.end()
        precond_end = steps_match.start()
        preconditions = clean(text[precond_start:precond_end])
        steps_text = text[steps_match.end():]

    elif precond_match and not steps_match:
        # Only preconditions, no numbered steps
        preconditions = clean(text[precond_match.end():])
        steps_text = ""

    elif steps_match and not precond_match:
        steps_text = text[steps_match.end():]

    steps = parse_steps(steps_text)
    return preconditions, steps


def parse_steps(text):
    """
    Parse numbered steps with optional expected results.
    Handles bold markdown like **Ожидаемый результат:**
    """
    text = clean(text)
    if not text:
        return []

    # Split on numbered step markers: "1. ", "2. " etc.
    matches = list(re.finditer(r"(?:^|\n)(\d+)\.\s+", text))

    steps = []

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()

        action = chunk
        expected = ""

        # Split on "Ожидаемый результат:" (with optional bold **)
        er_pattern = re.compile(
            r"\*{0,2}\s*Ожидаемый результат\s*\*{0,2}\s*:?\s*\*{0,2}\s*",
            re.IGNORECASE
        )
        er_match = er_pattern.search(chunk)

        if er_match:
            action = clean(chunk[:er_match.start()])
            expected = clean(chunk[er_match.end():])
        
        # Remove trailing bold markers from action
        action = re.sub(r"\*+$", "", action).strip()

        if action:
            step = {"action": action}
            if expected:
                step["expected_result"] = expected
            steps.append(step)

    return steps


# =========================================================
# DESCRIPTION BUILDER
# =========================================================

def build_description(kiwi, wipe=False):
    if wipe:
        return ""

    parts = []
    parts.append(f"Kiwi TC: https://kiwi.takeprofit.team/case/{kiwi['id']}/")

    if is_valid(kiwi.get("requirement")):
        parts.append(f"Requirements:\n{kiwi['requirement'].strip()}")

    if is_valid(kiwi.get("extra_link")):
        parts.append(f"Reference link:\n{kiwi['extra_link'].strip()}")

    if is_valid(kiwi.get("notes")):
        parts.append(f"Notes:\n{kiwi['notes'].strip()}")

    return "\n\n".join(parts)


# =========================================================
# KIWI PARSER
# =========================================================

def parse_kiwi_case(c):
    preconditions, steps = parse_text(c.get("text", ""))

    # Tags: category name
    tags = []
    if is_valid(c.get("category__name")):
        tags.append(c["category__name"].strip())

    return {
        "id": c["id"],
        "title": clean(c.get("summary", "")),
        "preconditions": preconditions,
        "steps": steps,
        "description": build_description(c),
        "priority": PRIORITY_MAP.get(str(c.get("priority", "")), 0),
        "status": STATUS_MAP.get(str(c.get("case_status", "")), 0),
        "automation": map_automation(c.get("is_automated", "False")),
        "tags": tags,
        "requirement": c.get("requirement"),
        "extra_link": c.get("extra_link"),
        "notes": c.get("notes"),
    }


# =========================================================
# PAYLOAD BUILDER
# =========================================================

def build_payload(kiwi, qase, mode):
    wipe = (mode == "3")

    payload = {
        "steps": kiwi["steps"] if not wipe else [],
        "steps_type": "classic",
        "description": kiwi["description"] if not wipe else "",
        "preconditions": kiwi["preconditions"] if not wipe else "",
        "priority": kiwi["priority"],
        "automation": kiwi["automation"],
        "tags": kiwi["tags"],
    }

    if mode == "1":
        payload["title"] = kiwi["title"]
    else:
        payload["title"] = qase.get("title", kiwi["title"])

    return payload


# =========================================================
# DIFF
# =========================================================

def compare_fields(kiwi, qase):
    print("\n📊 KIWI → QASE DIFF\n")

    checks = [
        ("title",         kiwi["title"],         qase.get("title")),
        ("preconditions", kiwi["preconditions"],  qase.get("preconditions")),
        ("steps count",   len(kiwi["steps"]),     len(qase.get("steps", []))),
        ("priority",      kiwi["priority"],       qase.get("priority")),
        ("automation",    kiwi["automation"],      qase.get("automation")),
    ]

    for label, kiwi_val, qase_val in checks:
        icon = "✅" if kiwi_val == qase_val else "🔄"
        print(f"  {icon} {label}: Kiwi={kiwi_val!r}  Qase={qase_val!r}")

    print()


# =========================================================
# MODE SELECTION
# =========================================================

def select_mode():
    print("\nChoose update mode:\n")
    print("1 - Replace everything (title + all fields)")
    print("2 - Replace data except title")
    print("3 - Clear all text fields (steps, description, preconditions)\n")

    while True:
        m = input("Mode [1/2/3]: ").strip()
        if m in ["1", "2", "3"]:
            return m


def confirm(mode):
    labels = {
        "1": "replace ALL data in this test case",
        "2": "replace steps, description and preconditions, keep title",
        "3": "delete all text fields, keep title and dropdowns",
    }
    return input(f"Do you really want to {labels[mode]}? [y/n]: ").strip().lower() == "y"


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
# MAIN
# =========================================================

def main():
    ts = get_runtime_timestamps()
    print(f"\nv{SCRIPT_VERSION}")
    print(ts["utc"])
    print(ts["pl"])

    kiwi_id = input("Kiwi ID: ").strip()
    qase_id = input("Qase ID: ").strip()

    kiwi_raw = json.loads(Path("kiwi_export.json").read_text(encoding="utf-8"))
    raw_case = next((x for x in kiwi_raw if str(x["id"]) == kiwi_id), None)

    if raw_case is None:
        print(f"❌ Kiwi case {kiwi_id} not found in kiwi_export.json")
        return

    kiwi = parse_kiwi_case(raw_case)
    qase = get_qase_case(qase_id)

    compare_fields(kiwi, qase)

    mode = select_mode()

    if not confirm(mode):
        print("Canceled")
        return

    payload = build_payload(kiwi, qase, mode)

    print("\nSending...\n")
    update_qase(qase_id, payload)
    print("✅ DONE")


if __name__ == "__main__":
    main()
