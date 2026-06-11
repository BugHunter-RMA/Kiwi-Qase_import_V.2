#!/usr/bin/env python3
"""
sync.py — Match Kiwi TCs to Qase by title and update missing data.

Logic:
- Full title match (case-sensitive)
- Duplicates in Qase → skip and log
- If Qase has less data → overwrite (except title)
- If expected_result is null in all Qase steps but Kiwi has ER → rewrite
- Migrates attachments from Kiwi to Qase
- Logs all actions to sync_log.jsonl

Flags:
  --case <qase_id>   Process only one specific Qase case by ID
"""

import json
import time
import argparse
import requests
from pathlib import Path

from config import PROJECT_CODE, KIWI_URL, KIWI_BASE_URL
from kiwi.parser import parse_kiwi_case
from kiwi.attachments import strip_images, extract_image_urls, migrate_step_attachments
from qase.client import get_headers, update_case
from qase.payload import build_payload
from core.utils import get_runtime_timestamps
from core.audit_logger import write_audit_log

SYNC_LOG = Path("sync_log.jsonl")


# ── Qase API: fetch all cases with pagination ──────────────────────────

def fetch_all_qase_cases():
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

        time.sleep(0.2)

    print(f"✅ Total Qase cases fetched: {len(all_cases)}\n")
    return all_cases


# ── Qase API: fetch single case by ID ─────────────────────────────────

def fetch_single_qase_case(qase_id):
    headers = get_headers()
    url = f"https://api.qase.io/v1/case/{PROJECT_CODE}/{qase_id}"

    print(f"⬇️  Fetching Qase case {qase_id}...")
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    result = r.json().get("result")
    if not result:
        print(f"❌ Case {qase_id} not found in Qase")
        return None
    print(f"✅ Fetched: {result.get('title')}\n")
    return result


# ── Clean and migrate steps ────────────────────────────────────────────

def prepare_steps(steps):
    """
    Clean steps:
    - Migrate attachments from Kiwi to Qase
    - Strip image markdown from action and expected_result
    - Remove _raw_chunk
    """
    qase_hdrs = get_headers()
    prepared = []

    for s in steps:
        raw = s.pop("_raw_chunk", "")
        images = extract_image_urls(raw)

        if images:
            print(f"  📎 Migrating attachments for step: {s.get('action', '')[:60]}...")
            _, hashes = migrate_step_attachments(
                raw, KIWI_BASE_URL, PROJECT_CODE, qase_hdrs
            )
            if hashes:
                s["attachments"] = hashes

        s["action"] = strip_images(s.get("action", ""))
        if "expected_result" in s:
            s["expected_result"] = strip_images(s["expected_result"])

        prepared.append(s)

    return prepared


# ── Compare: is Qase case "less complete" than Kiwi? ──────────────────

def qase_needs_update(kiwi, qase_case):
    reasons = []

    qase_steps = qase_case.get("steps") or []
    kiwi_steps = [s for s in kiwi.get("steps", []) if s.get("action")]

    # Steps count
    if len(kiwi_steps) > len(qase_steps):
        reasons.append(f"steps: Kiwi={len(kiwi_steps)} Qase={len(qase_steps)}")

    # ОР попали в шаги — все expected_result null, но Kiwi имеет ОР
    qase_all_null_er = all(
        s.get("expected_result") is None
        for s in qase_steps
    ) if qase_steps else False

    kiwi_has_er = any(
        s.get("expected_result")
        for s in kiwi_steps
    )

    if qase_all_null_er and kiwi_has_er:
        reasons.append("expected_result: ОР попали в шаги Qase, нужна перезапись")

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


# ── Process single case ────────────────────────────────────────────────

def process_single(qase_id, kiwi_raw):
    qase_case = fetch_single_qase_case(qase_id)
    if not qase_case:
        return

    qase_title = (qase_case.get("title") or "").strip()

    kiwi_match = None
    for raw in kiwi_raw:
        kiwi = parse_kiwi_case(raw)
        if kiwi["title"] == qase_title:
            kiwi_match = kiwi
            break

    if not kiwi_match:
        print(f"❌ No Kiwi case found with title: '{qase_title}'")
        log_sync({"status": "no_match", "qase_id": qase_id, "title": qase_title})
        return

    reasons = qase_needs_update(kiwi_match, qase_case)
    if not reasons:
        print(f"⏭️  Already up to date: [{qase_id}] {qase_title}")
        log_sync({"status": "up_to_date", "qase_id": qase_id, "title": qase_title})
        return

    print(f"🔄 UPDATE: [{qase_id}] {qase_title}")
    for r in reasons:
        print(f"   • {r}")

    kiwi_match["steps"] = prepare_steps(kiwi_match["steps"])
    payload = build_payload(kiwi_match, qase_case, "1", KIWI_URL)

    try:
        update_case(qase_id, payload)
        print(f"   ✅ Done")
        log_sync({"status": "updated", "qase_id": qase_id,
                  "title": qase_title, "reasons": reasons})
    except Exception as e:
        print(f"   ❌ Error: {e}")
        log_sync({"status": "error", "qase_id": qase_id,
                  "title": qase_title, "error": str(e)})


# ── Process all cases ──────────────────────────────────────────────────

def process_all(kiwi_raw):
    qase_cases = fetch_all_qase_cases()

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

    stats = {"matched": 0, "updated": 0, "skipped_no_match": 0,
             "skipped_duplicate": 0, "skipped_up_to_date": 0, "errors": 0}

    for raw in kiwi_raw:
        kiwi = parse_kiwi_case(raw)
        title = kiwi["title"]

        if title not in qase_by_title and title not in qase_duplicates:
            stats["skipped_no_match"] += 1
            log_sync({"status": "no_match", "title": title, "kiwi_id": kiwi["id"]})
            continue

        if title in qase_duplicates:
            stats["skipped_duplicate"] += 1
            print(f"⚠️  SKIP (duplicate): {title}")
            log_sync({"status": "duplicate", "title": title, "kiwi_id": kiwi["id"]})
            continue

        stats["matched"] += 1
        qase_case = qase_by_title[title]
        qase_id = str(qase_case["id"])

        reasons = qase_needs_update(kiwi, qase_case)
        if not reasons:
            stats["skipped_up_to_date"] += 1
            log_sync({"status": "up_to_date", "title": title,
                      "kiwi_id": kiwi["id"], "qase_id": qase_id})
            continue

        print(f"🔄 UPDATE: [{qase_id}] {title}")
        for r in reasons:
            print(f"   • {r}")

        kiwi["steps"] = prepare_steps(kiwi["steps"])
        payload = build_payload(kiwi, qase_case, "1", KIWI_URL)

        try:
            update_case(qase_id, payload)
            stats["updated"] += 1
            log_sync({"status": "updated", "title": title,
                      "kiwi_id": kiwi["id"], "qase_id": qase_id,
                      "reasons": reasons})
            print(f"   ✅ Done")
        except Exception as e:
            stats["errors"] += 1
            print(f"   ❌ Error: {e}")
            log_sync({"status": "error", "title": title,
                      "kiwi_id": kiwi["id"], "qase_id": qase_id,
                      "error": str(e)})

        time.sleep(0.3)

    print(f"\n{'='*50}")
    print(f"✅ Updated:            {stats['updated']}")
    print(f"📋 Matched:            {stats['matched']}")
    print(f"⏭️  Up to date:         {stats['skipped_up_to_date']}")
    print(f"⚠️  Duplicates skipped: {stats['skipped_duplicate']}")
    print(f"🔍 No match in Qase:   {stats['skipped_no_match']}")
    print(f"❌ Errors:             {stats['errors']}")
    print(f"{'='*50}")
    print(f"\n📄 Log saved to: {SYNC_LOG}")


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sync Kiwi TCs to Qase")
    parser.add_argument(
        "--case", type=str, default=None,
        help="Process only one Qase case by ID (e.g. --case 1639)"
    )
    args = parser.parse_args()

    ts = get_runtime_timestamps()
    print(f"\n🔄 SYNC — Kiwi → Qase")
    print(ts["utc"])
    print(ts["pl"])
    print()

    try:
        kiwi_raw = json.loads(
            Path("kiwi_export.json").read_text(encoding="utf-8")
        )
    except Exception as e:
        print(f"❌ Failed to read kiwi_export.json: {e}")
        return

    if args.case:
        process_single(args.case, kiwi_raw)
    else:
        process_all(kiwi_raw)


if __name__ == "__main__":
    main()