import json
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

SCRIPT_VERSION = "1.0.34"


def write_audit_log(entry: dict):
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        safe_entry = {
            "timestamp": ts,
            "version": SCRIPT_VERSION,
            **(entry or {})
        }

        file_name = LOG_DIR / f"qase_migration_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"

        with open(file_name, "a", encoding="utf-8") as f:
            f.write(json.dumps(safe_entry, ensure_ascii=False) + "\n")

    except Exception as e:
        print(f"⚠️ LOGGING FAILED: {e}")