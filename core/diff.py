# APPROVED
# Lightweight migration diff tool (debug utility)

def norm(v):
    if isinstance(v, str):
        return v.strip()
    return v


def norm_steps(v):
    if not isinstance(v, list):
        return v

    return [
        {
            "action": s.get("action", "").strip(),
            "expected_result": s.get("expected_result", "").strip()
        }
        for s in v
    ]


def compare_fields(payload, qase):

    print("\n📊 KIWI vs QASE DIFF REPORT\n")

    fields = ["title", "priority", "steps"]

    for f in fields:

        p = payload.get(f)
        q = qase.get(f)

        if f == "steps":
            p = norm_steps(p)
            q = norm_steps(q)
        else:
            p = norm(p)
            q = norm(q)

        if p == q:
            print(f"✅ {f}: MATCH")
        else:
            print(f"❌ {f}: DIFF")