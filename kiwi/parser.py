# STABLE BLOCK
# Approved. Kiwi case normalization layer.

from kiwi.steps import parse_steps
from kiwi.preconditions import extract_preconditions

# =========================================================
# PRIORITY MAPPING
# Kiwi: 1=КРИТИЧЕСКИЙ, 2=ВЫСОКИЙ, 3=СРЕДНИЙ, 4=НИЗКИЙ, 5=НИЗШИЙ
# Qase: 0=Not set, 1=Critical, 2=High, 3=Medium, 4=Low
# =========================================================
PRIORITY_MAP = {
    "1": 1,  # Critical
    "2": 2,  # High
    "3": 3,  # Medium
    "4": 4,  # Low
    "5": 4,  # Low (no "Lowest" in Qase)
}

# =========================================================
# STATUS MAPPING
# Kiwi case_status: 1=ОЖИДАЕТ АПРУВА, 2=СОГЛАСОВАН
# Qase status: 0=Actual, 1=Draft, 2=Deprecated
# =========================================================
STATUS_MAP = {
    "1": 1,  # Draft
    "2": 0,  # Actual
}


def map_automation(is_automated):
    """
    Kiwi is_automated: "True"/"False"
    Qase automation: 0=Not automated, 1=To be automated, 2=Automated
    """
    if str(is_automated).strip().lower() == "true":
        return 2
    return 0


def detect_behavior(summary, text=""):
    """
    Determine Qase Behavior based on summary and text keywords.
    Qase: 1=Positive, 2=Negative, 3=Destructive
    """
    combined = f"{summary} {text}".lower()

    destructive_keywords = [
        "удален", "удалени", "удалить", "удаляет", "delete", "removal",
        "сброс", "сбросить", "очистка", "очистить", "reset", "wipe",
    ]
    negative_keywords = [
        "негативн", "невозможно", "нельзя",
        "не отображается", "не работает", "не открывается",
        "не сохраняется", "не применяется",
        "ошибка", "error", "invalid", "fail", "incorrect",
        "запрещен", "недоступен", "заблокирован",
    ]

    for kw in destructive_keywords:
        if kw in combined:
            return 3  # Destructive

    for kw in negative_keywords:
        if kw in combined:
            return 2  # Negative

    return 1  # Positive


def detect_type(summary, text="", category="", priority=0):
    """
    Determine Qase Type based on keywords.
    Qase: 1=Other, 2=Functional, 3=Smoke, 4=Regression,
          5=Security, 6=Usability, 7=Performance, 8=Acceptance,
          9=Compatibility, 10=Integration, 11=Exploratory
    """
    combined = f"{summary} {text} {category}".lower()

    smoke_keywords = [
        "smoke", "смок", "базов", "основн",
        "функциональное тестирование",
    ]
    regression_keywords = [
        "регресс", "regression",
    ]
    security_keywords = [
        "безопасност", "security", "авториз", "логин", "пароль",
        "password", "auth", "permission", "доступ",
    ]
    performance_keywords = [
        "производительност", "performance", "нагрузк",
        "скорост", "timeout", "задержк",
    ]
    integration_keywords = [
        "интеграц", "integration", "api", "webhook",
        "sync", "синхрониз", "подключен", "аккаунт",
    ]
    exploratory_keywords = [
        "исследовательск", "exploratory",
    ]

    # критический приоритет + smoke маркер → Smoke
    if priority == 1:
        for kw in smoke_keywords:
            if kw in combined:
                return 3  # Smoke

    for kw in exploratory_keywords:
        if kw in combined:
            return 11  # Exploratory

    for kw in regression_keywords:
        if kw in combined:
            return 4  # Regression

    for kw in security_keywords:
        if kw in combined:
            return 5  # Security

    for kw in performance_keywords:
        if kw in combined:
            return 7  # Performance

    for kw in integration_keywords:
        if kw in combined:
            return 10  # Integration

    for kw in smoke_keywords:
        if kw in combined:
            return 3  # Smoke

    return 2  # Functional (default)


def parse_kiwi_case(c):
    tags = []
    category = (c.get("category__name") or "").strip()
    if category:
        tags.append(category)

    summary = (c.get("summary") or "").strip()
    text = (c.get("text") or "")
    priority = PRIORITY_MAP.get(str(c.get("priority", "")), 0)

    return {
        "id": c["id"],
        "title": summary,
        "preconditions": extract_preconditions(text),
        "steps": parse_steps(text),
        "requirement": c.get("requirement"),
        "extra_link": c.get("extra_link"),
        "notes": c.get("notes"),
        "priority": priority,
        "status": STATUS_MAP.get(str(c.get("case_status", "")), 0),
        "automation": map_automation(c.get("is_automated", "False")),
        "tags": tags,
        "behavior": detect_behavior(summary, text),
        "type": detect_type(summary, text, category, priority),
    }