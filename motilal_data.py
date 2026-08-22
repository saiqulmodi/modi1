from send_telegram import send_telegram_message
import yfinance as yf
import json
import pandas as pd
import requests
import os
import sys
from motilal_login import headers, auth_token, API_KEY
from angel_data import get_angel_ltp
from datetime import datetime

# When this script's output is redirected to a log file (as the scheduled
# task does), Windows defaults stdout to the system codepage instead of
# UTF-8, which can't encode emoji like the momentum flag below and crashes
# the whole run with UnicodeEncodeError. Forcing UTF-8 here fixes that.
sys.stdout.reconfigure(encoding="utf-8")

print(f"\n===== RUN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")

def load_watchlist_with_scripcodes(watchlist_path="watchlist.json", scrips_path="nse_scrips.csv"):
    with open(watchlist_path, "r") as f:
        watchlist = json.load(f)

    scrips = pd.read_csv(scrips_path, low_memory=False)
    equities = scrips[(scrips["exchangename"] == "NSE") & (scrips["optiontype"] == "EQ")]
    stocks = {}
    fundamentals_scores = {}
    for entry in watchlist:
        symbol = entry["symbol"]
        match = equities[equities["scripshortname"] == symbol]
        if not match.empty:
            stocks[symbol] = int(match.iloc[0]["scripcode"])
            fundamentals_scores[symbol] = entry["score"]
        else:
            print(f"WARNING: no scripcode found for {symbol}, skipping")
    return stocks, fundamentals_scores

stocks, fundamentals_scores = load_watchlist_with_scripcodes()

def load_alt_momentum():
    if os.path.exists("alt_data_momentum.csv"):
        alt_df = pd.read_csv("alt_data_momentum.csv")
        return dict(zip(alt_df["symbol"], alt_df["Momentum (%)"]))
    return {}

alt_momentum = load_alt_momentum()

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_trend_signal(symbol):
    """Fetches 1y history from yfinance and returns (trend_score, signal_string)"""
    hist = yf.Ticker(symbol + ".NS").history(period="1y")
    if hist.empty or len(hist) <= 200:
        return 0, "not enough history"

    hist = hist.copy()
    hist["MA50"] = hist["Close"].rolling(window=50).mean()
    hist["MA200"] = hist["Close"].rolling(window=200).mean()
    hist["RSI"] = calculate_rsi(hist["Close"])
    hist["AvgVolume20"] = hist["Volume"].rolling(window=20).mean()

    latest_ma50 = hist["MA50"].iloc[-1]
    latest_ma200 = hist["MA200"].iloc[-1]
    latest_rsi = hist["RSI"].iloc[-1]
    latest_volume = hist["Volume"].iloc[-1]
    avg_volume_20 = hist["AvgVolume20"].iloc[-1]

    trend_score = 0
    if latest_ma50 > latest_ma200:
        trend_score += 1
        trend = "uptrend"
    else:
        trend_score -= 1
        trend = "downtrend"

    if latest_rsi > 70:
        rsi_note = "overbought"
        trend_score -= 1
    elif latest_rsi < 30:
        rsi_note = "oversold"
        trend_score += 1
    else:
        rsi_note = "neutral"

    volume_spike = latest_volume > 1.2 * avg_volume_20
    volume_note = "normal volume"
    if volume_spike:
        if trend == "uptrend":
            trend_score += 1
            volume_note = "volume spike confirms uptrend"
        else:
            trend_score -= 1
            volume_note = "volume spike confirms downtrend"

    return trend_score, f"{trend}, RSI {latest_rsi:.0f} ({rsi_note}), {volume_note}"

def get_verdict(combined_score):
    if combined_score >= 4:
        return "BUY"
    elif combined_score <= 1:
        return "SELL/AVOID"
    else:
        return "HOLD"

ltp_url = "https://openapi.motilaloswal.com/rest/report/v3/getltpdata"

ltp_headers = headers.copy()
ltp_headers["Authorization"] = auth_token

print("=== LIVE PRICES (Motilal Oswal) ===\n")

summary_lines = ["*MODI1 Daily Signals*"]

for name, scripcode in stocks.items():
    body = {
        "clientcode": "",
        "exchange": "NSE",
        "scripcode": scripcode
    }
    try:
        response = requests.post(ltp_url, json=body, headers=ltp_headers, timeout=10)
        result = response.json()
    except Exception:
        result = {"status": "FAILED", "message": "Motilal request/parse error"}

    if result.get("status") == "SUCCESS":
        d = result["data"]
        ltp = d["ltp"] / 100
        open_price = d["open"] / 100
        high = d["high"] / 100
        low = d["low"] / 100
        prev_close = d["close"] / 100
    else:
        angel_result = get_angel_ltp(name)
        if not angel_result or not angel_result.get("status"):
            print(f"{name}: Motilal and Angel One both failed, skipping")
            continue
        d = angel_result["data"]
        ltp = d["ltp"]
        open_price = d.get("open", ltp)
        high = d.get("high", ltp)
        low = d.get("low", ltp)
        prev_close = d["close"]

    change = ltp - prev_close
    pct_change = (change / prev_close) * 100 if prev_close else 0
    trend_score, signal = get_trend_signal(name)
    combined_score = fundamentals_scores.get(name, 0) + trend_score
    verdict = get_verdict(combined_score)

    momentum = alt_momentum.get(name)
    momentum_note = ""
    momentum_flag = ""
    if pd.notna(momentum):
        momentum_note = f" | search {momentum:+.0f}%"
        if momentum >= 100:
            momentum_flag = " 🔥"

    print(f"{name}: Rs.{ltp:.2f}  ({pct_change:+.2f}%)  [Open: {open_price:.2f}  High: {high:.2f}  Low: {low:.2f}]  | {signal}{momentum_note}  ==> {verdict} (combined score {combined_score:+d}){momentum_flag}")
    summary_lines.append(f"{name}: Rs.{ltp:.2f} -> {verdict} ({combined_score:+d}){momentum_note}{momentum_flag}")

# --- Send Telegram summary ---
summary_message = "\n".join(summary_lines)
sent = send_telegram_message(summary_message)
if sent:
    print("\nTelegram notification sent successfully")
else:
    print("\nTelegram notification failed")