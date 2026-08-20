import yfinance as yf
import pandas as pd
import joblib

symbols = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "ITC.NS", "AXISBANK.NS", "SUNPHARMA.NS", "BAJAJ-AUTO.NS",
    "ASIANPAINT.NS", "APOLLOHOSP.NS", "EICHERMOT.NS", "MARUTI.NS",
    "ULTRACEMCO.NS", "TITAN.NS", "TATASTEEL.NS", "TECHM.NS", "TRENT.NS",
    "TATACONSUM.NS", "SBILIFE.NS", "SHRIRAMFIN.NS", "POWERGRID.NS", "ONGC.NS",
    "NTPC.NS", "NESTLEIND.NS", "MAXHEALTH.NS", "M&M.NS",
    "LT.NS", "KOTAKBANK.NS",  "JSWSTEEL.NS", "BHARTIARTL.NS",
    "JIOFIN.NS", "INDIGO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "HDFCLIFE.NS",
    "HCLTECH.NS", "GRASIM.NS", "ETERNAL.NS", "DRREDDY.NS",
    "COALINDIA.NS", "CIPLA.NS", "BAJAJFINSV.NS", "BEL.NS", 
    "BAJFINANCE.NS", "ADANIENT.NS", "ADANIPORTS.NS", "TMPV.NS", "WIPRO.NS",


]

model = joblib.load("price_model.pkl")

features = ["MA_trend", "RSI", "vol_ratio", "PEG", "ROE", "debt_to_equity", "revenue_growth",
            "MACD", "MACD_signal", "MACD_hist", "boll_width", "ATR"]

results = []

for symbol in symbols:
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty:
            continue

        ticker = yf.Ticker(symbol)
        info = ticker.info
        df["PEG"] = info.get("pegRatio", None)
        df["ROE"] = info.get("returnOnEquity", None)
        df["debt_to_equity"] = info.get("debtToEquity", None)
        df["revenue_growth"] = info.get("revenueGrowth", None)

        df["MA50"] = df["Close"].rolling(50).mean()
        df["MA200"] = df["Close"].rolling(200).mean()
        df["MA_trend"] = (df["MA50"] > df["MA200"]).astype(int)

        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

        df["vol_avg20"] = df["Volume"].rolling(20).mean()
        df["vol_ratio"] = df["Volume"] / df["vol_avg20"]

        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = ema12 - ema26
        df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

        boll_mid = df["Close"].rolling(20).mean()
        boll_std = df["Close"].rolling(20).std()
        df["boll_width"] = ((boll_mid + 2 * boll_std) - (boll_mid - 2 * boll_std)) / boll_mid

        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift()).abs()
        low_close = (df["Low"] - df["Close"].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["ATR"] = true_range.rolling(14).mean()

        latest = df.iloc[[-1]][features].fillna(0)
        prob = model.predict_proba(latest)[0][1]

        results.append({"symbol": symbol, "probability": round(prob, 3)})
    except Exception as e:
        print(f"Error on {symbol}: {e}")

results_df = pd.DataFrame(results).sort_values("probability", ascending=False)
print(results_df.to_string(index=False))