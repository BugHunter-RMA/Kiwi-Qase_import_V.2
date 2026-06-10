def compare_fields(payload, qase):

    print("\n📊 KIWI vs QASE DIFF REPORT\n")

    fields = ["title", "priority", "steps"]

    for f in fields:
        if payload.get(f) == qase.get(f):
            print(f"✅ {f}: MATCH")
        else:
            print(f"❌ {f}: DIFF")