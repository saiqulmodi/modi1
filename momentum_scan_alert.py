"""
Catches stocks moving significantly today OUTSIDE the ~10-symbol
watchlist.json (which buy_sell_alert.py is scoped to) -- e.g. a stock up
10%+ while the broader market/Nifty is flat or down, which the watchlist-
scoped script structurally can never see since it never looks at those
symbols at all.

Deliberately a SEPARATE script from buy_sell_alert.py rather than folded
into it: this scans the full ~547-symbol INTRADAY_SYMBOLS universe (2y
history + today's candles per symbol), which is a much heavier scan than
buy_sell_alert.py's 10-symbol watchlist. buy_sell_alert.py runs every 15
minutes with MultipleInstances=IgnoreNew and only sends its alerts (incl.
the protective SELL exit) after its ENTIRE run completes -- folding this
scan in would risk delaying, or on a slow API day entirely skipping
(a run still in progress when the next 15-min trigger fires), those
time-sensitive core alerts. Runs on its own, less frequent schedule
instead (see register_momentum_scan_task.ps1) so it never competes with
or delays buy_sell_alert.py's responsiveness.

Alert-only, same as the relative-strength/trend-reversal signals in
buy_sell_alert.py -- never auto-traded, MODI4/place_order.py is not
imported here at all.
"""

from datetime import datetime as _dt

_now = _dt.now()
_market_start = _now.replace(hour=9, minute=15, second=0, microsecond=0)
_market_end = _now.replace(hour=15, minute=30, second=0, microsecond=0)
if _now < _market_start or _now > _market_end:
    print(f"Outside market hours ({_now.strftime('%H:%M:%S')}), skipping run.")
    exit()

import json
import os
import sys
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
from send_telegram import send_telegram_message
from angel_data import find_symbol_token
from intraday_confirm import get_intraday_confirmation
from intraday_watchlist import INTRADAY_SYMBOLS

sys.stdout.reconfigure(encoding="utf-8")

STATE_FILE = "momentum_scan_alerted_state.json"
_today_str = _now.strftime("%Y-%m-%d")

# Deliberately lower than app.py's dashboard scan (max_workers=8) -- this
# script runs independently, alongside the dashboard and buy_sell_alert.py,
# all hitting the same Motilal/Angel APIs; a lower concurrency here trades
# some of this script's own speed for less combined load/rate-limit risk
# across everything running at once.
MAX_WORKERS = 5

try:
    _nifty_hist = yf.Ticker("^NSEI").history(period="5d")
    _index_pct_change = (
        (_nifty_hist["Close"].iloc[-1] - _nifty_hist["Close"].iloc[-2])
        / _nifty_hist["Close"].iloc[-2] * 100
    ) if len(_nifty_hist) >= 2 else None
except Exception as e:
    print(f"Nifty fetch error: {e}")
    _index_pct_change = None

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
else:
    state = {}


def scan_one(symbol):
    token = find_symbol_token(symbol)
    if not token:
        return None
    try:
        hist = yf.Ticker(symbol + ".NS").history(period="2y")
    except Exception:
        return None
    intraday = get_intraday_confirmation(token, symbol, hist, index_pct_change=_index_pct_change)
    if intraday is None:
        return None
    return symbol, intraday


new_alerts = []
print(f"Scanning {len(INTRADAY_SYMBOLS)} symbols for momentum outside the watchlist...")
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    for result in executor.map(scan_one, INTRADAY_SYMBOLS):
        if result is None:
            continue
        symbol, intraday = result

        # Both signals below now also require volume_confirms (the same
        # Nifty50 1.5x / other 2x threshold as the main BUY/SELL gate) --
        # added by explicit request after alerts fired on volume well under
        # 2x, since relative-strength/trend-reversal weren't originally
        # volume-gated at all (matching buy_sell_alert.py's pre-existing
        # behavior for these same two signals, now changed there too).
        rel_key = f"{symbol}_relstrength"
        if (
            intraday.get("relative_strength") == "strength"
            and intraday.get("volume_confirms")
            and state.get(rel_key) != _today_str
        ):
            new_alerts.append(
                f"\U0001f7e2 {symbol}: RELATIVE STRENGTH vs Nifty (outside watchlist) -- "
                f"price {intraday['current_price']}, vol {intraday['volume_ratio']}x avg "
                f"(needs {intraday['volume_threshold']}x, {intraday['liquidity_tier']})\n"
                f"    Why: stock is up {intraday['symbol_pct_change']:+.2f}% today vs Nifty's "
                f"{intraday['index_pct_change']:+.2f}% -- meaningfully outperforming the broader market"
            )
            state[rel_key] = _today_str

        trend_key = f"{symbol}_trendreversal"
        if (
            intraday.get("trend_reversal_bullish")
            and intraday.get("volume_confirms")
            and state.get(trend_key) != _today_str
        ):
            new_alerts.append(
                f"\U0001f7e1 {symbol}: TREND REVERSAL BUY (outside watchlist, manual, not auto-traded) -- "
                f"current price {intraday['current_price']}, vol {intraday['volume_ratio']}x avg "
                f"(needs {intraday['volume_threshold']}x, {intraday['liquidity_tier']})\n"
                f"    Why: this stock had an extended 6+ day downtrend that just reversed today "
                f"(higher high AND higher low together) -- classic sign the downtrend has exhausted itself"
            )
            state[trend_key] = _today_str

if new_alerts:
    MAX_MESSAGE_CHARS = 3500
    HEADER_RESERVE = 60
    chunks = []
    current_chunk, current_len = [], 0
    for alert_text in new_alerts:
        if len(alert_text) > MAX_MESSAGE_CHARS - HEADER_RESERVE:
            alert_text = alert_text[:MAX_MESSAGE_CHARS - HEADER_RESERVE] + "... [truncated]"
        if current_len + len(alert_text) + 1 > MAX_MESSAGE_CHARS - HEADER_RESERVE and current_chunk:
            chunks.append(current_chunk)
            current_chunk, current_len = [], 0
        current_chunk.append(alert_text)
        current_len += len(alert_text) + 1
    if current_chunk:
        chunks.append(current_chunk)

    total_sent_ok = True
    for part_num, chunk in enumerate(chunks, start=1):
        header = f"*MODI1 Momentum Scan* (part {part_num}/{len(chunks)})" if len(chunks) > 1 else "*MODI1 Momentum Scan*"
        message = header + "\n" + "\n".join(chunk)
        sent = send_telegram_message(message)
        if not sent:
            total_sent_ok = False
    print(f"Sent {len(new_alerts)} alert(s) in {len(chunks)} message(s). Telegram sent: {total_sent_ok}")
else:
    print("No new momentum alerts.")

state = {k: v for k, v in state.items() if v == _today_str}
with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)
