import re


def parse_steps(text):
    """
    Parse numbered steps from Kiwi text block.
    Handles:
    - **Ожидаемый результат:** or ОР: markers (bold markdown)
    - Multi-line expected results (preserves line breaks)
    - Trailing bold markers on action lines
    - Inline image markdown (kept as-is; stripped later by attachments module)
    """
    text = (text or "").replace("\r\n", "\n")

    # Only parse the steps section (after "Шаги по воспроизведению")
    steps_header = re.search(
        r"#{1,4}\s*\*{0,2}\s*Шаги по воспроизведению\s*\*{0,2}\s*:?\s*",
        text, re.IGNORECASE
    )
    if steps_header:
        text = text[steps_header.end():]

    matches = list(re.finditer(r"(?:^|\n)(\d+)\.\s+", text))
    steps = []

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()

        lines = chunk.splitlines()
        action_lines = []
        expected_lines = []
        in_expected = False

        for line in lines:
            er_match = re.match(
                r"^\s*\*{0,2}\s*(ОР|Ожидаемый результат)\s*\*{0,2}\s*:?\s*\*{0,2}\s*(.*)?$",
                line, re.IGNORECASE
            )
            if er_match:
                in_expected = True
                inline = er_match.group(2)
                if inline and inline.strip():
                    expected_lines.append(inline.strip())
                continue

            if in_expected:
                expected_lines.append(line)
            else:
                action_lines.append(line)

        # Clean action: remove trailing bold markers
        action = "\n".join(action_lines).strip()
        action = re.sub(r"\*+\s*$", "", action).strip()
        action = re.sub(r" {2,}", " ", action)

        # Preserve line breaks in expected result
        expected = "\n".join(expected_lines).strip()

        if action:
            step = {
                "action": action,
                "_raw_chunk": chunk,   # kept for attachment extraction
            }
            if expected:
                step["expected_result"] = expected
            steps.append(step)

    return steps


def finalize_steps(steps):
    """
    Remove internal _raw_chunk key before sending to Qase API.
    Call this after attachment migration is complete.
    """
    return [
        {k: v for k, v in s.items() if k != "_raw_chunk"}
        for s in steps
    ]
