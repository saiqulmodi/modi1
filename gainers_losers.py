from angel_data import get_angel_ltp
from motilal_login import headers, auth_token
from intraday_watchlist import INTRADAY_SYMBOLS
import pandas as pd
import time
import requests
import json
from datetime import datetime

def load_intraday_scripcodes(symbols_list, scrips_path="nse_scrips.csv"):
    scrips = pd.read_csv(scrips_path, low_memory=False)
    equities = scrips[(scrips["exchangename"] == "NSE") & (scrips["optiontype"] == "EQ")]
    stocks = {}
    for symbol in symbols_list:
        match = equities[equities["scripshortname"] == symbol]
        if not match.empty:
            stocks[symbol] = int(match.iloc[0]["scripcode"])
        else:
            print(f"WARNING: no scripcode found for {symbol}, skipping")
    return stocks

def get_all_changes():
    stocks = load_intraday_scripcodes(INTRADAY_SYMBOLS)

    ltp_url = "https://openapi.motilaloswal.com/rest/report/v3/getltpdata"
    ltp_headers = headers.copy()
    ltp_headers["Authorization"] = auth_token

    results = []

    for name, scripcode in stocks.items():
        body = {"clientcode": "", "exchange": "NSE", "scripcode": scripcode}
        time.sleep(0.5)

        try:
            response = requests.post(ltp_url, json=body, headers=ltp_headers, timeout=10)
            result = response.json()
        except Exception:
            result = {"status": "FAILED", "message": "Motilal request/parse error"}

        if result.get("status") == "SUCCESS":
            d = result["data"]
            ltp = d["ltp"] / 100
            prev_close = d["close"] / 100
        else:
            angel_result = get_angel_ltp(name)
            if not angel_result or not angel_result.get("status"):
                print(f"{name}: Motilal and Angel One both failed, skipping")
                continue
            d = angel_result["data"]
            ltp = d["ltp"]
            prev_close = d["close"]

        if not prev_close:
            continue

        pct_change = ((ltp - prev_close) / prev_close) * 100
        results.append({"symbol": name, "ltp": round(ltp, 2), "pct_change": round(pct_change, 2)})

    return results

if __name__ == "__main__":
    print(f"\n===== RUN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")
    all_changes = get_all_changes()
    ranked = sorted(all_changes, key=lambda x: x["pct_change"], reverse=True)

    top_gainers = ranked[:10]
    top_losers = ranked[-10:][::-1]

    print("\n--- TOP 10 GAINERS ---")
    for s in top_gainers:
        print(f"{s['symbol']}: {s['pct_change']:+.2f}%  (LTP {s['ltp']})")

    print("\n--- TOP 10 LOSERS ---")
    for s in top_losers:
        print(f"{s['symbol']}: {s['pct_change']:+.2f}%  (LTP {s['ltp']})")

    with open("gainers_losers.json", "w") as f:
        json.dump({"gainers": top_gainers, "losers": top_losers, "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)

    print("\nSaved to gainers_losers.json")