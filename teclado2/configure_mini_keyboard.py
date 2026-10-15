#!/usr/bin/env python3
"""
Configura o MINI KeyBoard automaticamente via GUI
"""
import pyautogui
import time
import pyperclip
import subprocess

# Apps a configurar
KEYS_CONFIG = [
    {
        "key_num": 1,
        "name": "Cursor",
        "path": r"C:\Users\hudson.santos\AppData\Local\Programs\cursor\Cursor.exe"
    },
    {
        "key_num": 2,
        "name": "Claude",
        "path": r"C:\Program Files\WindowsApps\Claude_1.49585.0.0_x64__pzs8sxrjxfjjc\app\claude.exe"
    },
    {
        "key_num": 3,
        "name": "ChatGPT",
        "path": r'C:\Program Files\WindowsApps\OpenAI.ChatGPT-Desktop_1.2026.190.0_x64__2p2nqsd0c76g0\app\ChatGPT Classic.exe'
    },
    {
        "key_num": 4,
        "name": "Grok Bot",
        "path": r"C:\Program Files\Grok Bot\Grok Bot.exe"
    }
]

def click_key_button(key_num):
    """Clica no botão KEY1/2/3/4 na interface"""
    positions = {
        1: (190, 228),
        2: (240, 228),
        3: (290, 228),
        4: (340, 228),
    }
    x, y = positions.get(key_num, (190, 228))
    pyautogui.click(x, y)
    time.sleep(0.5)

def enter_path(path):
    """Digita o caminho do executável no campo de texto"""
    # Clica no campo de input
    pyautogui.click(695, 240)
    time.sleep(0.3)

    # Limpa campo (Ctrl+A + Delete)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    pyautogui.press('delete')
    time.sleep(0.2)

    # Cola o caminho
    pyperclip.copy(path)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)

def main():
    print("=" * 60)
    print("MINI KeyBoard - Configurador Automático")
    print("=" * 60)
    print("\n⚠️  Clique na janela do MINI KeyBoard em 5 segundos...\n")
    time.sleep(5)

    print("▶️  Iniciando configuração...\n")

    for config in KEYS_CONFIG:
        key_num = config["key_num"]
        name = config["name"]
        path = config["path"]

        print(f"[{key_num}/4] Configurando KEY{key_num}: {name}")
        print(f"     Caminho: {path}\n")

        # Clica no botão da tecla
        click_key_button(key_num)

        # Digita o caminho
        enter_path(path)

        time.sleep(1)

    # Clica em Download para salvar
    print("💾 Salvando configurações (clicando Download)...")
    pyautogui.click(615, 306)  # Download button
    time.sleep(2)

    print("\n✅ Pronto! As configurações foram enviadas para o teclado.")
    print("\nTeste pressionar cada uma das 4 teclas/botões do macropad:")
    print("  • KEY1 → Cursor")
    print("  • KEY2 → Claude")
    print("  • KEY3 → ChatGPT")
    print("  • KEY4 → Grok Bot")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
