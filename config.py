# STABLE BLOCK
# Approved. Centralized project constants.
# Credentials loaded from .env file (never hardcoded, never committed)

from pathlib import Path

# ── optional: load .env if python-dotenv is available ──────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # dotenv not installed — set env vars manually or use .env fallback below

import os

# ── fallback: read .env manually if dotenv not installed ───────────────
def _load_env_file():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

_load_env_file()

# ── constants ───────────────────────────────────────────────────────────

SCRIPT_VERSION = "2.1.0"

PROJECT_CODE = "TP"

KIWI_BASE_URL = "https://kiwi.takeprofit.team"

KIWI_URL = f"{KIWI_BASE_URL}/case/"

# Kiwi credentials — read from .env
KIWI_USERNAME = os.environ.get("KIWI_USERNAME", "")
KIWI_PASSWORD = os.environ.get("KIWI_PASSWORD", "")
