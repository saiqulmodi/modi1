from motilal_login import headers, auth_token
from intraday_watchlist import INTRADAY_SYMBOLS
from send_telegram import send_telegram_message
import yfinance as yf
import json
import pandas as pd
import time
import requests
from datetime import datetime
import os
import sys

LOCK_FILE = "intraday_monitor.lock"

if os.path.exists(LOCK_FILE):
    print("Previous run still in progress, skipping this run.")
    sys.exit(0)

with open(LOCK_FILE, "w") as f:
    f.write(str(datetime.now()))

print(f"\n===== RUN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")

VOLUME_THRESHOLD = 1.21   # 21% above 20-day avg volume
PRICE_MOVE_THRESHOLD = 10.0  # 10% move vs previous close

def load_watchlist_with_scripcodes(watchlist_path="watchlist.json", scrips_path="nse_scrips.csv"):
    with open(watchlist_path, "r") as f:
        watchlist = json.load(f)
    scrips = pd.read_csv(scrips_path, low_memory=False)
    equities = scrips[(scrips["exchangename"] == "NSE") & (scrips["optiontype"] == "EQ")]
    stocks = {}
    for entry in watchlist:
        symbol = entry["symbol"]
        match = equities[equities["scripshortname"] == symbol]
        if not match.empty:
            stocks[symbol] = int(match.iloc[0]["scripcode"])
        else:
            print(f"WARNING: no scripcode found for {symbol}, skipping")
    return stocks

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

stocks = load_intraday_scripcodes(INTRADAY_SYMBOLS)

ltp_url = "https://openapi.motilaloswal.com/rest/report/v3/getltpdata"
ltp_headers = headers.copy()
ltp_headers["Authorization"] = auth_token

alerts = []
first_stock_printed = False

for name, scripcode in stocks.items():
    body = {"clientcode": "", "exchange": "NSE", "scripcode": scripcode}
    time.sleep(0.5)
    response = requests.post(ltp_url, json=body, headers=ltp_headers)
    result = response.json()

    if result.get("status") != "SUCCESS":
        print(f"{name}: Error - {result.get('message')}")
        continue

    d = result["data"]

    if not first_stock_printed:
        print("Sample raw data (checking field names):", d)
        first_stock_printed = True

    ltp = d["ltp"] / 100
    prev_close = d["close"] / 100
    pct_change = ((ltp - prev_close) / prev_close) * 100 if prev_close else 0

    today_volume = d.get("volume")  # confirm this key exists from the raw print above

    hist = yf.Ticker(name + ".NS").history(period="30d")
    avg_volume_20d = hist["Volume"].tail(20).mean() if not hist.empty else None

    volume_ratio = None
    if today_volume and avg_volume_20d:
        volume_ratio = today_volume / avg_volume_20d

    ratio_str = f"{volume_ratio:.2f}x" if volume_ratio else "N/A"
    avg_str = f"{avg_volume_20d:.0f}" if avg_volume_20d else "N/A"
    print(f"{name}: LTP={ltp:.2f} ({pct_change:+.2f}%)  volume={today_volume}  avg20d={avg_str}  ratio={ratio_str}")

    if volume_ratio and volume_ratio >= VOLUME_THRESHOLD:
        alerts.append(f"Volume spike {name}: {volume_ratio:.2f}x avg (LTP {ltp:.2f})")

    if abs(pct_change) >= PRICE_MOVE_THRESHOLD:
        direction = "up" if pct_change > 0 else "down"
        alerts.append(f"Price {direction} {name}: {pct_change:.2f}% (LTP {ltp:.2f})")

print("\n--- Alerts triggered ---")
if alerts:
    for a in alerts:
        print(a)
        sent = send_telegram_message(a)
        if not sent:
            print(f"  (Telegram send failed for: {a})")
else:
    print("None")
if os.path.exists(LOCK_FILE):
    os.remove(LOCK_FILE)