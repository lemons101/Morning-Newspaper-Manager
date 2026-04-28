@echo off
cd /d "%~dp0"
F:\Anaconda\Scripts\conda.exe run -n env1 python -B -m streamlit run dashboard_app.py --server.address=127.0.0.1 --server.port=8502 --server.headless=true
