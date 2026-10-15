@echo off
title Placa Amarela Gateway
cd /d "%~dp0"
:loop
netstat -ano | findstr ":8788" | findstr "LISTENING" >nul
if not errorlevel 1 (
  timeout /t 20 /nobreak >nul
  goto loop
)
"C:\Users\hudsons\AppData\Local\Programs\Python\Python312\python.exe" -u "%~dp0placa_gateway.py"
echo gateway saiu %errorlevel% — religando em 3s
timeout /t 3 /nobreak >nul
goto loop
