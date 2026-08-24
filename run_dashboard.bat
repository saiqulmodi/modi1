@echo off
cd /d C:\Users\saiqu\Projects\MODI1
"C:\Users\saiqu\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true >> logs\dashboard.log 2>&1
