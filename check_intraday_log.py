"""
One-off verification: checks the most recent monitor_intraday.py run in
logs/intraday_monitor.log and sends a Telegram summary covering:
  1. Whether it completed without a UnicodeEncodeError/Traceback
  2. How long the run took (from the "RUN COMPLETE: took X min" line)
  3. Whether alerts (if any) went out as one consolidated message
  4. Whether the following run hit the "still in progress" overlap guard
"""

import re
from send_telegram import send_telegram_message

LOG_FILE = "logs/intraday_monitor.log"

with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

runs = list(re.finditer(r"===== RUN: (.+?) =====", content))
if not runs:
    send_telegram_message("Log check: no RUN entries found in intraday_monitor.log yet.")
    raise SystemExit

last_run = runs[-1]
run_start_text = last_run.group(1)
run_body = content[last_run.end():runs[-1].end() if len(runs) == 1 else content.find("===== RUN:", last_run.end())]
if run_body == -1 or "===== RUN:" not in content[last_run.end():]:
    run_body = content[last_run.end():]
else:
    next_run_pos = content.find("===== RUN:", last_run.end())
    run_body = content[last_run.end():next_run_pos] if next_run_pos != -1 else content[last_run.end():]

has_error = bool(re.search(r"Traceback|UnicodeEncodeError", run_body))
duration_match = re.search(r"RUN COMPLETE: took ([\d.]+) min", run_body)
duration_text = f"{duration_match.group(1)} min" if duration_match else "not found (older log format or run still in progress)"
consolidated_match = re.search(r"Sent (\d+) alert\(s\) in (\d+) message\(s\)", run_body)
overlap_guard_hit = "Previous run still in progress, skipping this run" in content[last_run.end():]

lines = [
    "<b>MODI1 Intraday Monitor - log check</b>",
    f"Last run started: {run_start_text}",
    f"Errors/traceback found: {'YES - see log' if has_error else 'No'}",
    f"Run duration: {duration_text}",
]

if consolidated_match:
    n_alerts, n_messages = (int(x) for x in consolidated_match.groups())
    consolidated = n_messages < n_alerts or n_alerts <= 1
    lines.append(f"Alerts: {n_alerts} sent in {n_messages} message(s) (consolidated: {'yes' if consolidated else 'no'})")
else:
    lines.append("Alerts: none triggered this run")

lines.append(f"Overlap with next run detected: {'YES' if overlap_guard_hit else 'No'}")

message = "\n".join(lines)
print(message)
send_telegram_message(message)
