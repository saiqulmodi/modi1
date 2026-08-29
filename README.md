# MODI1 — Intraday Stock Scoring, ML Predictions & Alerts

Scans a curated NSE watchlist (`intraday_watchlist.py`), scores each stock via
`stock_check.py` (technical + ML model), and sends Telegram/WhatsApp alerts
when a BUY/SELL verdict changes (`buy_sell_alert.py`). Includes a Streamlit
dashboard (`app.py`) and backtesting (`backtest.py`).

## Setup

None of the credential files below are committed to this repo — each is
gitignored because it holds live broker/messaging secrets. Recreate them
locally with your own values before running anything.

### `angel_login.py` (Angel One SmartAPI)

```python
import pyotp
import requests

# --- FILL THESE IN WITH YOUR OWN VALUES ---
CLIENT_ID = "your-angel-client-id"
PASSWORD = "your-angel-account-password"
API_KEY = "your-angel-api-key"
API_SECRET = "your-angel-api-secret"
TOTP_SECRET = "your-angel-totp-secret"
# -------------------------------------------

totp_code = pyotp.TOTP(TOTP_SECRET).now()

login_url = "https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword"
headers = {
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
    "clientcode": CLIENT_ID,
    "password": PASSWORD,
    "totp": totp_code,
}

try:
    response = requests.post(login_url, json=body, headers=headers, timeout=10)
    data = response.json()
except Exception as e:
    print(f"Angel One login failed (request/parse error): {e}")
    data = {}

if data.get("status"):
    auth_token = data["data"]["jwtToken"]
    feed_token = data["data"]["feedToken"]
else:
    auth_token = None
    feed_token = None

def get_auth_token():
    return auth_token
```

Get `API_KEY`/`API_SECRET` from the [Angel One SmartAPI portal](https://smartapi.angelbroking.com/),
and `TOTP_SECRET` from the QR code shown when enabling TOTP-based 2FA on your account.

### `motilal_login.py` (Motilal Oswal OpenAPI)

```python
import hashlib
import pyotp
import requests

# --- FILL THESE IN WITH YOUR OWN VALUES ---
USER_ID = "your-motilal-user-id"
PASSWORD = "your-motilal-account-password"
DOB = "DD/MM/YYYY"
API_KEY = "your-motilal-api-key"
TOTP_SECRET = "your-motilal-totp-secret"
API_SECRET = "your-motilal-api-secret"
# -------------------------------------------

hashed_password = hashlib.sha256((PASSWORD + API_KEY).encode()).hexdigest()
totp_code = pyotp.TOTP(TOTP_SECRET).now()

login_url = "https://openapi.motilaloswal.com/rest/login/v7/authdirectapi"
headers = {
    "Accept": "application/json",
    "User-Agent": "MOSL/V.1.1.0",
    "ApiKey": API_KEY,
    "apisecretkey": API_SECRET,
    "ClientLocalIp": "1.2.3.4",
    "ClientPublicIp": "1.2.3.4",
    "MacAddress": "00:00:00:00:00:00",
    "SourceId": "WEB",
    "vendorinfo": USER_ID,
    "osname": "Windows 10",
    "osversion": "10.0.19041",
    "devicemodel": "AHV",
    "manufacturer": "DELL",
    "productname": "MODI1",
    "productversion": "1.0",
    "browsername": "Chrome",
    "browserversion": "125.0",
}
body = {"userid": USER_ID, "password": hashed_password, "2FA": DOB, "totp": totp_code}

try:
    response = requests.post(login_url, json=body, headers=headers, timeout=10)
    data = response.json()
except Exception as e:
    print(f"Motilal login failed: {e}")
    data = {"status": "FAILED"}

if data.get("status") == "SUCCESS":
    auth_token = data.get("AuthToken")
else:
    auth_token = None

def get_auth_token():
    return auth_token
```

Get `API_KEY`/`API_SECRET` from the [Motilal Oswal OpenAPI developer portal](https://openapi.motilaloswal.com/).

### `send_telegram.py` (Telegram alerts)

```python
import requests

BOT_TOKEN = "your-bot-token-here"
CHAT_ID = "your-chat-id-here"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"Telegram send failed: {response.text}")
    return response.status_code == 200
```

Get a bot token from [@BotFather](https://t.me/BotFather), and your chat ID
by messaging your bot once and checking
`https://api.telegram.org/bot<TOKEN>/getUpdates`.

### `whatsapp_config.py` (WhatsApp alerts via Twilio, used by `send_alert.py`)

```python
TWILIO_ACCOUNT_SID = "your-twilio-account-sid"
TWILIO_AUTH_TOKEN = "your-twilio-auth-token"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"   # Twilio sandbox number, or your own
MY_WHATSAPP_NUMBER = "whatsapp:+91XXXXXXXXXX"    # your number, with country code
```

Get these from the [Twilio Console](https://console.twilio.com/) → Messaging
→ Try WhatsApp (sandbox) or your provisioned WhatsApp sender.

`twilio_creds.py`, `twilio_login.py`, and `test_whatsapp.py` are standalone,
optional one-off test scripts (not imported by anything else) — only
recreate them if you want to test a WhatsApp send directly, using the same
fields as `whatsapp_config.py` above.

**Status: WhatsApp alerting is currently not active** — Twilio requires a
paid subscription/sender approval to send outside the sandbox's limited
window, which isn't set up right now. `send_alert.py` calls will fail
silently in that path until a paid Twilio plan is in place; Telegram
alerting (`send_telegram.py`) is unaffected and is the working channel.

## Running

- `run_dashboard.bat` — launches `app.py` (Streamlit dashboard)
- `run_stock_check.bat` — runs `stock_check.py` (scores the watchlist, writes `watchlist.json`)
- `run_buy_sell_alert.bat` — runs `buy_sell_alert.py` (Telegram alert on verdict change)
- `run_check_intraday_log.bat` — runs `check_intraday_log.py`

`watchlist.json` **is** committed (not gitignored) — it's the daily
top-shortlist output and doubles as a trade history, since MODI1 trades real
money off it. `price_model.pkl` and `training_data.csv` are generated
locally via `train_model.py` / `build_dataset.py` and are gitignored.
