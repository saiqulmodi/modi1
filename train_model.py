import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib

df = pd.read_csv("training_data.csv")

features = ["MA_trend", "RSI", "vol_ratio", "PEG", "ROE", "debt_to_equity", "revenue_growth",
            "MACD", "MACD_signal", "MACD_hist", "boll_width", "ATR"]
X = df[features]
y = df["label"]

# Split chronologically-agnostic random split is fine for a first baseline
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")  # ensure chronological order
cutoff = int(len(df) * 0.8)

X_train, X_test = X.loc[df.index[:cutoff]], X.loc[df.index[cutoff:]]
y_train, y_test = y.loc[df.index[:cutoff]], y.loc[df.index[cutoff:]]

model = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42, class_weight="balanced")
model.fit(X_train, y_train)

preds = model.predict(X_test)

print("=== Classification Report ===")
print(classification_report(y_test, preds))
print("=== Confusion Matrix ===")
print(confusion_matrix(y_test, preds))

importances = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
print("\n=== Feature Importance ===")
print(importances)

joblib.dump(model, "price_model.pkl")
print("\nModel saved to price_model.pkl")