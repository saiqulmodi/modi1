from angel_data import get_angel_ltp
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

# Stocks not present in Motilal's nse_scrips.csv - route directly to Angel One.
# Value is the Angel symbol suffix: "-EQ" normal, "-BE" = trade-to-trade
# (T2T stocks cannot be squared off intraday - alerts only, no auto-trade logic).
ANGEL_ONLY_SYMBOLS = {
    "DBREALTY": "-EQ",
    "IDEAFORGE": "-EQ",
    "STLTECH": "-BE",
    "MTARTECH": "-BE",
    "DIACABS": "-BE",
}

LOCK_FILE = "intraday_monitor.lock"
STALE_MINUTES = 15

if os.path.exists(LOCK_FILE):
    lock_age_seconds = time.time() - os.path.getmtime(LOCK_FILE)
    if lock_age_seconds < STALE_MINUTES * 60:
        print("Previous run still in progress, skipping this run.")
        sys.exit(0)
    else:
        print(f"Lock file is stale ({lock_age_seconds/60:.1f} min old), treating as crashed run and continuing.")

with open(LOCK_FILE, "w") as f:
    f.write(str(datetime.now()))

try:
    _run_start = datetime.now()
    print(f"\n===== RUN: {_run_start.strftime('%Y-%m-%d %H:%M:%S')} =====")

    VOLUME_THRESHOLD = 1.21   # 21% above 20-day avg volume
    PRICE_MOVE_THRESHOLD = 10.0  # 10% move vs previous close

    def load_intraday_scripcodes(symbols_list, scrips_path="nse_scrips.csv"):
        scrips = pd.read_csv(scrips_path, low_memory=False)
        equities = scrips[(scrips["exchangename"] == "NSE") & (scrips["optiontype"] == "EQ")]
        stocks = {}
        for symbol in symbols_list:
            if symbol in ANGEL_ONLY_SYMBOLS:
                continue  # handled separately below, not via Motilal scripcodes
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

    # ---- Main loop: Motilal-first, Angel One EQ fallback on failure ----
    for name, scripcode in stocks.items():
        body = {"clientcode": "", "exchange": "NSE", "scripcode": scripcode}
        time.sleep(0.5)

        try:
            response = requests.post(ltp_url, json=body, headers=ltp_headers, timeout=10)
            result = response.json()
        except Exception:
            result = {"status": "FAILED", "message": "Motilal request/parse error"}

        today_volume = None

        if result.get("status") == "SUCCESS":
            d = result["data"]
            if not first_stock_printed:
                print("Sample raw data (checking field names):", d)
                first_stock_printed = True
            ltp = d["ltp"] / 100
            prev_close = d["close"] / 100
            today_volume = d.get("volume")
        else:
            angel_result = get_angel_ltp(name)
            if not angel_result or not angel_result.get("status"):
                print(f"{name}: Error - Motilal failed ({result.get('message')}), Angel One fallback also failed")
                continue
            d = angel_result["data"]
            ltp = d["ltp"]
            prev_close = d["close"]
            print(f"{name}: using Angel One fallback (Motilal failed)")

        pct_change = ((ltp - prev_close) / prev_close) * 100 if prev_close else 0

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

    # ---- Angel-only loop: stocks missing from nse_scrips.csv (DBREALTY, IDEAFORGE, STLTECH, MTARTECH, DIACABS) ----
    # Price-move alerts only - Angel's LTP endpoint doesn't return volume data.
    for name, suffix in ANGEL_ONLY_SYMBOLS.items():
        time.sleep(0.5)
        angel_result = get_angel_ltp(name, suffix=suffix)
        if not angel_result or not angel_result.get("status"):
            print(f"{name}{suffix}: Angel One lookup failed")
            continue

        d = angel_result["data"]
        ltp = d["ltp"]
        prev_close = d["close"]
        pct_change = ((ltp - prev_close) / prev_close) * 100 if prev_close else 0

        print(f"{name}{suffix}: LTP={ltp:.2f} ({pct_change:+.2f}%)  [Angel-only, no volume data]")

        if abs(pct_change) >= PRICE_MOVE_THRESHOLD:
            direction = "up" if pct_change > 0 else "down"
            alerts.append(f"Price {direction} {name}{suffix}: {pct_change:.2f}% (LTP {ltp:.2f})")

    # Alerts from this run are sent as one consolidated message rather than
    # one-by-one with a sleep in between -- runs are already ~25 minutes
    # apart, which paces things out fine on its own, and sleeping here would
    # directly re-introduce the overlap-with-the-next-run risk we just fixed.
    print("\n--- Alerts triggered ---")
    if alerts:
        for a in alerts:
            print(a)

        MAX_MESSAGE_CHARS = 3500
        chunks, current_chunk, current_len = [], [], 0
        for a in alerts:
            if current_len + len(a) + 1 > MAX_MESSAGE_CHARS and current_chunk:
                chunks.append(current_chunk)
                current_chunk, current_len = [], 0
            current_chunk.append(a)
            current_len += len(a) + 1
        if current_chunk:
            chunks.append(current_chunk)

        total_sent_ok = True
        for chunk in chunks:
            sent = send_telegram_message("\n".join(chunk))
            if not sent:
                total_sent_ok = False
                print(f"  (Telegram send failed for {len(chunk)} alert(s))")
        print(f"Sent {len(alerts)} alert(s) in {len(chunks)} message(s). Telegram sent: {total_sent_ok}")
    else:
        print("None")

    _elapsed = (datetime.now() - _run_start).total_seconds()
    print(f"===== RUN COMPLETE: took {_elapsed/60:.1f} min =====")

finally:
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)