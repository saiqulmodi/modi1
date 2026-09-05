from angel_data import get_angel_ltp
from motilal_login import headers, auth_token
from intraday_watchlist import INTRADAY_SYMBOLS, ANGEL_ONLY_SYMBOLS
from intraday_confirm import get_volume_threshold, VOLUME_AVG_WINDOW_DAYS
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

    # Same Nifty50 (1.5x) / other (2x) tiering as intraday_confirm.py's
    # BUY/SELL volume gate -- this used to be a flat 1.21x for every
    # symbol, which meant non-Nifty50 stocks kept firing "volume spike"
    # alerts well under the 2x bar used everywhere else.
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

        # 90d (not 30d) so there's comfortably more than VOLUME_AVG_WINDOW_DAYS
        # (50) trading days once weekends/holidays are excluded -- this used
        # to average only the last 20 trading days, which doesn't match the
        # 50-day baseline intraday_confirm.py uses for the same volume gate
        # everywhere else.
        hist = yf.Ticker(name + ".NS").history(period="90d")
        avg_volume_50d = hist["Volume"].tail(VOLUME_AVG_WINDOW_DAYS).mean() if not hist.empty else None

        volume_ratio = None
        if today_volume and avg_volume_50d:
            volume_ratio = today_volume / avg_volume_50d

        ratio_str = f"{volume_ratio:.2f}x" if volume_ratio else "N/A"
        avg_str = f"{avg_volume_50d:.0f}" if avg_volume_50d else "N/A"
        print(f"{name}: LTP={ltp:.2f} ({pct_change:+.2f}%)  volume={today_volume}  avg50d={avg_str}  ratio={ratio_str}")

        tier, volume_threshold = get_volume_threshold(name)
        if volume_ratio and volume_ratio >= volume_threshold:
            alerts.append(f"Volume spike {name}: {volume_ratio:.2f}x avg (needs {volume_threshold}x, {tier}) (LTP {ltp:.2f})")

        if abs(pct_change) >= PRICE_MOVE_THRESHOLD:
            direction = "up" if pct_change > 0 else "down"
            alerts.append(f"Price {direction} {name}: {pct_change:.2f}% (LTP {ltp:.2f})")

    # ---- Angel-only loop: stocks missing as "EQ" from nse_scrips.csv (see ANGEL_ONLY_SYMBOLS in intraday_watchlist.py) ----
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