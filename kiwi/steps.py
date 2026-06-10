import re

def parse_steps(text):

    text = (text or "").replace("\r\n", "\n")

    matches = list(re.finditer(r"(\d+)\.\s*", text))

    steps = []

    for i, m in enumerate(matches):

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        chunk = text[start:end].strip()

        lines = chunk.splitlines()

        action = chunk
        expected = ""

        for idx, line in enumerate(lines):

            if re.match(r"^\s*\*{0,2}\s*(ОР|Ожидаемый результат)\s*\*{0,2}\s*:?.*$", line, re.I):

                action = "\n".join(lines[:idx]).strip()

                expected = "\n".join(lines[idx + 1:]).strip()

                expected = re.sub(r"\s+", " ", expected).strip()

                break

        action = re.sub(r"\s+", " ", action).strip()

        if action:
            step = {"action": action}
            if expected:
                step["expected_result"] = expected
            steps.append(step)

    return steps