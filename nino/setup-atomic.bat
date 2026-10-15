@echo off
REM Setup otimizado do Nino para usar Atomic Chat local
REM Instala: Piper (voz) + Whisper (transcrição)
REM Não precisa de Ollama (usa Atomic Chat em http://127.0.0.1:1337/v1)

setlocal enabledelayedexpansion

echo.
echo 🔧 Setup Nino + Atomic Chat
echo.

REM Verifica se Node.js está instalado
where node >nul 2>nul
if errorlevel 1 (
  echo ❌ Node.js não encontrado. Instale de: https://nodejs.org/
  exit /b 1
)

echo ✅ Node.js encontrado
echo.

REM ================================================================
echo 📦 Passo 1/3: Baixar Piper (voz neural PT-BR)
REM ================================================================

if not exist "vendor\piper\piper.exe" (
  echo Criando diretório vendor...
  if not exist "vendor\voices" mkdir vendor\voices
  if not exist "vendor\piper" mkdir vendor\piper

  echo Baixando Piper para Windows...
  powershell -NoProfile -Command ^
    "Invoke-WebRequest -Uri 'https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip' -OutFile '$env:TEMP\piper.zip'; " ^
    "Expand-Archive -Path '$env:TEMP\piper.zip' -DestinationPath 'vendor' -Force; " ^
    "Remove-Item '$env:TEMP\piper.zip'"
  if errorlevel 1 (
    echo ⚠️  Erro ao baixar Piper. Você pode:
    echo    1. Baixar manualmente: https://github.com/rhasspy/piper/releases
    echo    2. Extrair em vendor/piper
    echo    3. Continuar sem voz
  ) else (
    echo ✅ Piper instalado
  )
) else (
  echo ✅ Piper já existe
)

echo.
echo 📥 Baixando vozes PT-BR...

for %%V in (pt_BR-faber-medium pt_BR-edresson-low) do (
  if not exist "vendor\voices\%%V.onnx" (
    echo   • %%V...
    powershell -NoProfile -Command ^
      "Invoke-WebRequest -Uri 'https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/%%V.onnx' -OutFile 'vendor\voices\%%V.onnx'; " ^
      "Invoke-WebRequest -Uri 'https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/%%V.onnx.json' -OutFile 'vendor\voices\%%V.onnx.json'"
  )
)

echo ✅ Vozes PT-BR prontas
echo.

REM ================================================================
echo 🎤 Passo 2/3: Whisper (transcrição de voz)
REM ================================================================

REM Verifica Python
where python >nul 2>nul
if errorlevel 1 (
  echo ⚠️  Python3 não encontrado.
  echo    Instale de: https://www.python.org/
  echo    Marque "Add Python to PATH"
  echo    Depois execute este script novamente.
  goto skip_whisper
)

echo ✅ Python encontrado

if not exist "vendor\sttenv" (
  echo Criando ambiente Python virtual...
  python -m venv vendor\sttenv

  echo Ativando ambiente...
  call vendor\sttenv\Scripts\activate.bat

  echo Instalando faster-whisper...
  pip install -q --upgrade pip
  pip install -q faster-whisper

  call vendor\sttenv\Scripts\deactivate.bat
  echo ✅ Whisper pronto
) else (
  echo ✅ Ambiente Whisper já existe
)

:skip_whisper

echo.

REM ================================================================
echo 🎨 Passo 3/3: Ícones (opcional)
REM ================================================================

if exist "scripts\make-icons.js" (
  echo Gerando ícones...
  node scripts\make-icons.js
  echo ✅ Ícones prontos
)

echo.
echo ================================================================
echo ✅ Setup completo!
echo ================================================================
echo.
echo 📋 Próximos passos:
echo.
echo 1️⃣  Atomic Chat
echo    • Certifique-se que está rodando em http://127.0.0.1:1337
echo    • Crie um projeto e adicione seus documentos (base de conhecimento)
echo.
echo 2️⃣  Iniciar Nino
echo    • Abra esta pasta em PowerShell ou CMD
echo    • Execute:
echo.
echo      .\run-atomic.bat
echo.
echo    • Ou use npm:
echo.
echo      npm run web
echo.
echo 3️⃣  Acesse no navegador
echo    • Abra Chrome ou Edge
echo    • Vá para: http://127.0.0.1:3081
echo    • Clique em 🪟 para modo flutuante
echo.

pause
