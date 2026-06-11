#!/usr/bin/env python3
"""
sync.py — Match Kiwi TCs to Qase by title and update missing data.

Logic:
- Full title match (case-sensitive)
- Duplicates in Qase → skip and log
- If Qase has less data → overwrite (except title)
- Logs all actions to sync_log.jsonl
"""

import json
import time
from pathlib import Path
from datetime import datetime, timezone

from config import PROJECT_CODE, KIWI_URL
from kiwi.parser import parse_kiwi_case
from qase.client import get_headers, update_case
from qase.payload import build_payload
from core.utils import get_runtime_timestamps, is_valid
from core.audit_logger import write_audit_log

SYNC_LOG = Path("sync_log.jsonl")


# ── Qase API: fetch all cases with pagination ──────────────────────────

def fetch_all_qase_cases():
    import requests

    headers = get_headers()
    url = f"https://api.qase.io/v1/case/{PROJECT_CODE}"
    limit = 100
    offset = 0
    all_cases = []

    print("⬇️  Fetching all Qase cases...")

    while True:
        r = requests.get(
            url,
            headers=headers,
            params={"limit": limit, "offset": offset},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()

        entities = data.get("result", {}).get("entities", [])
        total = data.get("result", {}).get("total", 0)

        all_cases.extend(entities)
        offset += limit

        print(f"  Fetched {len(all_cases)}/{total}")

        if offset >= total:
            break

        time.sleep(0.2)  # rate limit

    print(f"✅ Total Qase cases fetched: {len(all_cases)}\n")
    return all_cases


# ── Compare: is Qase case "less complete" than Kiwi? ──────────────────

def qase_needs_update(kiwi, qase_case):
    """
    Returns True if Qase case is missing data compared to Kiwi.
    Checks: steps, preconditions, priority, behavior, type, automation.
    """
    reasons = []

    # Steps
    qase_steps = qase_case.get("steps") or []
    kiwi_steps = [s for s in kiwi.get("steps", []) if s.get("action")]
    if len(kiwi_steps) > len(qase_steps):
        reasons.append(f"steps: Kiwi={len(kiwi_steps)} Qase={len(qase_steps)}")

    # Preconditions
    kiwi_pre = (kiwi.get("preconditions") or "").strip()
    qase_pre = (qase_case.get("preconditions") or "").strip()
    if kiwi_pre and not qase_pre:
        reasons.append("preconditions: missing in Qase")

    # Priority
    if kiwi.get("priority", 0) != 0 and qase_case.get("priority", 0) == 0:
        reasons.append("priority: not set in Qase")

    # Behavior
    if kiwi.get("behavior", 0) != 0 and qase_case.get("behavior", 0) == 0:
        reasons.append("behavior: not set in Qase")

    # Type
    if kiwi.get("type", 2) != 1 and qase_case.get("type", 1) == 1:
        reasons.append("type: Other in Qase")

    return reasons


# ── Logging ────────────────────────────────────────────────────────────

def log_sync(entry):
    with SYNC_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Main ───────────────────────────────────────────────────────────────

def main():
    ts = get_runtime_timestamps()
    print(f"\n🔄 SYNC — Kiwi → Qase")
    print(ts["utc"])
    print(ts["pl"])
    print()

    # 1. Load Kiwi export
    try:
        kiwi_raw = json.loads(
            Path("kiwi_export.json").read_text(encoding="utf-8")
        )
    except Exception as e:
        print(f"❌ Failed to read kiwi_export.json: {e}")
        return

    # 2. Fetch all Qase cases
    qase_cases = fetch_all_qase_cases()

    # 3. Build Qase title → case map (detect duplicates)
    qase_by_title = {}
    qase_duplicates = set()

    for c in qase_cases:
        title = (c.get("title") or "").strip()
        if title in qase_by_title:
            qase_duplicates.add(title)
        else:
            qase_by_title[title] = c

    if qase_duplicates:
        print(f"⚠️  Found {len(qase_duplicates)} duplicate titles in Qase — will skip them\n")

    # 4. Process each Kiwi case
    stats = {"matched": 0, "updated": 0, "skipped_no_match": 0,
             "skipped_duplicate": 0, "skipped_up_to_date": 0, "errors": 0}

    for raw in kiwi_raw:
        kiwi = parse_kiwi_case(raw)
        title = kiwi["title"]

        # No match in Qase
        if title not in qase_by_title and title not in qase_duplicates:
            stats["skipped_no_match"] += 1
            log_sync({"status": "no_match", "title": title, "kiwi_id": kiwi["id"]})
            continue

        # Duplicate in Qase
        if title in qase_duplicates:
            stats["skipped_duplicate"] += 1
            print(f"⚠️  SKIP (duplicate): {title}")
            log_sync({"status": "duplicate", "title": title, "kiwi_id": kiwi["id"]})
            continue

        stats["matched"] += 1
        qase_case = qase_by_title[title]
        qase_id = str(qase_case["id"])

        # Check if update needed
        reasons = qase_needs_update(kiwi, qase_case)
        if not reasons:
            stats["skipped_up_to_date"] += 1
            log_sync({"status": "up_to_date", "title": title,
                      "kiwi_id": kiwi["id"], "qase_id": qase_id})
            continue

        print(f"🔄 UPDATE: [{qase_id}] {title}")
        for r in reasons:
            print(f"   • {r}")

        # Build payload (mode=2: safe update, keep title)
        payload = build_payload(kiwi, qase_case, "2", KIWI_URL)

        try:
            update_case(qase_id, payload)
            stats["updated"] += 1
            log_sync({
                "status": "updated", "title": title,
                "kiwi_id": kiwi["id"], "qase_id": qase_id,
                "reasons": reasons,
            })
            print(f"   ✅ Done")
        except Exception as e:
            stats["errors"] += 1
            print(f"   ❌ Error: {e}")
            log_sync({
                "status": "error", "title": title,
                "kiwi_id": kiwi["id"], "qase_id": qase_id,
                "error": str(e),
            })

        time.sleep(0.3)  # rate limit

    # 5. Summary
    print(f"\n{'='*50}")
    print(f"✅ Updated:            {stats['updated']}")
    print(f"📋 Matched:            {stats['matched']}")
    print(f"⏭️  Up to date:         {stats['skipped_up_to_date']}")
    print(f"⚠️  Duplicates skipped: {stats['skipped_duplicate']}")
    print(f"🔍 No match in Qase:   {stats['skipped_no_match']}")
    print(f"❌ Errors:             {stats['errors']}")
    print(f"{'='*50}")
    print(f"\n📄 Log saved to: {SYNC_LOG}")


if __name__ == "__main__":
    main()