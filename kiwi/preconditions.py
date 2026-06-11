# STABLE BLOCK
# Approved. Preconditions extraction.

import re

def extract_preconditions(text):

    if not text:
        return ""

    lines = text.replace("\r\n", "\n").split("\n")

    start = None

    headers = [
        "предусловия",
        "преусловия",
        "preconditions",
        "precondition",
        "pre-condition",
        "pre-conditions"
    ]

    for i, line in enumerate(lines):
        normalized = re.sub(r"[*#:\s]", "", line.lower())
        if normalized in headers:
            start = i + 1
            break

    if start is None:
        return ""

    end = len(lines)

    stop_headers = [
        "шаги",
        "steps",
        "stepstoreproduce",
        "шагиповоспроизведению"
    ]

    for i in range(start, len(lines)):
        normalized = re.sub(r"[*#:\s]", "", lines[i].lower())
        if normalized in stop_headers:
            end = i
            break

    return "\n".join(lines[start:end]).strip()