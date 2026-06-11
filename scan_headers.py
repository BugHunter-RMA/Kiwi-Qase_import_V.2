import json
import re
from pathlib import Path

data = json.loads(Path("kiwi_export.json").read_text(encoding="utf-8"))

headers = set()

for case in data:
    text = (case.get("text") or "").replace("\r\n", "\n")
    for line in text.split("\n"):
        stripped = line.strip()
        # ловим всё что похоже на заголовок — markdown или жирный текст
        if re.match(r"^(#{1,4}|\*{1,2}).{2,50}(\*{1,2})?:?\s*$", stripped):
            cleaned = re.sub(r"[#*:\s]", "", stripped).lower()
            headers.add(f"{stripped!r:60} -> {cleaned!r}")

for h in sorted(headers):
    print(h)