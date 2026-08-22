from angel_login import auth_token, API_KEY
import json
import requests

with open("angel_scrips.json", "r") as f:
    angel_scrips = json.load(f)


def find_symbol_token(symbol, suffix="-EQ"):
    """Find symboltoken for an NSE equity symbol (e.g. 'SBIN', suffix='-EQ' or '-BE')."""
    target = symbol + suffix
    for entry in angel_scrips:
        if entry.get("exch_seg") == "NSE" and entry.get("symbol") == target:
            return entry.get("token")
    return None


def get_angel_ltp(symbol, suffix="-EQ"):
    token = find_symbol_token(symbol, suffix)
    if not token:
        print(f"{symbol}{suffix}: symboltoken not found")
        return None
    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/getLtpData"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "1.2.3.4",
        "X-ClientPublicIP": "1.2.3.4",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-PrivateKey": API_KEY,
    }
    body = {
        "exchange": "NSE",
        "tradingsymbol": symbol + suffix,
        "symboltoken": token,
    }
    try:
        response = requests.post(url, json=body, headers=headers, timeout=10)
        result = response.json()
        return result
    except (requests.exceptions.RequestException, ValueError):
        return None


if __name__ == "__main__":
    test_symbols = ["SBIN", "RELIANCE", "TCS"]
    for s in test_symbols:
        result = get_angel_ltp(s)
        print(s, result)