import requests
from motilal_login import headers, auth_token, API_KEY

# Add scrip codes for the stocks you want to track
# (NSE scrip codes - a few common large-caps to start)
stocks = {
    "RELIANCE": 2885,
    "TCS": 11536,
    "INFY": 1594,
    "HDFCBANK": 1333,
    "ITC": 1660,
}

ltp_url = "https://openapi.motilaloswal.com/rest/report/v3/getltpdata"

ltp_headers = headers.copy()
ltp_headers["Authorization"] = auth_token

print("=== LIVE PRICES (Motilal Oswal) ===\n")

for name, scripcode in stocks.items():
    body = {
        "clientcode": "",
        "exchange": "NSE",
        "scripcode": scripcode
    }
    response = requests.post(ltp_url, json=body, headers=ltp_headers)
    result = response.json()

    if result.get("status") == "SUCCESS":
        d = result["data"]
        ltp = d["ltp"] / 100
        open_price = d["open"] / 100
        high = d["high"] / 100
        low = d["low"] / 100
        prev_close = d["close"] / 100

        change = ltp - prev_close
        pct_change = (change / prev_close) * 100 if prev_close else 0

        print(f"{name}: Rs.{ltp:.2f}  ({pct_change:+.2f}%)  [Open: {open_price:.2f}  High: {high:.2f}  Low: {low:.2f}]")
    else:
        print(f"{name}: Error - {result.get('message')}")