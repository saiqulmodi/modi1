"""
Intraday confirmation layer for equities: VWAP position, Opening Range
Breakout (ORB), and relative volume, computed from today's 5-minute candles
via Angel One's historical candle API.

Used to gate buy_sell_alert.py's combined score+ML signal so it only fires
when today's actual intraday price action agrees with the direction, rather
than alerting purely on daily-bar fundamentals/trend data that may be stale
by the time the market opens.

Volume confirmation is liquidity-tiered, since a flat ratio means very
different things depending on how liquid a stock normally is:

  - Mega-cap (market cap >= 1,00,000 crore): needs today's volume >= 1.75x
    the 20-day average. These names are so liquid that even 1.75x is a real,
    unusual move.
  - Large-cap (market cap >= 20,000 crore): needs >= 1.5x the 20-day average.
  - Mid/small-cap (everything smaller): needs >= 2x the 20-day average --
    the highest bar of the three, since these stocks see noisier day-to-day
    volume swings and a smaller multiple wouldn't reliably separate a real
    move from ordinary noise.

Also checks a 3-day swing structure using daily bars:
  - Higher High + Higher Low (HH+HL) over the last 3 days (today's
    intraday high/low so far, vs. the prior two COMPLETE trading days)
    is an ADDITIONAL required condition for confirms_bullish -- on top of
    VWAP/ORB/volume, not instead of them.
  - Lower Low + Lower High (LL+LH) over the same window is exposed as
    swing_structure_bearish -- an INDEPENDENT protective-exit signal the
    caller can act on for any held position, regardless of what the
    score-based signal currently says.

Fails closed: if there isn't enough intraday data yet (e.g. right at market
open) or the candle fetch fails, get_intraday_confirmation() returns None
and the caller should treat that as "no confirmation" rather than guessing.
"""

import time

import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
from angel_login import auth_token, API_KEY

CANDLE_URL = "https://apiconnect.angelone.in/rest/secure/angelbroking/historical/v1/getCandleData"
ORB_MINUTES = 15

# Angel's historical-candle endpoint times out or drops the connection
# often enough under this scan's per-symbol call volume (thousands of
# occurrences in production logs) that a single attempt isn't reliable --
# short exponential backoff before giving up and returning None (still
# fails closed, same as before, just after trying a couple more times).
CANDLE_FETCH_MAX_ATTEMPTS = 3
CANDLE_FETCH_BACKOFF_BASE_SECONDS = 1

MEGA_CAP_MARKET_CAP = 1_000_000_000_000   # Rs. 1,00,000 crore
LARGE_CAP_MARKET_CAP = 200_000_000_000    # Rs. 20,000 crore
MEGA_CAP_VOLUME_RATIO = 1.75
LARGE_CAP_VOLUME_RATIO = 1.5
MID_SMALL_CAP_VOLUME_RATIO = 2.0


def _headers():
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "1.2.3.4",
        "X-ClientPublicIP": "1.2.3.4",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-PrivateKey": API_KEY,
    }


def get_today_candles(token, exchange="NSE", interval="FIVE_MINUTE"):
    today = datetime.now().strftime("%Y-%m-%d")
    body = {
        "exchange": exchange,
        "symboltoken": str(token),
        "interval": interval,
        "fromdate": f"{today} 09:15",
        "todate": f"{today} 15:30",
    }
    result = None
    for attempt in range(1, CANDLE_FETCH_MAX_ATTEMPTS + 1):
        try:
            response = requests.post(CANDLE_URL, json=body, headers=_headers(), timeout=10)
            result = response.json()
            break
        except Exception as e:
            if attempt < CANDLE_FETCH_MAX_ATTEMPTS:
                backoff = CANDLE_FETCH_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                print(f"Candle fetch error (attempt {attempt}/{CANDLE_FETCH_MAX_ATTEMPTS}, retrying in {backoff}s): {e}")
                time.sleep(backoff)
            else:
                print(f"Candle fetch error (attempt {attempt}/{CANDLE_FETCH_MAX_ATTEMPTS}, giving up): {e}")
                return None

    if not result.get("status") or not result.get("data"):
        return None

    df = pd.DataFrame(result["data"], columns=["timestamp", "open", "high", "low", "close", "volume"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


def get_volume_threshold(symbol):
    """Returns (tier, ratio_threshold) for the given symbol's market-cap tier."""
    try:
        market_cap = yf.Ticker(symbol + ".NS").info.get("marketCap")
    except Exception:
        market_cap = None

    if market_cap is None:
        return "unknown", MID_SMALL_CAP_VOLUME_RATIO
    elif market_cap >= MEGA_CAP_MARKET_CAP:
        return "mega_cap", MEGA_CAP_VOLUME_RATIO
    elif market_cap >= LARGE_CAP_MARKET_CAP:
        return "large_cap", LARGE_CAP_VOLUME_RATIO
    else:
        return "mid_small_cap", MID_SMALL_CAP_VOLUME_RATIO


def check_swing_structure(daily_history, today_high, today_low):
    """
    3-day swing structure: today's intraday high/low so far vs. the prior
    two COMPLETE trading days (daily_history should NOT include today --
    yfinance daily bars don't include the current incomplete day during
    market hours, so a plain .tail(2) is normally safe).

    Returns "bullish" (HH+HL: each day's high and low higher than the one
    before), "bearish" (LL+LH: each day's low and high lower than the one
    before), or None if there's not enough history or it's a mixed/no
    clear pattern.
    """
    if daily_history is None or len(daily_history) < 2:
        return None

    last_two = daily_history.tail(2)
    d1 = last_two.iloc[-1]   # yesterday (most recent complete day)
    d2 = last_two.iloc[-2]   # day before yesterday

    higher_highs = today_high > d1["High"] > d2["High"]
    higher_lows = today_low > d1["Low"] > d2["Low"]
    if higher_highs and higher_lows:
        return "bullish"

    lower_lows = today_low < d1["Low"] < d2["Low"]
    lower_highs = today_high < d1["High"] < d2["High"]
    if lower_lows and lower_highs:
        return "bearish"

    return None


def check_trend_reversal(daily_history, today_high, today_low, min_streak_days=6):
    """
    Trend-exhaustion reversal: an extended (6+ trading day) Lower-Low +
    Lower-High downtrend that then reverses -- today's high/low so far
    both come in HIGHER than the last day of that downtrend streak (a
    same-day Higher-High AND Higher-Low together, not just one or the
    other). Mirror for an extended Higher-High + Higher-Low uptrend that
    reverses into a same-day Lower-Low + Lower-High.

    This is a different, longer-horizon signal from check_swing_structure()
    above (which looks for 3-day CONTINUATION, not a 6+ day reversal) --
    the two are independent, not layered on each other.

    Returns "bullish_reversal", "bearish_reversal", or None.
    """
    if daily_history is None or len(daily_history) < min_streak_days + 1:
        return None

    highs = list(daily_history["High"]) + [today_high]
    lows = list(daily_history["Low"]) + [today_low]
    n = len(highs)

    down_streak = 0
    i = n - 2
    while i > 0 and highs[i] < highs[i - 1] and lows[i] < lows[i - 1]:
        down_streak += 1
        i -= 1

    up_streak = 0
    i = n - 2
    while i > 0 and highs[i] > highs[i - 1] and lows[i] > lows[i - 1]:
        up_streak += 1
        i -= 1

    latest_higher_high = highs[-1] > highs[-2]
    latest_higher_low = lows[-1] > lows[-2]
    latest_lower_high = highs[-1] < highs[-2]
    latest_lower_low = lows[-1] < lows[-2]

    if down_streak >= min_streak_days and latest_higher_high and latest_higher_low:
        return "bullish_reversal"
    if up_streak >= min_streak_days and latest_lower_high and latest_lower_low:
        return "bearish_reversal"
    return None


def check_52week_breakout(daily_history, today_high, today_low, window_days=252):
    """
    Fresh 52-week high (today's high exceeds the prior ~252-trading-day
    high) or 52-week low (today's low undercuts the prior 52-week low).
    Needs daily_history to cover at least close to a year -- returns None
    if there isn't enough (e.g. a recent IPO).

    Returns "high_breakout", "low_breakout", or None.
    """
    if daily_history is None or len(daily_history) < 200:
        return None
    window = daily_history.tail(window_days)
    week52_high = window["High"].max()
    week52_low = window["Low"].min()
    if today_high > week52_high:
        return "high_breakout"
    if today_low < week52_low:
        return "low_breakout"
    return None


def check_relative_strength(symbol_pct_change, index_pct_change, threshold=0.5):
    """
    Relative strength/weakness vs. the index (Nifty), independent of the
    stock's own absolute move -- e.g. Nifty down 1% but this stock up is
    unusually strong, worth flagging even if the stock's own move looks
    unremarkable in isolation. threshold is in percentage points.

    Returns "strength" (outperforming by >= threshold), "weakness"
    (underperforming by >= threshold), or None.
    """
    if symbol_pct_change is None or index_pct_change is None:
        return None
    diff = symbol_pct_change - index_pct_change
    if diff >= threshold:
        return "strength"
    if diff <= -threshold:
        return "weakness"
    return None


def check_squeeze_breakout(daily_history, today_close, bb_period=20, lookback_days=120, squeeze_percentile=20):
    """
    Bollinger Band squeeze breakout: the stock was sitting in an unusually
    tight trading range (band width in the bottom `squeeze_percentile`% of
    its own last `lookback_days`) as of yesterday, and today's price just
    broke out above yesterday's upper band (bullish) or below yesterday's
    lower band (bearish). A squeeze without today's breakout returns None
    -- this only fires on the actual breakout day, not the whole squeeze
    period.

    Returns "bullish_breakout", "bearish_breakout", or None.
    """
    if daily_history is None or len(daily_history) < bb_period + lookback_days:
        return None

    close = daily_history["Close"]
    mid = close.rolling(bb_period).mean()
    std = close.rolling(bb_period).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    band_width = (upper - lower) / mid

    recent_width = band_width.tail(lookback_days)
    if recent_width.isna().any():
        return None

    yesterday_width = recent_width.iloc[-1]
    threshold_width = recent_width.quantile(squeeze_percentile / 100)
    was_squeezed = yesterday_width <= threshold_width

    if not was_squeezed:
        return None

    yesterday_upper = upper.iloc[-1]
    yesterday_lower = lower.iloc[-1]
    if today_close > yesterday_upper:
        return "bullish_breakout"
    if today_close < yesterday_lower:
        return "bearish_breakout"
    return None


def check_volume_accumulation(daily_history, min_days=3, volume_ratio_threshold=1.5):
    """
    Consecutive-day volume accumulation/distribution: `min_days` (default
    3) straight COMPLETE trading days each showing volume >= threshold x
    the 20-day average, all closing in the same direction -- a different,
    slower signal from the existing single-day 2x volume check, aimed at
    catching sustained buying/selling rather than a one-day spike.

    Returns "accumulation" (up days), "distribution" (down days), or None.
    """
    if daily_history is None or len(daily_history) < min_days + 21:
        return None

    closes = daily_history["Close"]
    volumes = daily_history["Volume"]
    avg_volume_20d = volumes.rolling(20).mean()

    recent_closes = closes.tail(min_days + 1).values
    recent_volumes = volumes.tail(min_days).values
    recent_avg_volumes = avg_volume_20d.tail(min_days).values

    if pd.isna(recent_avg_volumes).any():
        return None

    up_days = 0
    down_days = 0
    for i in range(min_days):
        day_close = recent_closes[i + 1]
        prev_close = recent_closes[i]
        volume_confirms = recent_volumes[i] >= volume_ratio_threshold * recent_avg_volumes[i]
        if not volume_confirms:
            up_days = down_days = -999  # disqualify -- one weak-volume day breaks the streak
            break
        if day_close > prev_close:
            up_days += 1
        elif day_close < prev_close:
            down_days += 1

    if up_days == min_days:
        return "accumulation"
    if down_days == min_days:
        return "distribution"
    return None


def get_intraday_confirmation(token, symbol, daily_history, exchange="NSE", index_pct_change=None):
    """
    daily_history: the daily OHLCV DataFrame for the last ~30 days (e.g.
    yf.Ticker(symbol + ".NS").history(period="30d")) -- used both as the
    volume baseline and for the 3-day swing structure check.

    Returns a dict describing today's intraday state, or None if there
    isn't enough data yet to judge anything (too early in the day, or the
    candle fetch failed).
    """
    candles_per_orb = max(1, ORB_MINUTES // 5)
    df = get_today_candles(token, exchange=exchange)
    if df is None or len(df) < candles_per_orb + 1:
        return None

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    vwap = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
    current_price = df["close"].iloc[-1]
    current_vwap = vwap.iloc[-1]

    orb_high = df["high"].iloc[:candles_per_orb].max()
    orb_low = df["low"].iloc[:candles_per_orb].min()
    if current_price > orb_high:
        orb_breakout = "UP"
    elif current_price < orb_low:
        orb_breakout = "DOWN"
    else:
        orb_breakout = None

    today_volume = df["volume"].sum()
    daily_volume = daily_history["Volume"].tail(20) if daily_history is not None else None
    mean_volume = daily_volume.mean() if daily_volume is not None and len(daily_volume) else None
    volume_ratio = (today_volume / mean_volume) if mean_volume else None

    tier, ratio_threshold = get_volume_threshold(symbol)
    volume_confirms = volume_ratio is not None and volume_ratio >= ratio_threshold

    above_vwap = current_price > current_vwap

    today_high = df["high"].max()
    today_low = df["low"].min()
    swing_structure = check_swing_structure(daily_history, today_high, today_low)
    trend_reversal = check_trend_reversal(daily_history, today_high, today_low)
    week52 = check_52week_breakout(daily_history, today_high, today_low)
    squeeze = check_squeeze_breakout(daily_history, current_price)
    volume_trend = check_volume_accumulation(daily_history)

    symbol_pct_change = None
    if daily_history is not None and len(daily_history) and daily_history["Close"].iloc[-1]:
        prev_close = daily_history["Close"].iloc[-1]
        symbol_pct_change = (current_price - prev_close) / prev_close * 100
    relative_strength = check_relative_strength(symbol_pct_change, index_pct_change)

    return {
        "current_price": round(current_price, 2),
        "vwap": round(current_vwap, 2),
        "above_vwap": above_vwap,
        "orb_high": round(orb_high, 2),
        "orb_low": round(orb_low, 2),
        "orb_breakout": orb_breakout,
        "liquidity_tier": tier,
        "volume_ratio": round(volume_ratio, 2) if volume_ratio is not None else None,
        "volume_threshold": ratio_threshold,
        "volume_confirms": volume_confirms,
        "swing_structure": swing_structure,
        "swing_structure_bearish": swing_structure == "bearish",
        "confirms_bullish": above_vwap and orb_breakout == "UP" and volume_confirms and swing_structure == "bullish",
        "confirms_bearish": (not above_vwap) and orb_breakout == "DOWN" and volume_confirms,
        # Independent of everything above: a 6+ day trend-exhaustion
        "trend_reversal": trend_reversal,
        "trend_reversal_bullish": trend_reversal == "bullish_reversal",
        "trend_reversal_bearish": trend_reversal == "bearish_reversal",
        # Four more independent, alert-only signals:
        "week52_breakout": week52,
        "squeeze_breakout": squeeze,
        "volume_trend": volume_trend,
        "symbol_pct_change": round(symbol_pct_change, 2) if symbol_pct_change is not None else None,
        "index_pct_change": round(index_pct_change, 2) if index_pct_change is not None else None,
        "relative_strength": relative_strength,
    }
