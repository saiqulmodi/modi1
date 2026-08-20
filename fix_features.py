with open("build_dataset.py", "r") as f:
    content = f.read()

old = '''        df["vol_avg20"] = df["Volume"].rolling(20).mean()
        df["vol_ratio"] = df["Volume"] / df["vol_avg20"]
'''

new = old + '''
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
'''

if old not in content:
    print("ERROR: could not find the target block. No changes made.")
else:
    content = content.replace(old, new)
    with open("build_dataset.py", "w") as f:
        f.write(content)
    print("SUCCESS: build_dataset.py updated.")