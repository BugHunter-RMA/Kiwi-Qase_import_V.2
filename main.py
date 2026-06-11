import json
from pathlib import Path

from config import SCRIPT_VERSION, KIWI_URL, KIWI_BASE_URL, PROJECT_CODE

from kiwi.parser import parse_kiwi_case
from kiwi.attachments import migrate_step_attachments, extract_image_urls, strip_images

from qase.client import get_case, update_case, get_headers
from qase.payload import build_payload

from core.diff import compare_fields
from core.utils import get_runtime_timestamps
from core.audit_logger import write_audit_log
from core.validator import validate_payload


FILES_USED = [
    "main.py",
    "kiwi/parser.py",
    "kiwi/steps.py",
    "kiwi/preconditions.py",
    "kiwi/attachments.py",
    "qase/payload.py",
    "qase/client.py",
    "core/utils.py",
    "core/diff.py",
    "core/validator.py",
]


def has_attachments(steps):
    """Check if any step contains embedded images."""
    return any(
        extract_image_urls(s.get("_raw_chunk", ""))
        for s in steps
    )


def migrate_attachments(steps):
    """
    For each step:
    - Download images from Kiwi (no auth needed)
    - Upload to Qase
    - Strip image markdown from action and expected_result
    - Add attachment hashes to step
    """
    qase_hdrs = get_headers()

    for step in steps:
        raw = step.pop("_raw_chunk", "")
        images = extract_image_urls(raw)

        if not images:
            continue

        print(f"  Step: {step['action'][:60]}...")

        _, hashes = migrate_step_attachments(
            raw, KIWI_BASE_URL, PROJECT_CODE, qase_hdrs
        )

        if hashes:
            step["attachments"] = hashes

        # Strip image markdown from action and expected_result
        step["action"] = strip_images(step.get("action", ""))
        if "expected_result" in step:
            step["expected_result"] = strip_images(step["expected_result"])

    return steps


def main():
    ts = get_runtime_timestamps()
    print(f"\nv{SCRIPT_VERSION}")
    print(ts["utc"])
    print(ts["pl"])

    kiwi_id = input("Kiwi ID: ").strip()
    qase_id = input("Qase ID: ").strip()

    # --- load kiwi export ---
    try:
        kiwi_raw = json.loads(
            Path("kiwi_export.json").read_text(encoding="utf-8")
        )
    except Exception as e:
        print(f"❌ Failed to read kiwi_export.json: {e}")
        return

    # --- find kiwi case ---
    try:
        kiwi_obj = next(
            x for x in kiwi_raw if str(x.get("id")) == kiwi_id
        )
    except StopIteration:
        print(f"❌ Kiwi ID not found: {kiwi_id}")
        return

    kiwi = parse_kiwi_case(kiwi_obj)

    # --- get qase case ---
    qase = get_case(qase_id)

    # --- preview diff ---
    preview_payload = build_payload(kiwi, qase, "2", KIWI_URL)
    compare_fields(preview_payload, qase)

    # --- MODE SELECTION ---
    print("\nВыберите режим работы миграции:\n")
    print("  1 - ПОЛНАЯ ПЕРЕЗАПИСЬ (FULL OVERWRITE)")
    print("      Полностью заменяет тест-кейс в Qase данными из Kiwi.")
    print("      ⚠️  Старые шаги и описание будут удалены.\n")
    print("  2 - БЕЗОПАСНОЕ ОБНОВЛЕНИЕ (SAFE UPDATE)")
    print("      Обновляет только изменённые поля.")
    print("      ⭐ Рекомендуется.\n")
    print("  3 - ОЧИСТКА (WIPE MODE)")
    print("      Удаляет шаги и описание, оставляет метаданные.\n")

    mode = input("Введите режим [1/2/3]: ").strip()
    if mode not in {"1", "2", "3"}:
        print("❌ Неверный режим. Допустимые значения: 1, 2, 3")
        return

    # --- ATTACHMENTS ---
    if mode != "3" and has_attachments(kiwi["steps"]):
        migrate_att = input(
            "\n📎 В кейсе найдены скриншоты. Перенести в Qase? [y/n]: "
        ).strip().lower()

        if migrate_att == "y":
            print("\n⬇️  Загружаем скриншоты из Kiwi...\n")
            kiwi["steps"] = migrate_attachments(kiwi["steps"])
            print()
        else:
            # Strip _raw_chunk and image markdown without uploading
            for s in kiwi["steps"]:
                s.pop("_raw_chunk", None)
                s["action"] = strip_images(s.get("action", ""))
                if "expected_result" in s:
                    s["expected_result"] = strip_images(s["expected_result"])
    else:
        for s in kiwi["steps"]:
            s.pop("_raw_chunk", None)
            s["action"] = strip_images(s.get("action", ""))
            if "expected_result" in s:
                s["expected_result"] = strip_images(s["expected_result"])

    # --- CONFIRMATION ---
    confirm = input("Proceed? [y/n]: ").strip().lower()
    if confirm != "y":
        print("❌ Aborted by user")
        return

    # --- BUILD PAYLOAD ---
    payload = build_payload(kiwi, qase, mode, KIWI_URL)

    # --- VALIDATION ---
    validation = validate_payload(payload, mode)

    if not validation["ok"]:
        print("\n❌ VALIDATION FAILED:")
        for err in validation["errors"]:
            print(" -", err)
        write_audit_log({
            "kiwi_id": kiwi_id, "qase_id": qase_id, "mode": mode,
            "status": "validation_failed", "errors": validation["errors"],
            "payload": payload, "files": FILES_USED
        })
        return

    if validation["warnings"]:
        print("\n⚠️  WARNINGS:")
        for w in validation["warnings"]:
            print(" -", w)

    # --- SEND TO QASE ---
    print("\nSending...\n")
    result = update_case(qase_id, payload)

    write_audit_log({
        "kiwi_id": kiwi_id, "qase_id": qase_id, "mode": mode,
        "status": "success", "payload": payload,
        "result": result, "files": FILES_USED
    })

    print("✅ DONE")


if __name__ == "__main__":
    main()
