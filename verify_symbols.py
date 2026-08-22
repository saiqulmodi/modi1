import pandas as pd
from intraday_watchlist import INTRADAY_SYMBOLS

print(f"RUN: verify_symbols.py")
print(f"Checking {len(INTRADAY_SYMBOLS)} symbols against nse_scrips.csv...\n")

df = pd.read_csv("nse_scrips.csv")
nse_eq = df[(df["exchangename"] == "NSE") & (df["optiontype"] == "EQ")]
valid_symbols = set(nse_eq["scripshortname"].astype(str))

matched = []
missing = []

for sym in INTRADAY_SYMBOLS:
    if sym in valid_symbols:
        matched.append(sym)
    else:
        missing.append(sym)

print(f"Matched: {len(matched)} / {len(INTRADAY_SYMBOLS)}")
print(f"Missing: {len(missing)}\n")

if missing:
    print("These symbols did NOT match nse_scrips.csv:")
    for m in missing:
        print(f"  - {m}")
else:
    print("All symbols matched successfully.")