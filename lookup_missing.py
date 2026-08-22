import pandas as pd

df = pd.read_csv("nse_scrips.csv")
nse_eq = df[(df["exchangename"] == "NSE") & (df["optiontype"] == "EQ")]

# loose substring guesses for each missing symbol's ticker
searches = {
    "DBREALTY": ["VALOR", "DBREAL", "REALTY"],
    "STLTECH": ["STER", "STLTEC", "STL"],
    "MTARTECH": ["MTAR"],
    "DIACABS": ["DIAMOND", "DIACAB", "DPIL"],
    "IDEAFORGE": ["IDEAFOR", "IDEA"],
    "ITCHOTEL": ["ITCHOT", "ITC"],
    "MINDA": ["MINDA"],
}

for wrong_symbol, keywords in searches.items():
    print(f"\n--- Looking for: {wrong_symbol} ---")
    pattern = "|".join(keywords)
    matches = nse_eq[nse_eq["scripshortname"].str.upper().str.contains(pattern, na=False)]
    if matches.empty:
        print("  No match found")
    else:
        print(matches[["scripshortname"]].to_string(index=False))