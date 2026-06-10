import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def write_audit_log(entry: dict):

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    entry["timestamp"] = ts

    file_name = LOG_DIR / f"qase_migration_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"

    with open(file_name, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")