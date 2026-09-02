"""
Detects the exact failure mode seen on 2026-09-02: the MODI1Dashboard
service reports "Running" and its python.exe process stays alive (still
using CPU), but the process silently stops listening on port 8501 --
possibly related to the sleep/wake issue also fixed that day. Windows'
own service-crash recovery doesn't catch this since the process never
actually exits. Checks both that the port is listening AND that the page
actually responds to an HTTP request, then restarts the service if not.
Meant to run every 15-20 min via Task Scheduler (see
register_dashboard_watchdog.ps1) -- restarting an already-fine service is
harmless (just a few seconds of downtime), so this errs toward restarting
whenever it can't positively confirm health rather than trying to be
clever about diagnosing the exact cause first.
"""

import subprocess
import sys
from datetime import datetime

import requests

sys.stdout.reconfigure(encoding="utf-8")

PORT = 8501
URL = f"http://localhost:{PORT}"
SERVICE_NAME = "MODI1Dashboard"


def is_dashboard_healthy():
    try:
        response = requests.get(URL, timeout=8)
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


print(f"===== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")

if is_dashboard_healthy():
    print("Dashboard healthy, nothing to do.")
else:
    print("Dashboard NOT responding -- restarting service.")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"Restart-Service {SERVICE_NAME}"],
        capture_output=True, text=True, timeout=60,
    )
    print(f"Restart-Service exit code: {result.returncode}")
    if result.stderr:
        print(f"stderr: {result.stderr}")

    import time
    time.sleep(10)
    if is_dashboard_healthy():
        print("Recovered -- dashboard responding after restart.")
    else:
        print("STILL NOT RESPONDING after restart -- needs manual attention.")
