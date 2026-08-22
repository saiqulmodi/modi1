from datetime import datetime as _dt

_now = _dt.now()
_market_start = _now.replace(hour=9, minute=15, second=0, microsecond=0)
_market_end = _now.replace(hour=15, minute=30, second=0, microsecond=0)
if _now < _market_start or _now > _market_end:
    print(f"Outside market hours ({_now.strftime('%H:%M:%S')}), skipping run.")
    exit()
import pandas as pd
import json
import os
from send_telegram import send_telegram_message

CSV_FILE = "alt_data_momentum.csv"
STATE_FILE = "momentum_alerted_state.json"
THRESHOLD = 100.0

if not os.path.exists(CSV_FILE):
    print("No alt_data_momentum.csv found yet, skipping.")
    exit(0)

csv_mtime = os.path.getmtime(CSV_FILE)

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
else:
    state = {}

if state.get("csv_mtime") != csv_mtime:
    state = {"csv_mtime": csv_mtime, "alerted": []}

alerted = set(state.get("alerted", []))

df = pd.read_csv(CSV_FILE)
new_alerts = []

for _, row in df.iterrows():
    symbol = row["symbol"]
    momentum = row["Momentum (%)"]
    if pd.notna(momentum) and momentum >= THRESHOLD and symbol not in alerted:
        new_alerts.append(f"🔥 {symbol}: search momentum {momentum:+.0f}% (vs prior 23-day avg)")
        alerted.add(symbol)
if new_alerts:
    CHUNK_SIZE = 40
    total_sent_ok = True
    for i in range(0, len(new_alerts), CHUNK_SIZE):
        chunk = new_alerts[i:i + CHUNK_SIZE]
        part_num = (i // CHUNK_SIZE) + 1
        total_parts = (len(new_alerts) + CHUNK_SIZE - 1) // CHUNK_SIZE
        header = f"*MODI1 Search Momentum Spike* (part {part_num}/{total_parts})" if total_parts > 1 else "*MODI1 Search Momentum Spike*"
        message = header + "\n" + "\n".join(chunk)
        sent = send_telegram_message(message)
        if not sent:
            total_sent_ok = False
    print(f"Sent alert for {len(new_alerts)} stock(s). Telegram sent: {total_sent_ok}")
else:
    print("No new momentum spikes to alert.")