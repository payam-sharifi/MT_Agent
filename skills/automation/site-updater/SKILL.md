---
name: update_site_data
description: Updates values in site_data.json (such as phone, email, address) for the jarbezan project.
---

# Site Data Updater

When the user asks to update a setting, field, or contact info in site_data.json, run the following Python inline script via shell:

python3 -c '
import json, os
path = "/Users/negin-payam/projects/jarbezan/Ads_client/site_data.json"
key = "$KEY"
val = "$VALUE"

if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data[key] = val
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Successfully updated {key} to {val}")
else:
    print("File not found")
'
