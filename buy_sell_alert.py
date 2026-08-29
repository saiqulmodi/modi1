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

Two more signals run independently of the above, regardless of the score
verdict:
  - Protective SELL (automated, held positions only): fires on either the
    existing 3-day Lower-Low+Lower-High continuation, OR a 6+ day
    Higher-High+Higher-Low uptrend that just reversed into a same-day
    Lower-Low+Lower-High (trend exhaustion). Either is enough to close
    the position for real, same as the score-based SELL/AVOID path.
  - Trend-reversal BUY (alert-only, never auto-traded): a 6+ day
    Lower-Low+Lower-High downtrend that just reversed into a same-day
    Higher-High+Higher-Low. Sent as a manual Telegram suggestion only.

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
from holdings import get_broker_holdings, get_broker_positions

WATCHLIST_FILE = "watchlist.json"
STATE_FILE = "buy_sell_alerted_state.json"
PROTECTIVE_EXIT_STATE_FILE = "protective_exit_state.json"
TREND_REVERSAL_STATE_FILE = "trend_reversal_alerted_state.json"
EXTRA_SIGNALS_STATE_FILE = "extra_signals_alerted_state.json"

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

if os.path.exists(TREND_REVERSAL_STATE_FILE):
    with open(TREND_REVERSAL_STATE_FILE, "r") as f:
        trend_reversal_state = json.load(f)
else:
    trend_reversal_state = {}

if os.path.exists(EXTRA_SIGNALS_STATE_FILE):
    with open(EXTRA_SIGNALS_STATE_FILE, "r") as f:
        extra_signals_state = json.load(f)
else:
    extra_signals_state = {}

_today_str = _now.strftime("%Y-%m-%d")

# Nifty's own daily % change, fetched once per run (not per-symbol) --
# needed for the relative-strength/weakness check below.
try:
    _nifty_hist = yf.Ticker("^NSEI").history(period="5d")
    _index_pct_change = (
        (_nifty_hist["Close"].iloc[-1] - _nifty_hist["Close"].iloc[-2])
        / _nifty_hist["Close"].iloc[-2] * 100
    ) if len(_nifty_hist) >= 2 else None
except Exception as e:
    print(f"Nifty fetch error: {e}")
    _index_pct_change = None

# Real Motilal demat holdings AND MTF positions, fetched once per run --
# this is what lets the protective LL+LH exit below cover stocks you
# already held before MODI4 existed or bought manually, not just positions
# MODI4 itself opened (risk_manager.get_open_position() only knows about
# its own trades). MTF buys are broker-funded/pledged and do NOT show up
# under DP holdings -- they're a separate "position", so both sources are
# needed to see the whole picture. Each fails closed to {} on error, so a
# fetch hiccup just means that side of the check is skipped this run, not
# that nothing is held.
broker_holdings = get_broker_holdings()
broker_positions = get_broker_positions()

new_alerts = []
for entry in watchlist:
    symbol = entry["symbol"]
    ml_prob = get_ml_probability(symbol + ".NS")
    signal = get_combined_signal(entry["score"], ml_prob)

    scripcode = get_motilal_scripcode(symbol)
    self_tracked = get_open_position(symbol)
    mtf_held = broker_positions.get(str(scripcode)) if scripcode is not None else None
    dp_held = broker_holdings.get(str(scripcode)) if scripcode is not None else None
    is_held = self_tracked is not None or mtf_held is not None or dp_held is not None

    # Intraday confirmation is fetched for every watchlist entry (only
    # ~10 symbols, cheap) rather than just when signal/holding requires
    # it, since the independent trend-reversal BUY check below needs it
    # for ALL candidates, not just the ones with an active score signal.
    # 2y (not 30d) so the 52-week and Bollinger-squeeze checks have enough
    # history -- still only ~10 symbols, so the extra fetch cost is small.
    token = find_symbol_token(symbol)
    intraday = None
    if token:
        hist = yf.Ticker(symbol + ".NS").history(period="2y")
        intraday = get_intraday_confirmation(token, symbol, hist, index_pct_change=_index_pct_change)

    if signal in ("BUY", "SELL/AVOID"):
        if intraday is None:
            print(f"{symbol}: {signal} signal held back, no intraday confirmation data available")
            signal = "HOLD"
        elif signal == "BUY" and not intraday["confirms_bullish"]:
            print(f"{symbol}: BUY signal held back, intraday action doesn't confirm ({intraday})")
            signal = "HOLD"
        elif signal == "SELL/AVOID" and not intraday["confirms_bearish"]:
            print(f"{symbol}: SELL/AVOID signal held back, intraday action doesn't confirm ({intraday})")
            signal = "HOLD"

    # Independent protective exit, for ANY currently held position --
    # regardless of what the score-based signal above says (a stock can be
    # structurally breaking down while the score/ML verdict still reads
    # HOLD or even BUY on stale daily data). Two independent triggers, either
    # one is enough: the existing 3-day Lower-Low+Lower-High continuation, or
    # a 6+ day Higher-High+Higher-Low uptrend that just reversed into a
    # Lower-Low+Lower-High day (trend exhaustion). Fires at most once per
    # symbol per day so a broker-holdings entry that hasn't settled/updated
    # yet by the next 5-minute cycle doesn't get sold again before the
    # position actually clears. SELL is only ever applied to a position
    # already held -- never a fresh short entry.
    if is_held and scripcode is not None and intraday is not None and protective_exit_state.get(symbol) != _today_str:
        exit_reasons = []
        if intraday.get("swing_structure_bearish"):
            exit_reasons.append(
                "3-day LL+LH: today's high/low so far are both lower than yesterday's, "
                "which were both lower than the day before -- a fresh 3-day breakdown pattern"
            )
        if intraday.get("trend_reversal_bearish"):
            exit_reasons.append(
                "TREND REVERSAL: this stock had an extended 6+ day uptrend (higher highs and "
                "higher lows each day) that just reversed today (lower high AND lower low together) "
                "-- classic sign the uptrend has exhausted itself"
            )

        if exit_reasons:
            # MTF close for a position MODI4 itself opened, or any pre-existing
            # MTF position the broker already shows as a margin position
            # (matches how it's actually held); SELLFROMDP only for a plain
            # DP/delivery holding with no margin position behind it.
            if self_tracked:
                qty, product_type = self_tracked["quantity"], "MTF"
            elif mtf_held:
                qty, product_type = mtf_held["quantity"], "MTF"
            else:
                qty, product_type = dp_held["quantity"], "SELLFROMDP"
            reason_str = " + ".join(exit_reasons)
            print(f"{symbol}: protective SELL ({reason_str}), qty {qty}, product_type {product_type}")
            place_order(
                symbol=symbol, scripcode=scripcode, exchange="NSE",
                transaction_type="SELL", quantity=qty,
                entry_price=intraday["current_price"],
                product_type=product_type,
            )
            protective_exit_state[symbol] = _today_str
            new_alerts.append(
                f"\U0001f534 {symbol} ({entry['name']}): AUTOMATED SELL executed -- "
                f"qty {qty}, price {intraday['current_price']}\n"
                f"    Why: {reason_str}"
            )

    # Independent, ALERT-ONLY (never auto-traded): a 6+ day Lower-Low+Lower-High
    # downtrend that just reversed into a Higher-High+Higher-Low day. Unlike
    # the score-based BUY above, this is purely a Telegram suggestion for you
    # to act on manually -- fires at most once per symbol per day.
    if (
        intraday is not None
        and intraday.get("trend_reversal_bullish")
        and trend_reversal_state.get(symbol) != _today_str
    ):
        new_alerts.append(
            f"\U0001f7e1 {symbol} ({entry['name']}): TREND REVERSAL BUY (manual, not auto-traded) -- "
            f"current price {intraday['current_price']}\n"
            f"    Why: this stock had an extended 6+ day downtrend (lower highs and lower lows "
            f"each day) that just reversed today (higher high AND higher low together) -- "
            f"classic sign the downtrend has exhausted itself"
        )
        trend_reversal_state[symbol] = _today_str

    # Four more independent, ALERT-ONLY signals (never auto-traded, same
    # caution as the trend-reversal BUY above) -- each fires at most once
    # per symbol per day.
    if intraday is not None:
        w52 = intraday.get("week52_breakout")
        w52_key = f"{symbol}_week52"
        if w52 and extra_signals_state.get(w52_key) != _today_str:
            label = "52-WEEK HIGH BREAKOUT" if w52 == "high_breakout" else "52-WEEK LOW BREAKDOWN"
            emoji = "\U0001f7e2" if w52 == "high_breakout" else "\U0001f534"
            why = (
                "today's high just broke above its highest point in the last 52 weeks -- fresh breakout momentum"
                if w52 == "high_breakout" else
                "today's low just broke below its lowest point in the last 52 weeks -- fresh breakdown, watch for further downside"
            )
            new_alerts.append(
                f"{emoji} {symbol} ({entry['name']}): {label} -- price {intraday['current_price']}\n"
                f"    Why: {why}"
            )
            extra_signals_state[w52_key] = _today_str

        squeeze = intraday.get("squeeze_breakout")
        squeeze_key = f"{symbol}_squeeze"
        if squeeze and extra_signals_state.get(squeeze_key) != _today_str:
            label = "VOLATILITY SQUEEZE BREAKOUT (bullish)" if squeeze == "bullish_breakout" else "VOLATILITY SQUEEZE BREAKDOWN (bearish)"
            emoji = "\U0001f7e2" if squeeze == "bullish_breakout" else "\U0001f534"
            why = (
                "the stock was sitting in an unusually tight, low-volatility range, and today it broke out upward -- squeezes often precede a sharp move"
                if squeeze == "bullish_breakout" else
                "the stock was sitting in an unusually tight, low-volatility range, and today it broke down -- squeezes often precede a sharp move"
            )
            new_alerts.append(
                f"{emoji} {symbol} ({entry['name']}): {label} -- price {intraday['current_price']}\n"
                f"    Why: {why}"
            )
            extra_signals_state[squeeze_key] = _today_str

        vol_trend = intraday.get("volume_trend")
        vol_trend_key = f"{symbol}_voltrend"
        if vol_trend and extra_signals_state.get(vol_trend_key) != _today_str:
            label = "VOLUME ACCUMULATION (3+ days up on high volume)" if vol_trend == "accumulation" else "VOLUME DISTRIBUTION (3+ days down on high volume)"
            emoji = "\U0001f7e2" if vol_trend == "accumulation" else "\U0001f534"
            why = (
                "3+ straight days closing higher, each on above-average volume -- looks like sustained buying, not a one-day spike"
                if vol_trend == "accumulation" else
                "3+ straight days closing lower, each on above-average volume -- looks like sustained selling, not a one-day spike"
            )
            new_alerts.append(
                f"{emoji} {symbol} ({entry['name']}): {label} -- price {intraday['current_price']}\n"
                f"    Why: {why}"
            )
            extra_signals_state[vol_trend_key] = _today_str

        rel_strength = intraday.get("relative_strength")
        rel_strength_key = f"{symbol}_relstrength"
        if rel_strength and extra_signals_state.get(rel_strength_key) != _today_str:
            label = "RELATIVE STRENGTH vs Nifty" if rel_strength == "strength" else "RELATIVE WEAKNESS vs Nifty"
            emoji = "\U0001f7e2" if rel_strength == "strength" else "\U0001f534"
            why = (
                f"stock is up {intraday['symbol_pct_change']:+.2f}% today vs Nifty's {intraday['index_pct_change']:+.2f}% -- meaningfully outperforming the broader market"
                if rel_strength == "strength" else
                f"stock is down {intraday['symbol_pct_change']:+.2f}% today vs Nifty's {intraday['index_pct_change']:+.2f}% -- meaningfully underperforming the broader market"
            )
            new_alerts.append(
                f"{emoji} {symbol} ({entry['name']}): {label}\n"
                f"    Why: {why}"
            )
            extra_signals_state[rel_strength_key] = _today_str

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
            why = (
                "fundamentals/trend score AND the ML model both agree, and today's actual intraday "
                "price action confirms it (right side of VWAP, opening-range breakout, and volume "
                "backing it up)"
            )
            new_alerts.append(
                f"{emoji} {symbol} ({entry['name']}): {signal} "
                f"(score {entry['score']}, ml_prob {prob_str}, {intraday_str})\n"
                f"    Why: {why}"
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
    # Chunk by character length, not item count -- a fixed 40-items-per-
    # message chunk can still exceed Telegram's 4096-char cap when alerts
    # are the longer multi-line kind (squeeze/volume/relative-strength
    # entries with a "Why:" line), which would silently drop the whole
    # message ("Bad Request: message is too long", nothing delivered).
    # Same bug, same fix, as MODI6's ma_rsi_alert.py.
    MAX_MESSAGE_CHARS = 3500
    HEADER_RESERVE = 60  # room for the "(part N/M)" header line
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
        header = f"*MODI1 Buy/Sell Signal* (part {part_num}/{len(chunks)})" if len(chunks) > 1 else "*MODI1 Buy/Sell Signal*"
        message = header + "\n" + "\n".join(chunk)
        sent = send_telegram_message(message)
        if not sent:
            total_sent_ok = False
    print(f"Sent alert for {len(new_alerts)} verdict change(s) in {len(chunks)} message(s). Telegram sent: {total_sent_ok}")
else:
    print("No verdict changes to alert.")

with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)

protective_exit_state = {k: v for k, v in protective_exit_state.items() if v == _today_str}
with open(PROTECTIVE_EXIT_STATE_FILE, "w") as f:
    json.dump(protective_exit_state, f, indent=2)

trend_reversal_state = {k: v for k, v in trend_reversal_state.items() if v == _today_str}
with open(TREND_REVERSAL_STATE_FILE, "w") as f:
    json.dump(trend_reversal_state, f, indent=2)

extra_signals_state = {k: v for k, v in extra_signals_state.items() if v == _today_str}
with open(EXTRA_SIGNALS_STATE_FILE, "w") as f:
    json.dump(extra_signals_state, f, indent=2)
