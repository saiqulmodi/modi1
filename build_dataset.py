import yfinance as yf
import pandas as pd
import time

# Same Nifty 50 universe you already use in stock_check.py
symbols = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "ITC.NS", "AXISBANK.NS", "SUNPHARMA.NS", "BAJAJ-AUTO.NS",
    "ASIANPAINT.NS", "APOLLOHOSP.NS", "EICHERMOT.NS", "MARUTI.NS",
]

all_rows = []

for symbol in symbols:
    print(f"Fetching {symbol}...")
    try:
        df = yf.download(symbol, period="3y", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty:
            print(f"  No data for {symbol}, skipping.")
            continue
        if df.empty:
            print(f"  No data for {symbol}, skipping.")
            continue

        df["symbol"] = symbol
        # Fetch current fundamentals (approximation applied to all historical rows)
        ticker = yf.Ticker(symbol)
        info = ticker.info
        peg = info.get("pegRatio", None)
        roe = info.get("returnOnEquity", None)
        debt_to_equity = info.get("debtToEquity", None)
        revenue_growth = info.get("revenueGrowth", None)

        df["PEG"] = peg
        df["ROE"] = roe
        df["debt_to_equity"] = debt_to_equity
        df["revenue_growth"] = revenue_growth

        # Basic technical features
        df["MA50"] = df["Close"].rolling(50).mean()
        df["MA200"] = df["Close"].rolling(200).mean()
        df["MA_trend"] = (df["MA50"] > df["MA200"]).astype(int)  # 1 = golden cross zone

        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

        df["vol_avg20"] = df["Volume"].rolling(20).mean()
        df["vol_ratio"] = df["Volume"] / df["vol_avg20"]
        # MACD (12-day EMA - 26-day EMA, plus signal line)
        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = ema12 - ema26
        df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

        # Bollinger Band width (20-day, 2 std dev)
        boll_mid = df["Close"].rolling(20).mean()
        boll_std = df["Close"].rolling(20).std()
        df["boll_width"] = ((boll_mid + 2 * boll_std) - (boll_mid - 2 * boll_std)) / boll_mid

        # ATR (14-day Average True Range, volatility)
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift()).abs()
        low_close = (df["Low"] - df["Close"].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["ATR"] = true_range.rolling(14).mean()

        # Label: did price go up 5%+ over the NEXT 5 trading days?
        df["future_close"] = df["Close"].shift(-10)
        df["future_return"] = (df["future_close"] - df["Close"]) / df["Close"]
        df["label"] = (df["future_return"] >= 0.05).astype(int)

        all_rows.append(df)
        time.sleep(1)  # be polite to Yahoo Finance
    except Exception as e:
        print(f"  Error on {symbol}: {e}")

combined = pd.concat(all_rows)
# Only drop rows missing the core technical features (these are essential)
combined = combined.dropna(subset=["MA200", "RSI", "vol_ratio", "label"])

# Fill missing fundamentals with the median across all stocks (reasonable neutral guess)
for col in ["PEG", "ROE", "debt_to_equity", "revenue_growth"]:
    combined[col] = combined[col].fillna(combined[col].median())

combined.to_csv("training_data.csv")
print(f"\nSaved {len(combined)} rows to training_data.csv")
print(combined["label"].value_counts())