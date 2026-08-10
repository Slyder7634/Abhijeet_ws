@echo off
title Abhijeet WS

cd /d "%~dp0"

echo Starting Abhijeet WS...

start "Abhijeet Backend" cmd /k "call venv\Scripts\activate.bat && python backend.py"

timeout /t 2 /nobreak >nul

start "Abhijeet App" cmd /k "call venv\Scripts\activate.bat && python main.py"

exit