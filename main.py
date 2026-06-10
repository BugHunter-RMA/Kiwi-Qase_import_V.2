import json
from pathlib import Path

from config import SCRIPT_VERSION, KIWI_URL

from kiwi.parser import parse_kiwi_case
from qase.client import get_case, update_case
from qase.payload import build_payload
from core.diff import compare_fields
from core.utils import get_runtime_timestamps
from core.audit_logger import write_audit_log
from config import SCRIPT_VERSION

FILES_USED = [
    "main.py",
    "kiwi/parser.py",
    "kiwi/steps.py",
    "kiwi/preconditions.py",
    "qase/payload.py",
    "qase/client.py",
    "core/utils.py",
    "core/diff.py"
]


def main():

    ts = get_runtime_timestamps()

    print(f"\nv{SCRIPT_VERSION}")
    print(ts["utc"])
    print(ts["pl"])

    kiwi_id = input("Kiwi ID: ").strip()
    qase_id = input("Qase ID: ").strip()

    kiwi_raw = json.loads(Path("kiwi_export.json").read_text(encoding="utf-8"))
    kiwi = parse_kiwi_case(next(x for x in kiwi_raw if str(x["id"]) == kiwi_id))

    qase = get_case(qase_id)

    preview = build_payload(kiwi, qase, "2", KIWI_URL)
    compare_fields(preview, qase)

    mode = input("\nMode [1/2/3]: ").strip()

    confirm = input("Proceed? [y/n]: ").strip().lower()
    if confirm != "y":
        return

    payload = build_payload(kiwi, qase, mode, KIWI_URL)

    print("\nSending...\n")
    update_case(qase_id, payload)

    print("DONE")


if __name__ == "__main__":
    main()