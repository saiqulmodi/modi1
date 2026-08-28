@echo off
cd /d C:\Users\saiqu\Projects\MODI1
"C:\Users\saiqu\AppData\Local\Python\pythoncore-3.14-64\python.exe" stock_check.py >> logs\weekly_screener.log 2>&1

git add watchlist.json
git diff --cached --quiet watchlist.json
if errorlevel 1 (
    git commit -m "Update watchlist.json (automated daily screener run)" >> logs\weekly_screener.log 2>&1
    git push >> logs\weekly_screener.log 2>&1
) else (
    echo No watchlist.json changes to commit. >> logs\weekly_screener.log
)
