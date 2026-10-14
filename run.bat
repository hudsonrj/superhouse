@echo off
REM Script para rodar o mapper de teclado
REM Configura as 4 teclas do mini teclado

cd /d "%~dp0"

echo.
echo ===============================================
echo Mini Teclado ALLOET - Ativador
echo ===============================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo Erro: Python nao encontrado!
    echo Instale Python de https://python.org
    pause
    exit /b 1
)

echo Iniciando mapper de teclado...
echo.

REM Executa o script Python
python global_shortcuts.py

pause
