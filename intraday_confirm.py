"""
Intraday confirmation layer for equities: VWAP position, Opening Range
Breakout (ORB), and relative volume, computed from today's 5-minute candles
via Angel One's historical candle API.

Used to gate buy_sell_alert.py's combined score+ML signal so it only fires
when today's actual intraday price action agrees with the direction, rather
than alerting purely on daily-bar fundamentals/trend data that may be stale
by the time the market opens.

Volume confirmation is liquidity-tiered rather than a single flat ratio,
because mid/small-cap stocks have much noisier day-to-day volume than large
caps -- a flat threshold either lets small-cap noise "confirm" too easily or
is too strict for genuinely liquid names. So:

  - Mega-cap (market cap >= 1,00,000 crore): needs today's volume >= 1.75x
    the 20-day average. These names are so liquid that even 1.75x is a real,
    unusual move.
  - Large-cap (market cap >= 20,000 crore): needs >= 1.5x the 20-day average.
  - Everything smaller: a flat ratio doesn't mean much against these stocks'
    own volatility, so instead requires today's volume to be at least 2
    standard deviations above its own 20-day mean (a z-score), which
    self-adjusts to how noisy that specific stock's volume normally is.

Fails closed: if there isn't enough intraday data yet (e.g. right at market
open) or the candle fetch fails, get_intraday_confirmation() returns None
and the caller should treat that as "no confirmation" rather than guessing.
"""

import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
from angel_login import auth_token, API_KEY

CANDLE_URL = "https://apiconnect.angelone.in/rest/secure/angelbroking/historical/v1/getCandleData"
ORB_MINUTES = 15

MEGA_CAP_MARKET_CAP = 1_000_000_000_000   # Rs. 1,00,000 crore
LARGE_CAP_MARKET_CAP = 200_000_000_000    # Rs. 20,000 crore
MEGA_CAP_VOLUME_RATIO = 1.75
LARGE_CAP_VOLUME_RATIO = 1.5
MID_SMALL_CAP_ZSCORE = 2.0


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
    try:
        response = requests.post(CANDLE_URL, json=body, headers=_headers(), timeout=10)
        result = response.json()
    except Exception as e:
        print(f"Candle fetch error: {e}")
        return None

    if not result.get("status") or not result.get("data"):
        return None

    df = pd.DataFrame(result["data"], columns=["timestamp", "open", "high", "low", "close", "volume"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


def get_volume_threshold(symbol):
    """
    Returns (tier, ratio_threshold) where ratio_threshold is None for
    mid/small caps, since those use a z-score instead of a flat ratio.
    """
    try:
        market_cap = yf.Ticker(symbol + ".NS").info.get("marketCap")
    except Exception:
        market_cap = None

    if market_cap is None:
        return "unknown", None
    elif market_cap >= MEGA_CAP_MARKET_CAP:
        return "mega_cap", MEGA_CAP_VOLUME_RATIO
    elif market_cap >= LARGE_CAP_MARKET_CAP:
        return "large_cap", LARGE_CAP_VOLUME_RATIO
    else:
        return "mid_small_cap", None


def get_intraday_confirmation(token, symbol, daily_volume, exchange="NSE"):
    """
    daily_volume: pandas Series of the last ~20 trading days' daily volume
    (e.g. yf.Ticker(symbol + ".NS").history(period="30d")["Volume"].tail(20)),
    used as the baseline for both the flat-ratio and z-score volume checks.

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
    mean_volume = daily_volume.mean() if daily_volume is not None and len(daily_volume) else None
    std_volume = daily_volume.std() if daily_volume is not None and len(daily_volume) > 1 else None

    volume_ratio = (today_volume / mean_volume) if mean_volume else None
    z_score = ((today_volume - mean_volume) / std_volume) if std_volume else None

    tier, ratio_threshold = get_volume_threshold(symbol)
    if ratio_threshold is not None:
        volume_confirms = volume_ratio is not None and volume_ratio >= ratio_threshold
    else:
        volume_confirms = z_score is not None and z_score >= MID_SMALL_CAP_ZSCORE

    above_vwap = current_price > current_vwap

    return {
        "current_price": round(current_price, 2),
        "vwap": round(current_vwap, 2),
        "above_vwap": above_vwap,
        "orb_high": round(orb_high, 2),
        "orb_low": round(orb_low, 2),
        "orb_breakout": orb_breakout,
        "liquidity_tier": tier,
        "volume_ratio": round(volume_ratio, 2) if volume_ratio is not None else None,
        "volume_zscore": round(z_score, 2) if z_score is not None else None,
        "volume_confirms": volume_confirms,
        "confirms_bullish": above_vwap and orb_breakout == "UP" and volume_confirms,
        "confirms_bearish": (not above_vwap) and orb_breakout == "DOWN" and volume_confirms,
    }
