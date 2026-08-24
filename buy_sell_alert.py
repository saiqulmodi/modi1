"""
Sends a Telegram alert whenever a stock's combined BUY/SELL signal changes.

Backtesting (see backtest.py) showed the score-only verdict barely beats the
base rate (BUY: 26.2% vs 25.6% baseline win rate), while requiring the score
verdict AND the ML model to agree lifts the win rate to 30.4% with a higher
average return. So the base signal is:

  BUY         -> score verdict is BUY  AND  ml_prob >= 0.5
  SELL/AVOID  -> score verdict is SELL/AVOID  AND  ml_prob < 0.5
  HOLD        -> otherwise (including when the ML probability can't be
                 fetched, to avoid alerting on stale/partial data)

On top of that, a BUY/SELL is only actually alerted on if today's intraday
price action (see intraday_confirm.py) agrees: price on the right side of
VWAP, an Opening Range Breakout in the same direction, and volume confirming
(liquidity-tiered: 1.75x/1.5x the 20-day average for mega/large caps, or a
2-standard-deviation volume z-score for mid/small caps, since a flat ratio
means very different things depending on how liquid the stock normally is).
This avoids firing an alert purely off daily-bar data when nothing is
actually happening intraday. If intraday data can't be fetched (e.g. too
early in the session), the signal is held back rather than alerted on blind.

Only fires during market hours. Tracks last-seen signal per symbol in
buy_sell_alerted_state.json so it only alerts on a change, not every run.
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
import pandas as pd
import yfinance as yf
from send_telegram import send_telegram_message
from ml_predict import get_ml_probability
from angel_data import find_symbol_token
from intraday_confirm import get_intraday_confirmation

WATCHLIST_FILE = "watchlist.json"
STATE_FILE = "buy_sell_alerted_state.json"


def get_score_verdict(score):
    if score >= 4:
        return "BUY"
    elif score <= 1:
        return "SELL/AVOID"
    else:
        return "HOLD"


def get_combined_signal(score, ml_prob):
    if ml_prob is None:
        return "HOLD"
    score_verdict = get_score_verdict(score)
    if score_verdict == "BUY" and ml_prob >= 0.5:
        return "BUY"
    elif score_verdict == "SELL/AVOID" and ml_prob < 0.5:
        return "SELL/AVOID"
    else:
        return "HOLD"


if not os.path.exists(WATCHLIST_FILE):
    print("No watchlist.json found, skipping.")
    exit(0)

with open(WATCHLIST_FILE, "r") as f:
    watchlist = json.load(f)

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
else:
    state = {}

new_alerts = []
for entry in watchlist:
    symbol = entry["symbol"]
    ml_prob = get_ml_probability(symbol + ".NS")
    signal = get_combined_signal(entry["score"], ml_prob)

    intraday = None
    if signal in ("BUY", "SELL/AVOID"):
        token = find_symbol_token(symbol)
        if token:
            hist = yf.Ticker(symbol + ".NS").history(period="30d")
            daily_volume = hist["Volume"].tail(20) if not hist.empty else None
            intraday = get_intraday_confirmation(token, symbol, daily_volume)

        if intraday is None:
            print(f"{symbol}: {signal} signal held back, no intraday confirmation data available")
            signal = "HOLD"
        elif signal == "BUY" and not intraday["confirms_bullish"]:
            print(f"{symbol}: BUY signal held back, intraday action doesn't confirm ({intraday})")
            signal = "HOLD"
        elif signal == "SELL/AVOID" and not intraday["confirms_bearish"]:
            print(f"{symbol}: SELL/AVOID signal held back, intraday action doesn't confirm ({intraday})")
            signal = "HOLD"

    prev_signal = state.get(symbol)

    if signal != prev_signal:
        state[symbol] = signal
        if signal in ("BUY", "SELL/AVOID"):
            emoji = "🟢" if signal == "BUY" else "🔴"
            prob_str = f"{ml_prob:.0%}" if ml_prob is not None else "N/A"
            intraday_str = (
                f"VWAP {intraday['vwap']}, ORB {intraday['orb_breakout']}, "
                f"vol {intraday['volume_ratio']}x avg (needs {intraday['volume_threshold']}x, {intraday['liquidity_tier']})"
            )
            new_alerts.append(
                f"{emoji} {symbol} ({entry['name']}): {signal} "
                f"(score {entry['score']}, ml_prob {prob_str}, {intraday_str})"
            )

if new_alerts:
    CHUNK_SIZE = 40
    total_sent_ok = True
    for i in range(0, len(new_alerts), CHUNK_SIZE):
        chunk = new_alerts[i:i + CHUNK_SIZE]
        part_num = (i // CHUNK_SIZE) + 1
        total_parts = (len(new_alerts) + CHUNK_SIZE - 1) // CHUNK_SIZE
        header = f"*MODI1 Buy/Sell Signal* (part {part_num}/{total_parts})" if total_parts > 1 else "*MODI1 Buy/Sell Signal*"
        message = header + "\n" + "\n".join(chunk)
        sent = send_telegram_message(message)
        if not sent:
            total_sent_ok = False
    print(f"Sent alert for {len(new_alerts)} verdict change(s). Telegram sent: {total_sent_ok}")
else:
    print("No verdict changes to alert.")

with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)
