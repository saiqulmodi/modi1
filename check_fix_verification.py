"""
One-off validation check (2026-09-03, extended same day for the S/R
breakout change) that today's three MODI1 changes actually worked once the
market has run on them:

1. intraday_confirm.py's CANDLE_MIN_INTERVAL_SECONDS throttle (commit
   3707ba0) should eliminate (or sharply reduce) the "Expecting value:
   line 1 column 1" candle-fetch failures that were starving the volume
   gate of data.
2. buy_sell_alert.py's dedup-state fix (commit 3707ba0) should mean no
   symbol gets the same alert (same headline label, e.g. "BUY" or
   "52-WEEK HIGH BREAKOUT") more than once in a day -- the old bug was a
   transient fetch failure getting persisted as a fake HOLD, making the
   next successful cycle look like a fresh signal.
3. The new multi-timeframe S/R breakout check (commit ef0a485) should (a)
   actually fire when conditions are met and (b) always clear its own
   volume threshold, same as every other volume-gated signal here --
   verified via the "vol X.XXx avg (needs Y.Yx, TIER)" text now logged
   for every alert that carries it (see buy_sell_alert.py's Why: lines).

Dedup key is (symbol, label) rather than symbol alone: a symbol can
legitimately get more than one DIFFERENT alert type on the same day (e.g.
a BUY signal AND a 52-week breakout), which is correct behavior, not a
repeat -- only the same (symbol, label) pair recurring is the bug.

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
# Captures the symbol and everything after "): " on an "ALERT: " headline
# line; the label itself is isolated from that by splitting on " -- " or
# " (score " (see alert_dedup_key), since some labels (e.g. "52-WEEK
# (weekly bars) HIGH BREAKOUT") legitimately contain their own parens.
ALERT_HEADLINE_PATTERN = re.compile(r"^ALERT: \S+ (\S+) \([^)]*\): (.+)$")
LABEL_SPLIT_PATTERN = re.compile(r" -- | \(score ")
VOLUME_GATE_PATTERN = re.compile(r"vol ([\d.]+)x avg \(needs ([\d.]+)x, (\w+)\)")


def alert_dedup_key(headline_line):
    """(symbol, label) for a "ALERT: ..." headline line, or None if it
    doesn't match the expected shape."""
    m = ALERT_HEADLINE_PATTERN.match(headline_line)
    if not m:
        return None
    symbol, rest = m.groups()
    label = LABEL_SPLIT_PATTERN.split(rest, maxsplit=1)[0].strip()
    return symbol, label


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

lines = [f"[MODI1] Fix verification (throttle + dedup + S/R breakout, since commit {baseline.get('commit', '?')}) -- checking logs since deploy"]

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

# 2. Dedup fix: did the same (symbol, label) pair fire more than once
# today in buy_sell_alert.log? Relies on the "ALERT: <emoji> SYMBOL (...):
# label ..." headline line.
if bs_new:
    alert_lines = [l for l in bs_new.splitlines() if l.startswith("ALERT: ")]
    keys_seen = Counter()
    key_to_lines = {}
    for l in alert_lines:
        key = alert_dedup_key(l)
        if key:
            keys_seen[key] += 1
            key_to_lines.setdefault(key, []).append(l)
    repeats = {k: n for k, n in keys_seen.items() if n > 1}
    lines.append(f"\n2. Repeat-alert check: {len(alert_lines)} alert(s) logged since deploy ({len(keys_seen)} distinct symbol+signal pairs).")
    if repeats:
        lines.append(f"⚠️ DEDUP MAY HAVE FAILED -- same (symbol, signal) alerted more than once:")
        for key, n in repeats.items():
            lines.append(f"    {key[0]} / {key[1]} x{n}")
            for l in key_to_lines[key]:
                lines.append(f"        {l}")
    elif alert_lines:
        lines.append("OK -- no (symbol, signal) pair alerted more than once.")
    else:
        lines.append("No alerts fired yet since deploy -- nothing to check yet, also nothing wrong.")
else:
    lines.append("\n2. Repeat-alert check: buy_sell_alert.log not found or hasn't run yet.")

# 3. Volume-gate compliance: every alert that embeds a "vol X.XXx avg
# (needs Y.Yx, TIER)" string (S/R breakout, trend-reversal, relative-
# strength) should show vol >= needs -- covers the new S/R breakout check
# specifically, alongside the signals this already applied to.
if bs_new:
    vol_matches = VOLUME_GATE_PATTERN.findall(bs_new)
    vol_failures = [(v, n, t) for v, n, t in vol_matches if float(v) < float(n)]
    lines.append(f"\n3. Volume-gate compliance: {len(vol_matches)} volume-gated alert(s) checked since deploy.")
    if vol_failures:
        lines.append(f"⚠️ VOLUME GATE FAILED -- {len(vol_failures)} alert(s) fired below their own threshold:")
        for v, n, t in vol_failures[:10]:
            lines.append(f"    vol {v}x < needs {n}x ({t})")
    elif vol_matches:
        lines.append("OK -- every volume-gated alert met or exceeded its threshold.")
    else:
        lines.append("No volume-gated alerts fired yet since deploy -- nothing to check yet, also nothing wrong.")
else:
    lines.append("\n3. Volume-gate compliance: buy_sell_alert.log not found or hasn't run yet.")

# 4. Latest morning_health_check.py summary, for broker/switch/config
# context alongside the above.
health_new = read_new_content("logs/morning_health_check.log", baseline["offsets"].get("logs/morning_health_check.log", 0))
if health_new and health_new.strip():
    lines.append("\n4. Latest morning_health_check.py output since deploy:")
    lines.append(health_new.strip()[-1500:])
else:
    lines.append("\n4. morning_health_check.py hasn't run yet since deploy.")

message = "\n".join(lines)
print(message)
sent = send_telegram_message(message)
print(f"\nTelegram sent: {sent}")
