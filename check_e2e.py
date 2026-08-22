import json

with open("angel_scrips.json", "r") as f:
    angel_data = json.load(f)

matches = [e for e in angel_data if "E2E" in str(e.get("symbol", "")).upper() or "E2E" in str(e.get("name", "")).upper()]

print(f"Found {len(matches)} matches:")
for e in matches:
    print(f"  symbol={e.get('symbol')} name={e.get('name')} token={e.get('token')} exch={e.get('exch_seg')}")