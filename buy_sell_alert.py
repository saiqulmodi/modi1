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
import sys
import pandas as pd
import yfinance as yf
from send_telegram import send_telegram_message
from ml_predict import get_ml_probability
from angel_data import find_symbol_token
from intraday_confirm import get_intraday_confirmation

# MODI4: automated order placement (still DRY_RUN=True there -- no real
# orders are possible until that's explicitly flipped off). Order execution
# goes through Motilal (that's where the real trading account is); Angel
# above is only used for intraday candle confirmation, unchanged.
sys.path.insert(0, r"C:\Users\saiqu\Projects\MODI4")
from place_order import place_order
from risk_manager import calculate_quantity, get_open_position
from holdings import get_broker_holdings

WATCHLIST_FILE = "watchlist.json"
STATE_FILE = "buy_sell_alerted_state.json"
PROTECTIVE_EXIT_STATE_FILE = "protective_exit_state.json"

_nse_scrips = pd.read_csv("nse_scrips.csv", low_memory=False)
_equities = _nse_scrips[(_nse_scrips["exchangename"] == "NSE") & (_nse_scrips["optiontype"] == "EQ")]


def get_motilal_scripcode(symbol):
    match = _equities[_equities["scripshortname"] == symbol]
    return int(match.iloc[0]["scripcode"]) if not match.empty else None


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

if os.path.exists(PROTECTIVE_EXIT_STATE_FILE):
    with open(PROTECTIVE_EXIT_STATE_FILE, "r") as f:
        protective_exit_state = json.load(f)
else:
    protective_exit_state = {}

_today_str = _now.strftime("%Y-%m-%d")

# Real Motilal demat holdings, fetched once per run -- this is what lets
# the protective LL+LH exit below cover stocks you already held before
# MODI4 existed or bought manually, not just positions MODI4 itself opened
# (risk_manager.get_open_position() only knows about its own trades).
# Fails closed to {} on any error, so a fetch hiccup just means the
# broker-holdings side of the check is skipped for this run, not that
# nothing is held.
broker_holdings = get_broker_holdings()

new_alerts = []
for entry in watchlist:
    symbol = entry["symbol"]
    ml_prob = get_ml_probability(symbol + ".NS")
    signal = get_combined_signal(entry["score"], ml_prob)

    scripcode = get_motilal_scripcode(symbol)
    self_tracked = get_open_position(symbol)
    broker_held = broker_holdings.get(str(scripcode)) if scripcode is not None else None
    is_held = self_tracked is not None or broker_held is not None

    intraday = None
    if signal in ("BUY", "SELL/AVOID") or is_held:
        token = find_symbol_token(symbol)
        if token:
            hist = yf.Ticker(symbol + ".NS").history(period="30d")
            intraday = get_intraday_confirmation(token, symbol, hist)

        if intraday is None:
            if signal in ("BUY", "SELL/AVOID"):
                print(f"{symbol}: {signal} signal held back, no intraday confirmation data available")
                signal = "HOLD"
        elif signal == "BUY" and not intraday["confirms_bullish"]:
            print(f"{symbol}: BUY signal held back, intraday action doesn't confirm ({intraday})")
            signal = "HOLD"
        elif signal == "SELL/AVOID" and not intraday["confirms_bearish"]:
            print(f"{symbol}: SELL/AVOID signal held back, intraday action doesn't confirm ({intraday})")
            signal = "HOLD"

    # Independent protective exit: Lower-Low + Lower-High over the last 3
    # days, for ANY currently held position -- regardless of what the
    # score-based signal above says (a stock can be structurally breaking
    # down while the score/ML verdict still reads HOLD or even BUY on
    # stale daily data). Fires at most once per symbol per day so a
    # broker-holdings entry that hasn't settled/updated yet by the next
    # 5-minute cycle doesn't get sold again before the position actually
    # clears.
    if (
        is_held
        and scripcode is not None
        and intraday is not None
        and intraday.get("swing_structure_bearish")
        and protective_exit_state.get(symbol) != _today_str
    ):
        qty = self_tracked["quantity"] if self_tracked else broker_held["quantity"]
        # MTF close for a position MODI4 itself opened (matches how it was
        # bought); SELLFROMDP for a pre-existing/manual demat holding MODI4
        # never bought, since that's not tracked as an MTF/NORMAL position.
        product_type = "MTF" if self_tracked else "SELLFROMDP"
        print(f"{symbol}: protective SELL (swing structure LL+LH), qty {qty}, product_type {product_type}")
        place_order(
            symbol=symbol, scripcode=scripcode, exchange="NSE",
            transaction_type="SELL", quantity=qty,
            entry_price=intraday["current_price"],
            product_type=product_type,
        )
        protective_exit_state[symbol] = _today_str

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

            # MODI4 auto-trading (live for MODI1/NSE): BUY opens a new
            # rupee-sized position; SELL/AVOID only closes a position MODI4
            # is already tracking -- it never opens a fresh short (this
            # signal just means "bearish", not "you own this stock").
            # product_type=MTF: leveraged, broker-funded, carries forward
            # across days (not squared off same day) -- interest accrues on
            # the funded portion, which isn't reflected in our P&L tracking,
            # and not every stock is MTF-eligible (Motilal will reject those
            # orders safely, logged as live_failed).
            if scripcode is None:
                print(f"{symbol}: MODI4 order skipped, no Motilal scripcode found")
            elif signal == "BUY":
                qty = calculate_quantity(intraday["current_price"])
                place_order(
                    symbol=symbol, scripcode=scripcode, exchange="NSE",
                    transaction_type="BUY", quantity=qty,
                    entry_price=intraday["current_price"],
                    product_type="MTF",
                )
            elif signal == "SELL/AVOID" and get_open_position(symbol):
                held_qty = get_open_position(symbol)["quantity"]
                place_order(
                    symbol=symbol, scripcode=scripcode, exchange="NSE",
                    transaction_type="SELL", quantity=held_qty,
                    entry_price=intraday["current_price"],
                    product_type="MTF",
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

protective_exit_state = {k: v for k, v in protective_exit_state.items() if v == _today_str}
with open(PROTECTIVE_EXIT_STATE_FILE, "w") as f:
    json.dump(protective_exit_state, f, indent=2)
