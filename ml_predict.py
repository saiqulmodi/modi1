import yfinance as yf
import pandas as pd
import joblib

FEATURES = ["MA_trend", "RSI", "vol_ratio", "PEG", "ROE", "debt_to_equity", "revenue_growth",
            "MACD", "MACD_signal", "MACD_hist", "boll_width", "ATR"]

_model = None

def get_model():
    global _model
    if _model is None:
        _model = joblib.load("price_model.pkl")
    return _model

def get_ml_probability(symbol_ns):
    """symbol_ns should include the .NS suffix, e.g. 'INFY.NS'. Returns probability (0-1) or None on failure."""
    try:
        df = yf.download(symbol_ns, period="1y", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty:
            return None

        ticker = yf.Ticker(symbol_ns)
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

        latest = df.iloc[[-1]][FEATURES].fillna(0)
        model = get_model()
        prob = model.predict_proba(latest)[0][1]
        return round(float(prob), 3)
    except Exception as e:
        print(f"ML prediction error on {symbol_ns}: {e}")
        return None