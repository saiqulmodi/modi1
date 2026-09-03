"""
One-off validation check (2026-09-03) that the throttle + dedup-state fix
(commit 3707ba0 -- see fix_verification_baseline.json) actually worked once
the market has run on it: (1) intraday_confirm.py's new
CANDLE_MIN_INTERVAL_SECONDS throttle should eliminate (or sharply reduce)
the "Expecting value: line 1 column 1" candle-fetch failures that were
starving the volume gate of data, and (2) buy_sell_alert.py should no
longer re-send the same BUY/SELL alert for a symbol whose signal never
actually changed (the old bug: a transient fetch failure got persisted as
a fake HOLD, making the next successful cycle look like a fresh signal).

Only reads content appended AFTER the byte offsets recorded in
fix_verification_baseline.json, so pre-fix log history (which is full of
exactly the errors we're checking are now gone) doesn't pollute the count.
Read-only -- doesn't modify any state. Sends one Telegram summary. Meant
to run once, the morning after deploy, after a few buy_sell_alert.py
cycles (every 15 min) have had a chance to run.
"""

import json
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

from send_telegram import send_telegram_message

BASELINE_FILE = "fix_verification_baseline.json"
CANDLE_ERROR_PATTERN = "Expecting value: line 1 column 1"
ALERT_LINE_PATTERN = re.compile(r"^ALERT: [^\s]+ (\S+) \(")


def read_new_content(path, offset):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            return f.read()
    except FileNotFoundError:
        return None


try:
    with open(BASELINE_FILE, "r", encoding="utf-8") as f:
        baseline = json.load(f)
except FileNotFoundError:
    print(f"No {BASELINE_FILE} found -- nothing to compare against.")
    sys.exit(1)

lines = [f"[MODI1] Fix verification (throttle + dedup, commit {baseline.get('commit', '?')}) -- checking logs since deploy"]

# 1. Candle-fetch throttle: did "Expecting value" errors go away?
bs_new = read_new_content("logs/buy_sell_alert.log", baseline["offsets"].get("logs/buy_sell_alert.log", 0))
mom_new = read_new_content("logs/momentum_scan_alert.log", baseline["offsets"].get("logs/momentum_scan_alert.log", 0))

if bs_new is None and mom_new is None:
    lines.append("\n⚠️ Neither buy_sell_alert.log nor momentum_scan_alert.log found -- nothing has run yet.")
else:
    bs_errors = bs_new.count(CANDLE_ERROR_PATTERN) if bs_new else 0
    mom_errors = mom_new.count(CANDLE_ERROR_PATTERN) if mom_new else 0
    total_errors = bs_errors + mom_errors
    if total_errors == 0:
        lines.append("\n1. Candle-fetch throttle: OK -- zero \"Expecting value\" errors since deploy (was constant before).")
    else:
        lines.append(
            f"\n1. Candle-fetch throttle: ⚠️ {total_errors} \"Expecting value\" error(s) still occurred "
            f"(buy_sell_alert.log: {bs_errors}, momentum_scan_alert.log: {mom_errors}) -- fewer than before "
            "is still progress, but check if the 1s interval needs to be longer."
        )

# 2. Dedup fix: did the same ALERT (symbol + signal) fire more than once
# today in buy_sell_alert.log? Relies on the new "ALERT: <emoji> SYMBOL
# (...)" log line added alongside this fix.
if bs_new:
    alert_lines = [l for l in bs_new.splitlines() if l.startswith("ALERT: ")]
    symbols_seen = Counter()
    for l in alert_lines:
        m = ALERT_LINE_PATTERN.match(l)
        if m:
            symbols_seen[m.group(1)] += 1
    repeats = {sym: n for sym, n in symbols_seen.items() if n > 1}
    lines.append(f"\n2. Repeat-alert check: {len(alert_lines)} alert(s) logged since deploy.")
    if repeats:
        lines.append(f"⚠️ DEDUP MAY HAVE FAILED -- same symbol alerted more than once: {repeats}")
        for l in alert_lines:
            lines.append(f"    {l}")
    elif alert_lines:
        lines.append("OK -- no symbol alerted more than once.")
    else:
        lines.append("No BUY/SELL/trend-reversal alerts fired yet since deploy -- nothing to check yet, also nothing wrong.")
else:
    lines.append("\n2. Repeat-alert check: buy_sell_alert.log not found or hasn't run yet.")

# 3. Latest morning_health_check.py summary, for broker/switch/config
# context alongside the above.
health_new = read_new_content("logs/morning_health_check.log", baseline["offsets"].get("logs/morning_health_check.log", 0))
if health_new and health_new.strip():
    lines.append("\n3. Latest morning_health_check.py output since deploy:")
    lines.append(health_new.strip()[-1500:])
else:
    lines.append("\n3. morning_health_check.py hasn't run yet since deploy.")

message = "\n".join(lines)
print(message)
sent = send_telegram_message(message)
print(f"\nTelegram sent: {sent}")
