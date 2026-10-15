#!/usr/bin/env python3
import pyautogui
import time
import pyperclip

# Disable failsafe (move mouse to corner to stop)
pyautogui.FAILSAFE = False

# Configurações das teclas
KEY_CONFIG = {
    "KEY1": "start https://grokbot.com",  # Grokbot
    "KEY2": "start https://chat.openai.com",  # ChatGPT
    "KEY3": "start https://claude.ai",  # Claude
    "KEY4": "start https://grok.com",  # Grok na web
}

# Posições aproximadas dos botões KEY na interface (x, y)
# Baseado na screenshot capturada
KEY_POSITIONS = {
    "KEY1": (190, 228),  # Primeira linha
    "KEY2": (240, 228),  # Primeira linha
    "KEY3": (290, 228),  # Primeira linha
    "KEY4": (340, 228),  # Primeira linha
}

# Campo de entrada de texto (aproximadamente no centro da janela)
INPUT_FIELD = (695, 240)

# Botão Download (para salvar)
DOWNLOAD_BUTTON = (615, 306)

def click_at(x, y, delay=0.3):
    """Clica em uma posição e aguarda"""
    pyautogui.click(x, y)
    time.sleep(delay)

def configure_key(key_name, command):
    """Configura uma tecla com um comando"""
    print(f"Configurando {key_name}: {command}")

    # Clica no botão da tecla
    x, y = KEY_POSITIONS[key_name]
    click_at(x, y, 0.5)

    # Clica no campo de input
    click_at(INPUT_FIELD[0], INPUT_FIELD[1], 0.3)

    # Limpa o campo (Ctrl+A e Delete)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    pyautogui.press('delete')
    time.sleep(0.2)

    # Cola o comando usando clipboard (mais seguro)
    pyperclip.copy(command)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)

    print(f"  ✓ {key_name} configurada")

def main():
    print("Iniciando configuração do MINI KeyBoard em 3 segundos...")
    time.sleep(3)

    # Configura cada tecla
    for key_name, command in KEY_CONFIG.items():
        configure_key(key_name, command)
        time.sleep(1)

    # Clica no botão Download para salvar
    print("Salvando configurações...")
    click_at(DOWNLOAD_BUTTON[0], DOWNLOAD_BUTTON[1], 1)

    print("✓ Configuração concluída!")

if __name__ == "__main__":
    main()
