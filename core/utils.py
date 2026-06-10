# APPROVED
# Stable utility layer (no structural changes needed)

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def get_runtime_timestamps():
    now_utc = datetime.now(timezone.utc)
    now_pl = now_utc.astimezone(ZoneInfo("Europe/Warsaw"))

    return {
        "utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "pl": now_pl.strftime("%Y-%m-%d %H:%M:%S Europe/Warsaw"),
    }


def is_valid(value):
    if value is None:
        return False

    if isinstance(value, str):
        v = value.strip().lower()

        if v in ["", "none", "null", "nan"]:
            return False

    return True