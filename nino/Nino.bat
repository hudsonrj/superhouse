@echo off
setlocal
cd /d "%~dp0"
set "OLLAMA_HOST=http://127.0.0.1:1337/v1"
set "OPENAI_COMPATIBLE=true"
if not exist "node_modules\electron\dist\electron.exe" (
  echo Electron ausente. Execute npm install nesta pasta.
  pause
  exit /b 1
)
start "" "%~dp0node_modules\electron\dist\electron.exe" "%~dp0."
exit /b 0