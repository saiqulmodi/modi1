"""
Recurring (daily, ~10:30am) consolidated health check covering: the
Nifty50 volume-threshold config, auto-trading being disabled, buy_sell_
alert.py and momentum_scan_alert.py actually running, the dashboard
service, the yfinance version (crumb-error fix from 2026-09-02), and the
Angel One token cache (login-storm fix from 2026-09-02). Read-only --
doesn't modify any state, doesn't place orders. Sends one Telegram
summary daily so a regression in any of these gets caught on an ongoing
basis, not just on the day someone happened to schedule a one-off check.
"""

import sys
import os
import re
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

from send_telegram import send_telegram_message

_today_str = datetime.now().strftime("%Y-%m-%d")
lines = [f"[MODI1] Morning health check -- {datetime.now().strftime('%Y-%m-%d %H:%M')}"]


def _read_tail(path, max_bytes=200_000):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - max_bytes))
        return f.read()


def _modified_recently(path, within_minutes):
    # Neither buy_sell_alert.py nor momentum_scan_alert.py timestamp their
    # print() output, so "did this run today" can't be answered by
    # searching the log text -- file mtime is the only reliable signal.
    if not os.path.exists(path):
        return False
    return (time.time() - os.path.getmtime(path)) < within_minutes * 60


# 1. buy_sell_alert.py ran recently (every 15 min during market hours), no
#    unhandled tracebacks
log_path = "logs/buy_sell_alert.log"
log = _read_tail(log_path)
if log is None:
    lines.append("\n1. buy_sell_alert.py: ⚠️ no log file found")
else:
    ran_recently = _modified_recently(log_path, within_minutes=20)
    has_traceback = "Traceback (most recent call last)" in log
    status = "OK" if ran_recently and not has_traceback else "⚠️ CHECK"
    lines.append(f"\n1. buy_sell_alert.py: {status}")
    lines.append(f"   ran in last 20 min: {ran_recently}, traceback found: {has_traceback}")

# 2. momentum_scan_alert.py ran recently (every 30 min), no tracebacks
log_path = "logs/momentum_scan_alert.log"
log = _read_tail(log_path)
if log is None:
    lines.append("\n2. momentum_scan_alert.py: ⚠️ no log file yet (scheduled task may not have fired)")
else:
    ran_recently = _modified_recently(log_path, within_minutes=35)
    has_traceback = "Traceback (most recent call last)" in log
    scan_count = len(re.findall(r"Scanning \d+ symbols", log))
    status = "OK" if ran_recently and not has_traceback else "⚠️ CHECK"
    lines.append(f"\n2. momentum_scan_alert.py: {status}")
    lines.append(f"   ran in last 35 min: {ran_recently}, scan cycles seen (log so far): {scan_count}, traceback found: {has_traceback}")

# 3. MODI1Dashboard: is the service still up, any errors beyond known
#    Yahoo Finance crumb noise (unrelated, pre-existing, non-fatal)
try:
    import subprocess
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "(Get-Service MODI1Dashboard).Status"],
        capture_output=True, text=True, timeout=15,
    )
    service_status = result.stdout.strip()
except Exception as e:
    service_status = f"check failed: {e}"
lines.append(f"\n3. MODI1Dashboard service: {service_status}")

# 4. Safety check: auto-trading must still be disabled (LIVE_EXCHANGES empty)
modi4_path = r"C:\Users\saiqu\Projects\MODI4\place_order.py"
if os.path.exists(modi4_path):
    with open(modi4_path, "r", encoding="utf-8") as f:
        content = f.read()
    live_exchanges_disabled = "LIVE_EXCHANGES = set()" in content
    status = "OK -- alerts only" if live_exchanges_disabled else "🔴 AUTO-TRADING MAY BE LIVE -- CHECK IMMEDIATELY"
    lines.append(f"\n4. Auto-trading safety switch: {status}")
else:
    lines.append("\n4. Auto-trading safety switch: ⚠️ MODI4/place_order.py not found")

# 5. Volume threshold config still intact (Nifty50 2-tier system)
intraday_confirm_path = "intraday_confirm.py"
if os.path.exists(intraday_confirm_path):
    with open(intraday_confirm_path, "r", encoding="utf-8") as f:
        content = f.read()
    has_nifty50 = "NIFTY_50_SYMBOLS" in content and "NIFTY50_VOLUME_RATIO = 1.5" in content
    has_50day = "VOLUME_AVG_WINDOW_DAYS = 50" in content
    status = "OK" if (has_nifty50 and has_50day) else "⚠️ CHECK -- settings may have reverted"
    lines.append(f"\n5. Volume threshold config: {status}")
else:
    lines.append("\n5. Volume threshold config: ⚠️ intraday_confirm.py not found")

# 6. yfinance version -- the 2026-09-02 crumb-error fix was an upgrade,
#    not a code change, so nothing stops a future environment update from
#    silently reverting it.
try:
    import yfinance
    yf_version = yfinance.__version__
    yf_ok = tuple(int(p) for p in yf_version.split(".")[:2]) >= (1, 7)
    status = "OK" if yf_ok else f"⚠️ CHECK -- {yf_version} may have the crumb-error bug again"
    lines.append(f"\n6. yfinance version ({yf_version}): {status}")
except Exception as e:
    lines.append(f"\n6. yfinance version: ⚠️ check failed: {e}")

# 7. Angel One token cache -- confirms the 2026-09-02 login-storm fix is
#    actually being used (a missing/stale cache means every script is back
#    to logging in fresh on every run).
cache_path = "angel_token_cache.json"
if os.path.exists(cache_path):
    age_minutes = (time.time() - os.path.getmtime(cache_path)) / 60
    status = "OK" if age_minutes < 90 else f"⚠️ CHECK -- last refreshed {age_minutes:.0f} min ago"
    lines.append(f"\n7. Angel token cache: {status} (age: {age_minutes:.0f} min)")
else:
    lines.append("\n7. Angel token cache: ⚠️ file not found -- caching may not be active")

# 8. Live broker-side connectivity -- a token existing isn't proof it
#    actually works (Angel invalidates sessions, Motilal tokens expire).
#    Makes one real LTP call to each broker for RELIANCE, the same way
#    app.py/buy_sell_alert.py do it. Read-only, no order-related endpoints
#    touched.
try:
    import pandas as pd
    import requests as _requests
    from angel_data import find_symbol_token
    from angel_login import auth_token as _angel_token, headers as _angel_headers

    angel_ok = False
    token = find_symbol_token("RELIANCE")
    if token and _angel_token:
        ltp_headers = _angel_headers.copy()
        ltp_headers["Authorization"] = f"Bearer {_angel_token}"
        resp = _requests.post(
            "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/getLtpData",
            json={"exchange": "NSE", "tradingsymbol": "RELIANCE-EQ", "symboltoken": token},
            headers=ltp_headers, timeout=10,
        )
        angel_ok = bool(resp.json().get("status"))
except Exception as e:
    angel_ok = False
    angel_err = str(e)
else:
    angel_err = None

try:
    from motilal_login import headers as _motilal_headers, login_url as _motilal_login_url, USER_ID, PASSWORD, API_KEY, DOB, TOTP_SECRET
    import hashlib, pyotp
    scrips = pd.read_csv("nse_scrips.csv", low_memory=False)
    equities = scrips[(scrips["exchangename"] == "NSE") & (scrips["optiontype"] == "EQ")]
    match = equities[equities["scripshortname"] == "RELIANCE"]
    motilal_ok = False
    if not match.empty:
        scripcode = int(match.iloc[0]["scripcode"])
        hashed_password = hashlib.sha256((PASSWORD + API_KEY).encode()).hexdigest()
        totp_code = pyotp.TOTP(TOTP_SECRET).now()
        login_resp = _requests.post(
            _motilal_login_url,
            json={"userid": USER_ID, "password": hashed_password, "2FA": DOB, "totp": totp_code},
            headers=_motilal_headers, timeout=10,
        )
        login_data = login_resp.json()
        if login_data.get("status") == "SUCCESS":
            ltp_headers = _motilal_headers.copy()
            ltp_headers["Authorization"] = login_data["AuthToken"]
            ltp_resp = _requests.post(
                "https://openapi.motilaloswal.com/rest/report/v3/getltpdata",
                json={"clientcode": "", "exchange": "NSE", "scripcode": scripcode},
                headers=ltp_headers, timeout=10,
            )
            motilal_ok = ltp_resp.json().get("status") == "SUCCESS"
except Exception as e:
    motilal_ok = False
    motilal_err = str(e)
else:
    motilal_err = None

angel_status = "OK -- live LTP call succeeded" if angel_ok else f"⚠️ CHECK -- LTP call failed{f' ({angel_err})' if angel_err else ''}"
motilal_status = "OK -- live LTP call succeeded" if motilal_ok else f"⚠️ CHECK -- LTP call failed{f' ({motilal_err})' if motilal_err else ''}"
lines.append(f"\n8. Live broker connectivity (RELIANCE LTP):")
lines.append(f"   Angel One: {angel_status}")
lines.append(f"   Motilal: {motilal_status}")

message = "\n".join(lines)
print(message)
sent = send_telegram_message(message)
print(f"\nTelegram sent: {sent}")
