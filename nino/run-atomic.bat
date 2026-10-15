@echo off
REM Inicia Nino com Atomic Chat local

setlocal enabledelayedexpansion

echo.
echo 🚀 Iniciando Nino com Atomic Chat...
echo.

REM Define Atomic Chat como backend (OpenAI-compatible)
set OLLAMA_HOST=http://127.0.0.1:1337/v1
set OPENAI_COMPATIBLE=true

REM Inicia servidor web do Nino
echo 📡 Servidor rodando em http://127.0.0.1:3081
echo 🌐 Abra no Chrome/Edge e clique em 🪟 para modo flutuante
echo.
echo ⚠️  Aguardando dependências...
echo    - Piper (voz)
echo    - Whisper (transcrição)
echo    - Node.js packages
echo.

node src/server/web.js

endlocal
pause
