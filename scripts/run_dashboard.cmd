@echo off
rem Launches the Streamlit dashboard inside WSL on the port assigned by the
rem preview harness (PORT env var, forwarded into WSL via WSLENV).
if "%PORT%"=="" set PORT=8501
set WSLENV=PORT/u
wsl -e bash -c "cd /mnt/c/Users/sandi/Projects/life-os && exec .venv/bin/python -m streamlit run dashboard/app.py --server.headless true --server.port $PORT"
