"""
One-off validation check (2026-09-03) that momentum_scan_alert.py's
volume-gate fix from 2026-09-02 is actually working on live data: every
RELATIVE STRENGTH / TREND REVERSAL BUY alert sent should show a volume
ratio at or above its own threshold (each alert message embeds
"vol X.XXx avg (needs Y.Yx, TIER)" -- see momentum_scan_alert.py). Read-only
-- doesn't modify any state, doesn't resend anything. Sends one Telegram
summary. Meant to run once tomorrow morning after a few scan cycles.
"""

import sys
import re
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

from send_telegram import send_telegram_message

LOG_PATH = "logs/momentum_scan_alert.log"
PATTERN = re.compile(r"vol ([\d.]+)x avg \(needs ([\d.]+)x, (\w+)\)")

try:
    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        log = f.read()
except FileNotFoundError:
    log = None

lines = [f"[MODI1] Momentum scan volume-gate check -- {datetime.now().strftime('%Y-%m-%d %H:%M')}"]

if log is None:
    lines.append("\n⚠️ No momentum_scan_alert.log found at all.")
else:
    matches = PATTERN.findall(log)
    if not matches:
        lines.append("\nNo momentum alerts have fired yet today -- nothing to verify, but also nothing wrong.")
    else:
        failures = [(vol, needs, tier) for vol, needs, tier in matches if float(vol) < float(needs)]
        lines.append(f"\nMomentum alerts checked: {len(matches)}")
        if failures:
            lines.append(f"⚠️ VOLUME GATE FAILED -- {len(failures)} alert(s) fired below their own threshold:")
            for vol, needs, tier in failures[:10]:
                lines.append(f"    vol {vol}x < needs {needs}x ({tier})")
        else:
            lines.append("OK -- every alert met or exceeded its volume threshold.")

message = "\n".join(lines)
print(message)
sent = send_telegram_message(message)
print(f"\nTelegram sent: {sent}")
