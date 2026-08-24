import json
import yfinance as yf
import pandas as pd
from datetime import datetime
from intraday_watchlist import INTRADAY_SYMBOLS
print(f"\n===== RUN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")

# Scans the full watchlist universe (all sectors added over time: pharma/
# CDMO, textiles, hospitals, hospitality, auto ancillaries, data center,
# construction/housing/railway/cement/paint/tiles, NIFTY50+financials,
# plus the original screening list) rather than a separate, narrower
# hardcoded list -- still only the TOP_N below actually become tradeable
# candidates in watchlist.json, so this widens the pool of opportunities
# considered without changing how many are ever acted on.
symbols = [s + ".NS" for s in INTRADAY_SYMBOLS]

    

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_trend_signal(hist):
    """Returns (score_adjustment, notes_list) based on MA crossover + RSI"""
    notes = []
    score = 0
    if hist.empty or len(hist) <= 200:
        return 0, ["not enough price history"]

    hist = hist.copy()
    hist["MA50"] = hist["Close"].rolling(window=50).mean()
    hist["MA200"] = hist["Close"].rolling(window=200).mean()
    hist["RSI"] = calculate_rsi(hist["Close"])

    latest_ma50 = hist["MA50"].iloc[-1]
    latest_ma200 = hist["MA200"].iloc[-1]
    prev_ma50 = hist["MA50"].iloc[-2]
    prev_ma200 = hist["MA200"].iloc[-2]
    latest_rsi = hist["RSI"].iloc[-1]

    if prev_ma50 <= prev_ma200 and latest_ma50 > latest_ma200:
        score += 2
        notes.append("GOLDEN CROSS (bullish)")
    elif prev_ma50 >= prev_ma200 and latest_ma50 < latest_ma200:
        score -= 2
        notes.append("DEATH CROSS (bearish)")
    elif latest_ma50 > latest_ma200:
        score += 1
        notes.append("uptrend (50MA>200MA)")
    else:
        score -= 1
        notes.append("downtrend (50MA<200MA)")

    if latest_rsi > 70:
        notes.append(f"RSI {latest_rsi:.0f} (overbought)")
    elif latest_rsi < 30:
        score += 1
        notes.append(f"RSI {latest_rsi:.0f} (oversold)")
    else:
        notes.append(f"RSI {latest_rsi:.0f} (neutral)")

    return score, notes

# --- Check overall market trend first (Nifty 50) ---
print("=== MARKET CONTEXT (Nifty 50) ===\n")
nifty = yf.Ticker("^NSEI")
nifty_hist = nifty.history(period="1y")
market_score, market_notes = get_trend_signal(nifty_hist)
market_trend = "BULLISH" if market_score >= 0 else "BEARISH"
print(f"Nifty 50 is currently {market_trend}: {', '.join(market_notes)}\n")

# --- Screen individual stocks ---
results = []

for symbol in symbols:
    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        name = info.get("longName", symbol)
        pe_ratio = info.get("trailingPE")
        earnings_growth = info.get("earningsGrowth")
        revenue_growth = info.get("revenueGrowth")
        debt_to_equity = info.get("debtToEquity")
        roe = info.get("returnOnEquity")

        score = 0
        notes = []

        if pe_ratio and earnings_growth and earnings_growth > 0:
            peg_ratio = pe_ratio / (earnings_growth * 100)
            if peg_ratio < 1:
                score += 2
                notes.append(f"PEG {peg_ratio:.2f} (undervalued)")
            elif peg_ratio < 2:
                score += 1
                notes.append(f"PEG {peg_ratio:.2f} (fair)")
            else:
                notes.append(f"PEG {peg_ratio:.2f} (overvalued)")
        elif earnings_growth is not None and earnings_growth < 0:
            score -= 1
            notes.append("earnings shrinking")

        if debt_to_equity is not None:
            if debt_to_equity < 50:
                score += 1
                notes.append(f"low debt ({debt_to_equity:.0f})")
            elif debt_to_equity > 100:
                score -= 1
                notes.append(f"high debt ({debt_to_equity:.0f})")

        if roe is not None:
            if roe > 0.15:
                score += 1
                notes.append(f"strong ROE ({roe*100:.1f}%)")
            elif roe < 0.08:
                score -= 1
                notes.append(f"weak ROE ({roe*100:.1f}%)")

        if revenue_growth is not None:
            if revenue_growth > 0.10:
                score += 1
                notes.append(f"revenue growth {revenue_growth*100:.1f}%")
            elif revenue_growth < 0:
                score -= 1
                notes.append(f"revenue declining {revenue_growth*100:.1f}%")

        hist = stock.history(period="1y")
        trend_score, trend_notes = get_trend_signal(hist)
        score += trend_score
        notes.extend(trend_notes)

        results.append({
            "symbol": symbol,
            "name": name,
            "score": score,
            "notes": notes
        })

    except Exception as e:
        print(f"Skipping {symbol}: {e}")

results.sort(key=lambda x: x["score"], reverse=True)

print("=== STOCK SCREENER RESULTS (ranked) ===\n")
for r in results:
    print(f"{r['score']:+d}  {r['name']} ({r['symbol']})")
    print(f"     {', '.join(r['notes']) if r['notes'] else 'no data available'}")
    print()
# --- Export top N to watchlist.json for the daily price/signal script ---
TOP_N = 10

watchlist = []
for r in results[:TOP_N]:
    watchlist.append({
        "symbol": r["symbol"].replace(".NS", ""),
        "name": r["name"],
        "score": r["score"],
        "notes": r["notes"]
    })

with open("watchlist.json", "w") as f:
    json.dump(watchlist, f, indent=2)

print(f"\nSaved top {TOP_N} stocks to watchlist.json")