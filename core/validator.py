# APPROVED
# Payload validation layer for migration safety

def validate_payload(payload, mode="2"):
    errors = []
    warnings = []

    # --- TITLE ---
    title = payload.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        errors.append("Title is empty or invalid")

    # --- STEPS ---
    steps = payload.get("steps")

    if mode != "3":
        if not isinstance(steps, list) or len(steps) == 0:
            errors.append("Steps are empty")

        else:
            for i, step in enumerate(steps):

                if not isinstance(step, dict):
                    errors.append(f"Step {i} is not a dict")
                    continue

                action = step.get("action")

                if not action or not isinstance(action, str) or not action.strip():
                    errors.append(f"Step {i}: action is empty")

                expected = step.get("expected_result")
                if expected is not None and not isinstance(expected, str):
                    errors.append(f"Step {i}: expected_result must be string")

    # --- PRIORITY ---
    priority = payload.get("priority")
    if priority is None:
        warnings.append("Priority is missing")

    # --- DESCRIPTION ---
    desc = payload.get("description")
    if desc is not None and not isinstance(desc, str):
        errors.append("Description must be string")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }