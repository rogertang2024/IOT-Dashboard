import json

content = '<img src="/local/intruder_alert.jpg?t={{ as_timestamp(now()) }}" style="width:100%; border-radius: 8px; border: 2px solid #e53935;" />'

md_card = {
    "type": "markdown",
    "title": "📸 Latest Intruder Snapshot (Verified AI)",
    "content": content
}

for path in ["config/.storage/lovelace.lovelace", "config/.storage/lovelace"]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        views = d.get("data", {}).get("config", {}).get("views", [])
        if views:
            cards = views[0].get("cards", [])
            cards = [c for c in cards if not ("Latest Intruder" in c.get("title", ""))]
            cards.append(md_card)
            views[0]["cards"] = cards
            with open(path, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=4)
            print("Successfully updated", path)
    except Exception as e:
        print("Error updating", path, e)
