@echo off
title AT Trading
echo Starting AT Trading...
echo   Frontend: http://localhost:3002
echo   Backend:  http://localhost:8003
echo.
start "" http://localhost:3002
bun run dev
pause
