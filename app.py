from ml_predict import get_ml_probability
from streamlit_autorefresh import st_autorefresh
import streamlit as st
import json
import pandas as pd
import requests
import os
from motilal_login import headers, auth_token
from angel_data import get_angel_ltp
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="MODI1 Dashboard", layout="wide")
st_autorefresh(interval=60000, key="datarefresh")  # refreshes every 90 seconds
st.title("MODI1 - Stock Watchlist")

if st.button("Refresh"):
    st.rerun()

with open("watchlist.json", "r") as f:
    watchlist = json.load(f)

nse_scrips = pd.read_csv("nse_scrips.csv", low_memory=False)
equities = nse_scrips[(nse_scrips["exchangename"] == "NSE") & (nse_scrips["optiontype"] == "EQ")]

def load_alt_momentum():
    if os.path.exists("alt_data_momentum.csv"):
        alt_df = pd.read_csv("alt_data_momentum.csv")
        return dict(zip(alt_df["symbol"], alt_df["Momentum (%)"]))
    return {}

alt_momentum = load_alt_momentum()

def get_scripcode(symbol):
    match = equities[equities["scripshortname"] == symbol]
    if not match.empty:
        return int(match.iloc[0]["scripcode"])
    return None


def get_live_price(scripcode, symbol):
    ltp_url = "https://openapi.motilaloswal.com/rest/report/v3/getltpdata"
    ltp_headers = headers.copy()
    ltp_headers["Authorization"] = auth_token
    body = {"clientcode": "", "exchange": "NSE", "scripcode": scripcode}
    try:
        response = requests.post(ltp_url, json=body, headers=ltp_headers, timeout=10)
        result = response.json()
        if result.get("status") == "SUCCESS":
            d = result["data"]
            ltp = d["ltp"] / 100
            prev_close = d["close"] / 100
            pct_change = ((ltp - prev_close) / prev_close) * 100 if prev_close else 0
            return ltp, pct_change
    except Exception:
        pass

    angel_result = get_angel_ltp(symbol)
    if angel_result and angel_result.get("status"):
        d = angel_result["data"]
        ltp = d["ltp"]
        prev_close = d["close"]
        pct_change = ((ltp - prev_close) / prev_close) * 100 if prev_close else 0
        return ltp, pct_change

    return None, None
def get_verdict(score):
    if score >= 4:
        return "BUY"
    elif score <= 1:
        return "SELL/AVOID"
    else:
        return "HOLD"

rows = []
for entry in watchlist:
    symbol = entry["symbol"]
    scripcode = get_scripcode(symbol)
    ltp, pct_change = get_live_price(scripcode, symbol) if scripcode else (None, None)
    ml_prob = get_ml_probability(symbol + ".NS")
    momentum = alt_momentum.get(symbol)
    rows.append({
        "symbol": symbol,
        "name": entry["name"],
        "score": entry["score"],
        "verdict": get_verdict(entry["score"]),
        "price": f"Rs.{ltp:.2f}" if ltp is not None else "N/A",
        "change": f"{pct_change:+.2f}%" if pct_change is not None else "N/A",
        "ml_probability": f"{ml_prob:.1%}" if ml_prob is not None else "N/A",
        "search_momentum": f"{momentum:+.1f}%" if pd.notna(momentum) else "N/A",
        "notes": ", ".join(entry["notes"])
    })
df = pd.DataFrame(rows)

def color_verdict(row):
    if row["verdict"] == "BUY":
        color = "background-color: #d4f7dc"
    elif row["verdict"] == "SELL/AVOID":
        color = "background-color: #f7d4d4"
    else:
        color = "background-color: #f7f0d4"
    return [color] * len(row)

st.subheader("Top Ranked Stocks - Live")
styled_df = df.style.apply(color_verdict, axis=1)
st.dataframe(styled_df, width="stretch", hide_index=True)

FULL_UNIVERSE = [
    "MARKSANS", "CARYSIL", "TECHM", "LAURUSLABS", "GLAND", "NETWEB", "POLYCAB",
    "LODHA", "HINDCOPPER", "NATIONALUM", "LUMAXTECH", "GRSE", "APOLLOHOSP",
    "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "EICHERMOT", "HINDALCO", "ICICIBANK",
    "NESTLEIND", "ONGC", "SHRIRAMFIN", "SBIN", "SUNPHARMA", "DIVISLAB", "ANANTRAJ",
    "SOMANYCERA", "ADANIPORTS", "COALINDIA", "ETERNAL", "INDUSINDBK", "JSWSTEEL",
    "JIOFIN", "TATASTEEL", "GOPAL", "SANDUMA", "HINDZINC", "SAGILITY",
    "INDHOTEL", "BAJFINANCE", "GRASIM", "HDFCBANK", "KOTAKBANK", "TCS", "TITAN",
    "WIPRO", "PPLPHARMA", "BOMDYEING", "AJMERA", "GMRAIRPORT", "SUPRAJIT",
    "MAZDOCK", "ADANIENT", "BEL", "BHARTIARTL", "CIPLA", "HCLTECH", "HDFCLIFE",
    "INFY", "LT", "M&M", "TATACONSUM", "TRENT", "ULTRACEMCO", "ASTRAL", "ICIL",
    "MOIL", "HEROMOTOCO", "HINDUNILVR", "MARUTI", "RELIANCE", "SBILIFE", "TMCV",
    "ANTHEM", "TECHNOE", "HUDCO", "LEMONTREE", "RHIM", "APLAPOLLO", "BAJAJFINSV",
    "SYNGENE", "GOKEX", "DRREDDY", "ITC", "COHANCE", "NTPC", "POWERGRID",
    "SIGNATURE", "BRIGADE", "TMPV",
]

def fetch_one(symbol):
    scripcode = get_scripcode(symbol)
    if not scripcode:
        return None
    ltp, pct_change = get_live_price(scripcode, symbol)
    if ltp is not None and pct_change is not None:
        return {"symbol": symbol, "price": ltp, "change": pct_change}
    return None

def get_all_live_prices(symbols):
    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for result in executor.map(fetch_one, symbols):
            if result is not None:
                results.append(result)
    return results

all_prices = get_all_live_prices(FULL_UNIVERSE)
gainers = sorted(all_prices, key=lambda x: x["change"], reverse=True)[:10]
losers = sorted(all_prices, key=lambda x: x["change"])[:10]

gainers_df = pd.DataFrame(gainers)
losers_df = pd.DataFrame(losers)

def highlight_gain(row):
    return ["background-color: #1e5631; color: #ffffff; font-weight: 600"] * len(row)

def highlight_loss(row):
    return ["background-color: #7a1f1f; color: #ffffff; font-weight: 600"] * len(row)

st.subheader("Top 10 Gainers")
if not gainers_df.empty:
    st.dataframe(
        gainers_df.style.apply(highlight_gain, axis=1).format({"price": "Rs.{:.2f}", "change": "{:+.2f}%"}),
        hide_index=True, width=400
    )

st.subheader("Top 10 Losers")
if not losers_df.empty:
    st.dataframe(
        losers_df.style.apply(highlight_loss, axis=1).format({"price": "Rs.{:.2f}", "change": "{:+.2f}%"}),
        hide_index=True, width=400
    )
