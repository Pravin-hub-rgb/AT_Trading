@echo off
cd /d "%~dp0"
echo Starting BTC Trading Server (venv Python)...
echo.
call venv\Scripts\activate
python server.py
pause