import json
import yaml

d = json.load(open("config/.storage/lovelace.lovelace", encoding="utf-8"))
print("=== .storage/lovelace.lovelace (Overview /lovelace/0) ===")
for v in d["data"]["config"].get("views", []):
    print("View:", v.get("title"), "| type:", v.get("type"))
    for i, c in enumerate(v.get("cards", [])):
        print(" ", i, c.get("type"), "|", c.get("title"))

print()
y = yaml.safe_load(open("config/farm_dashboard.yaml", encoding="utf-8"))
print("=== config/farm_dashboard.yaml (Smart Farm /smart-farm/0) ===")
for v in y.get("views", []):
    print("View:", v.get("title"), "| type:", v.get("type"))
    for i, c in enumerate(v.get("cards", [])):
        print(" ", i, c.get("type"), "|", c.get("title"))
