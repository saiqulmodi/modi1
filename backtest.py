"""
Backtests the two signal methods currently feeding MODI1's alerts, using the
5 years of historical data already collected in training_data.csv:

  1. Rule-based score/verdict (same logic as stock_check.py + get_verdict()):
     evaluated on the FULL history, since it's a fixed rule, not fit to data.

  2. ML model (price_model.pkl): evaluated ONLY on the chronological hold-out
     slice that train_model.py never fit on, so this is a fair out-of-sample
     check, not a look-at-your-own-training-data number.

  3. Combined (score verdict AND ml probability agree): same hold-out slice,
     to compare directly against method 2 on equal footing.

"label" in the data means: did the stock return >= 5% over the next 10
trading days. "future_return" is the actual forward return used for the
win-rate / average-return stats below.
"""

import pandas as pd
import joblib

FEATURES = ["MA_trend", "RSI", "vol_ratio", "PEG", "ROE", "debt_to_equity", "revenue_growth",
            "MACD", "MACD_signal", "MACD_hist", "boll_width", "ATR"]

df = pd.read_csv("training_data.csv")
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date").reset_index(drop=True)


def score_row(row):
    score = 0

    peg = row["PEG"]
    if pd.notna(peg):
        if peg < 1:
            score += 2
        elif peg < 2:
            score += 1

    if pd.notna(row["debt_to_equity"]):
        if row["debt_to_equity"] < 50:
            score += 1
        elif row["debt_to_equity"] > 100:
            score -= 1

    if pd.notna(row["ROE"]):
        if row["ROE"] > 0.15:
            score += 1
        elif row["ROE"] < 0.08:
            score -= 1

    if pd.notna(row["revenue_growth"]):
        if row["revenue_growth"] > 0.10:
            score += 1
        elif row["revenue_growth"] < 0:
            score -= 1

    score += 1 if row["MA_trend"] == 1 else -1

    if row["RSI"] < 30:
        score += 1

    return score


def get_verdict(score):
    if score >= 4:
        return "BUY"
    elif score <= 1:
        return "SELL/AVOID"
    else:
        return "HOLD"


def bucket_stats(sub_df, group_col):
    stats = sub_df.groupby(group_col).agg(
        n=("label", "size"),
        win_rate=("label", "mean"),
        avg_return=("future_return", "mean"),
        median_return=("future_return", "median"),
    )
    stats["win_rate"] = (stats["win_rate"] * 100).round(1)
    stats["avg_return"] = (stats["avg_return"] * 100).round(2)
    stats["median_return"] = (stats["median_return"] * 100).round(2)
    return stats


print(f"Total rows: {len(df)}  |  Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
print(f"Overall base rate (label==1): {df['label'].mean() * 100:.1f}%\n")

# ---------------------------------------------------------------------------
# 1. Rule-based score/verdict, full history
# ---------------------------------------------------------------------------
df["score"] = df.apply(score_row, axis=1)
df["verdict"] = df["score"].apply(get_verdict)

print("=== 1. Rule-based verdict (score logic), full 5y history ===")
print(bucket_stats(df, "verdict"))
print()

# ---------------------------------------------------------------------------
# 2. ML model, chronological hold-out only (same 80/20 split as train_model.py)
# ---------------------------------------------------------------------------
cutoff = int(len(df) * 0.8)
test_df = df.iloc[cutoff:].copy()

model = joblib.load("price_model.pkl")
X_test = test_df[FEATURES]
test_df["ml_prob"] = model.predict_proba(X_test)[:, 1]
test_df["ml_signal"] = (test_df["ml_prob"] >= 0.5).map({True: "ML_BUY", False: "ML_NO"})

print(f"=== 2. ML model, hold-out only ({test_df['Date'].min().date()} to {test_df['Date'].max().date()}, n={len(test_df)}) ===")
print(bucket_stats(test_df, "ml_signal"))
print()

test_df["ml_decile"] = pd.qcut(test_df["ml_prob"], 10, labels=False, duplicates="drop")
print("--- ML probability decile calibration (0=lowest confidence, 9=highest) ---")
print(bucket_stats(test_df, "ml_decile"))
print()

# ---------------------------------------------------------------------------
# 3. Combined: score verdict AND ML agree, same hold-out slice
# ---------------------------------------------------------------------------
test_df["combined_signal"] = "NO_SIGNAL"
test_df.loc[(test_df["verdict"] == "BUY") & (test_df["ml_prob"] >= 0.5), "combined_signal"] = "BOTH_BUY"
test_df.loc[(test_df["verdict"] == "SELL/AVOID") & (test_df["ml_prob"] < 0.5), "combined_signal"] = "BOTH_SELL"

print("=== 3. Combined (score verdict AND ml_prob agree), same hold-out slice ===")
print(bucket_stats(test_df, "combined_signal"))
