# APPROVED
# Stable audit logging layer with consistent versioning and JSONL output

import json
from datetime import datetime, timezone
from pathlib import Path

from config import SCRIPT_VERSION


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def write_audit_log(entry: dict):
    try:
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%d %H:%M:%S UTC")

        safe_entry = {
            "timestamp": ts,
            "version": SCRIPT_VERSION,
            **(entry or {})
        }

        file_name = LOG_DIR / f"qase_migration_{now.strftime('%Y%m%d')}.jsonl"

        with open(file_name, "a", encoding="utf-8") as f:
            f.write(json.dumps(safe_entry, ensure_ascii=False) + "\n")

    except Exception as e:
        print(f"⚠️ AUDIT LOGGING FAILED: {e}")