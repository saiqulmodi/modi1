import json

with open("angel_scrips.json", "r") as f:
    angel_data = json.load(f)

targets = ["STLTECH", "MTARTECH", "DIACABS"]

for t in targets:
    print(f"\n--- {t} (broad search, all exchanges) ---")
    matches = [e for e in angel_data if t in str(e.get("symbol", "")).upper() or t in str(e.get("name", "")).upper()]
    if not matches:
        print("  NOT FOUND anywhere in angel_scrips.json")
    else:
        for e in matches:
            print(f"  symbol={e.get('symbol')} name={e.get('name')} token={e.get('token')} exch={e.get('exch_seg')} instrumenttype={e.get('instrumenttype')}")