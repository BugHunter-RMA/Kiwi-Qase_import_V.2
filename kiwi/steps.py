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

        action_lines = []
        expected_lines = []

        in_expected = False

        for line in lines:

            # --- detect expected result header ---
            match = re.match(
                r"^\s*\*{0,2}\s*(ОР|Ожидаемый результат)\s*\*{0,2}\s*:?\s*(.*)$",
                line,
                re.I
            )

            if match:
                in_expected = True

                # 🔥 FIX 1: inline expected result (ОР: ...)
                if match.group(2):
                    expected_lines.append(match.group(2).strip())

                continue

            if in_expected:
                expected_lines.append(line)
            else:
                action_lines.append(line)

        action = re.sub(r"\s+", " ", "\n".join(action_lines)).strip()
        expected = re.sub(r"\s+", " ", "\n".join(expected_lines)).strip()

        if action:

            step = {"action": action}

            if expected:
                step["expected_result"] = expected

            steps.append(step)

    return steps