#!/usr/bin/env python3
"""
Configura o mini teclado com 4 atalhos
"""
import pyautogui
import time
import pyperclip
import subprocess
from pathlib import Path

# Disable pyautogui's failsafe
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1

# URLs/Comandos para cada tecla
KEYBOARD_CONFIG = [
    ("KEY1", "start https://grokbot.com", "Grokbot"),
    ("KEY2", "start https://chat.openai.com", "ChatGPT"),
    ("KEY3", "start https://claude.ai", "Claude"),
    ("KEY4", "start https://grok.com", "Grok na web"),
]

def find_mini_keyboard_window():
    """Encontra a janela MINI KeyBoard"""
    import subprocess
    result = subprocess.run(
        ["powershell", "-Command",
         "Get-Process | Where-Object {$_.Name -eq 'MINI KeyBoard'} | Select-Object -First 1"],
        capture_output=True, text=True
    )
    return "MINI KeyBoard" in result.stdout

def click_key_button(key_num):
    """Clica no botão da tecla KEY1/2/3/4"""
    # Posições aproximadas dos botões (baseado na screenshot)
    # A janela está em torno de (160, 160)
    positions = {
        1: (190, 228),   # KEY1
        2: (240, 228),   # KEY2
        3: (290, 228),   # KEY3
        4: (340, 228),   # KEY4
    }
    x, y = positions.get(key_num, (190, 228))
    pyautogui.click(x, y)
    time.sleep(0.5)

def type_command(command):
    """Digita um comando no campo de texto"""
    # Clica no campo de input (grande, no centro)
    pyautogui.click(695, 240)
    time.sleep(0.3)

    # Limpa (Ctrl+A + Delete)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    pyautogui.press('delete')
    time.sleep(0.2)

    # Cola via clipboard (mais seguro que digitar caracteres especiais)
    pyperclip.copy(command)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)

def save_config():
    """Clica no botão Download para salvar"""
    pyautogui.click(615, 306)  # Download button
    time.sleep(1)

def main():
    print("🎹 Configurador de Mini Teclado MINI KeyBoard")
    print("=" * 50)

    # Aguarda que a janela esteja em foco
    print("\n⚠️  Clique na janela MINI KeyBoard em 5 segundos...")
    time.sleep(5)

    print("\n▶️  Iniciando configuração...\n")

    for key_num, key_name, description in KEYBOARD_CONFIG:
        # Extrai número da tecla (KEY1 -> 1)
        num = int(key_name[-1])
        command = KEYBOARD_CONFIG[num-1][1]

        print(f"  [{key_name}] Configurando para: {description}")

        # Clica no botão da tecla
        click_key_button(num)

        # Digita o comando
        type_command(command)

        print(f"  ✓ {key_name} pronta\n")
        time.sleep(0.5)

    # Salva as configurações
    print("💾 Salvando configurações...")
    save_config()

    print("\n✅ Configuração concluída com sucesso!")
    print("\nAs teclas estão prontas para usar:")
    for key_name, cmd, desc in KEYBOARD_CONFIG:
        print(f"  • {key_name}: {desc}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
