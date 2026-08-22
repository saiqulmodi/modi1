from ml_predict import get_ml_probability

test_symbols = ["3MINDIA", "GLAND", "KAJARIACER", "RELIANCE", "SBIN"]

for sym in test_symbols:
    prob = get_ml_probability(sym + ".NS")
    print(f"{sym}: probability={prob}")