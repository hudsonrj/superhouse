@echo off
setlocal
cd /d "%~dp0"
set "OLLAMA_HOST=http://127.0.0.1:1337/v1"
set "OPENAI_COMPATIBLE=true"
node src\server\atom.js
pause
