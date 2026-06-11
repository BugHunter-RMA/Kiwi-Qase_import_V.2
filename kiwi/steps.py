import re

# ── заголовки секции шагов ──────────────────────────────────────────────
STEPS_HEADER_RE = re.compile(
    r"(?:^|\n)\s*(?:#{1,4}\s*)?(?:\*{1,2})?\s*"
    r"(Шаги по воспроизведению(?: и Ожидаемый [Рр]езультат)?|Шаги воспроизведения|Шаги|Steps to reproduce|Steps)"
    r"\s*(?:\*{1,2})?\s*:?\s*(?:\n|$)",
    re.IGNORECASE
)

# ── заголовки блочного ОР (отдельная секция) ───────────────────────────
EXPECTED_BLOCK_HEADER_RE = re.compile(
    r"(?:^|\n)\s*(?:#{1,4}\s*)?(?:\*{1,2})?\s*"
    r"(Ожидаемые результаты|Expected results?)"
    r"\s*(?:\*{1,2})?\s*:?\s*(?:\n|$)",
    re.IGNORECASE
)

# ── стоп-секции после шагов ────────────────────────────────────────────
STOP_SECTION_RE = re.compile(
    r"(?:^|\n)\s*(?:#{1,4}\s*)?(?:\*{1,2})?\s*"
    r"(Постусловие|Примечания|Тестовые данные|Notes|Post.?condition)"
    r"\s*(?:\*{1,2})?\s*:?\s*(?:\n|$)",
    re.IGNORECASE
)

# ── инлайн-маркер ОР внутри шага ───────────────────────────────────────
INLINE_ER_RE = re.compile(
    r"^\s*\*{0,2}\s*(ОР|Ожидаемый результ[а-я]*)\s*\*{0,2}\s*:?\s*\*{0,2}\s*(.*)?$",
    re.IGNORECASE
)

# ── нумерованный шаг ───────────────────────────────────────────────────
STEP_NUM_RE = re.compile(r"(?:^|\n)(\d+)\.\s+")


def _extract_steps_text(text):
    """Обрезаем текст: берём только секцию шагов."""
    m = STEPS_HEADER_RE.search(text)
    if m:
        text = text[m.end():]

    # обрезаем стоп-секции в конце
    stop = STOP_SECTION_RE.search(text)
    if stop:
        text = text[:stop.start()]

    return text


def _split_steps_and_expected_block(text):
    """
    Если есть отдельный блок ОР — делим.
    Возвращает (steps_text, expected_block_text or None)
    """
    m = EXPECTED_BLOCK_HEADER_RE.search(text)
    if m:
        return text[:m.start()], text[m.end():]
    return text, None


def _parse_numbered_items(text):
    """Парсит нумерованный список → список строк."""
    matches = list(STEP_NUM_RE.finditer(text))
    items = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        items.append(text[start:end].strip())
    return items


def _clean_action(text):
    text = re.sub(r"\*+\s*$", "", text).strip()
    text = re.sub(r" {2,}", " ", text)
    return text


def parse_steps(text):
    text = (text or "").replace("\r\n", "\n")

    # 1. Обрезаем до секции шагов
    text = _extract_steps_text(text)

    # 2. Проверяем блочный формат (отдельная секция ОР)
    steps_text, expected_block = _split_steps_and_expected_block(text)

    if expected_block is not None:
        # ── БЛОЧНЫЙ ФОРМАТ ──────────────────────────────────────────
        step_actions = _parse_numbered_items(steps_text)
        step_expected = _parse_numbered_items(expected_block)

        steps = []
        for i, action in enumerate(step_actions):
            action = _clean_action(action)
            if not action:
                continue
            step = {
                "action": action,
                "_raw_chunk": action,
            }
            if i < len(step_expected):
                er = step_expected[i].strip()
                if er:
                    step["expected_result"] = er
            steps.append(step)
        return steps

    # ── ПОПАРНЫЙ ФОРМАТ (шаг → ОР inline) ───────────────────────────
    matches = list(STEP_NUM_RE.finditer(text))
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
            er_match = INLINE_ER_RE.match(line)
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

        action = _clean_action("\n".join(action_lines))
        expected = "\n".join(expected_lines).strip()

        if action:
            step = {
                "action": action,
                "_raw_chunk": chunk,
            }
            if expected:
                step["expected_result"] = expected
            steps.append(step)

    return steps


def finalize_steps(steps):
    return [
        {k: v for k, v in s.items() if k != "_raw_chunk"}
        for s in steps
    ]