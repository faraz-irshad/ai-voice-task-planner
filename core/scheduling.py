def build_schedule(prioritized_tasks: list[dict]) -> dict:
    today: list[dict] = []
    tomorrow: list[dict] = []
    later: list[dict] = []

    for item in prioritized_tasks:
        p = (item.get("priority") or "").strip().lower()

        if p == "urgent & important":
            today.append(item)
        elif p == "urgent & not important":
            today.append(item)
        elif p == "important & not urgent":
            tomorrow.append(item)
        elif p == "not urgent & not important":
            later.append(item)

    print(f"Today : {today}")
    print(f"Tmrw : {tomorrow}")
    print(f"Later : {later}")

    return {
        "today": today,
        "tomorrow": tomorrow,
        "later": later,
    }
