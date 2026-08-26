from ml_predict import get_ml_probability
from streamlit_autorefresh import st_autorefresh
import streamlit as st
import json
import pandas as pd
import requests
import os
import hashlib
import pyotp
from motilal_login import (
    headers, USER_ID, PASSWORD as MOTILAL_PASSWORD, DOB,
    API_KEY as MOTILAL_API_KEY, TOTP_SECRET as MOTILAL_TOTP_SECRET,
    login_url as MOTILAL_LOGIN_URL,
)
from angel_data import find_symbol_token
from angel_login import (
    headers as angel_headers, CLIENT_ID, PASSWORD as ANGEL_PASSWORD,
    TOTP_SECRET as ANGEL_TOTP_SECRET, login_url as ANGEL_LOGIN_URL,
)
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="MODI1 Dashboard", layout="wide")

# motilal_login.py/angel_login.py fetch their auth token ONCE, at import
# time. That's fine for short-lived scripts (Task Scheduler starts a fresh
# process every run), but this dashboard runs as a long-lived NSSM service
# that's only imported once per service start -- after a few hours the
# token dies and every live-price call fails silently, which is what was
# making prices and the Gainers/Losers section vanish. These re-run the
# same login fresh, cached for 1 hour so the dashboard keeps a live token
# indefinitely instead of running on an increasingly stale one.


@st.cache_resource(ttl=3600)
def get_fresh_motilal_token():
    hashed_password = hashlib.sha256((MOTILAL_PASSWORD + MOTILAL_API_KEY).encode()).hexdigest()
    totp_code = pyotp.TOTP(MOTILAL_TOTP_SECRET).now()
    body = {"userid": USER_ID, "password": hashed_password, "2FA": DOB, "totp": totp_code}
    try:
        response = requests.post(MOTILAL_LOGIN_URL, json=body, headers=headers, timeout=10)
        data = response.json()
    except Exception:
        return None
    return data.get("AuthToken") if data.get("status") == "SUCCESS" else None


@st.cache_resource(ttl=3600)
def get_fresh_angel_token():
    totp_code = pyotp.TOTP(ANGEL_TOTP_SECRET).now()
    body = {"clientcode": CLIENT_ID, "password": ANGEL_PASSWORD, "totp": totp_code}
    try:
        response = requests.post(ANGEL_LOGIN_URL, json=body, headers=angel_headers, timeout=10)
        data = response.json()
    except Exception:
        return None
    return data["data"]["jwtToken"] if data.get("status") else None


def get_angel_ltp_fresh(symbol, suffix="-EQ"):
    token = find_symbol_token(symbol, suffix)
    if not token:
        return None
    angel_token = get_fresh_angel_token()
    if not angel_token:
        return None
    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/getLtpData"
    ltp_headers = angel_headers.copy()
    ltp_headers["Authorization"] = f"Bearer {angel_token}"
    body = {"exchange": "NSE", "tradingsymbol": symbol + suffix, "symboltoken": token}
    try:
        response = requests.post(url, json=body, headers=ltp_headers, timeout=10)
        return response.json()
    except Exception:
        return None
# Full render (watchlist + gainers/losers) measured at ~50s; a 60s refresh
# was cutting it off mid-render before the Gainers/Losers section (rendered
# last) ever finished, so it silently never appeared. 150s gives real margin.
st_autorefresh(interval=150000, key="datarefresh")
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
    fresh_token = get_fresh_motilal_token()
    ltp_headers = headers.copy()
    ltp_headers["Authorization"] = fresh_token
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

    angel_result = get_angel_ltp_fresh(symbol)
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

def build_row(entry):
    symbol = entry["symbol"]
    scripcode = get_scripcode(symbol)
    ltp, pct_change = get_live_price(scripcode, symbol) if scripcode else (None, None)
    ml_prob = get_ml_probability(symbol + ".NS")
    momentum = alt_momentum.get(symbol)
    return {
        "symbol": symbol,
        "name": entry["name"],
        "score": entry["score"],
        "verdict": get_verdict(entry["score"]),
        "price": f"Rs.{ltp:.2f}" if ltp is not None else "N/A",
        "change": f"{pct_change:+.2f}%" if pct_change is not None else "N/A",
        "ml_probability": f"{ml_prob:.1%}" if ml_prob is not None else "N/A",
        "search_momentum": f"{momentum:+.1f}%" if pd.notna(momentum) else "N/A",
        "notes": ", ".join(entry["notes"])
    }

with ThreadPoolExecutor(max_workers=8) as executor:
    rows = list(executor.map(build_row, watchlist))

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
