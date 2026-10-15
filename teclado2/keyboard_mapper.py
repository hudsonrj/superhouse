#!/usr/bin/env python3
"""
Mapeia as 4 teclas do mini teclado ALLOET para abrir aplicativos
"""
import os
import sys
import time
import subprocess
from pynput import keyboard

# Configuração de URLs e aplicativos
APP_CONFIG = {
    keyboard.Key.f13: ("Cursor", r"C:\Users\hudson.santos\AppData\Local\Programs\cursor\Cursor.exe"),
    keyboard.Key.f14: ("Claude", r"C:\Program Files\WindowsApps\Claude_1.49585.0.0_x64__pzs8sxrjxfjjc\app\claude.exe"),
    keyboard.Key.f15: ("ChatGPT", r"C:\Program Files\WindowsApps\OpenAI.ChatGPT-Desktop_1.2026.190.0_x64__2p2nqsd0c76g0\app\ChatGPT Classic.exe"),
    keyboard.Key.f16: ("Grok Bot", r"C:\Program Files\Grok Bot\Grok Bot.exe"),
}

# Alternativa se as teclas forem numeradas
NUMERIC_CONFIG = {
    '1': ("Grok Bot", r"C:\Program Files\Grok Bot\Grok Bot.exe"),
    '2': ("Claude", "https://claude.ai"),
    '3': ("ChatGPT", "https://chat.openai.com"),
    '4': ("Grok", "https://grok.com"),
}

def open_app(target):
    """Abre uma aplicação ou URL"""
    try:
        if target.startswith("http"):
            # URL - abre no navegador padrão
            os.startfile(target)
        else:
            # Executável
            subprocess.Popen(target)
        return True
    except Exception as e:
        print(f"Erro ao abrir {target}: {e}")
        return False

def on_press(key):
    """Callback quando uma tecla é pressionada"""
    try:
        # Tenta config principal (F13-F16)
        if key in APP_CONFIG:
            app_name, target = APP_CONFIG[key]
            print(f"🎹 Abrindo: {app_name}")
            open_app(target)

        # Tenta config alternativa (números)
        elif hasattr(key, 'char') and key.char in NUMERIC_CONFIG:
            app_name, target = NUMERIC_CONFIG[key.char]
            print(f"🎹 Abrindo: {app_name}")
            open_app(target)

    except AttributeError:
        pass

def main():
    print("=" * 50)
    print("🎹 Mini Teclado ALLOET - Mapper de Aplicativos")
    print("=" * 50)
    print("\nMapeamentos:")
    print("  F13 (KEY1) → Grok Bot")
    print("  F14 (KEY2) → Claude")
    print("  F15 (KEY3) → ChatGPT")
    print("  F16 (KEY4) → Grok\n")
    print("Alternativas (se as acima não funcionarem):")
    print("  1 → Grok Bot")
    print("  2 → Claude")
    print("  3 → ChatGPT")
    print("  4 → Grok\n")
    print("Pressione Ctrl+C para sair...\n")

    # Inicia o listener de teclado
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    try:
        # Verifica se pynput está instalado
        from pynput import keyboard
    except ImportError:
        print("Instalando dependência (pynput)...")
        os.system("pip install pynput -q")
        print("✓ Instalado! Reinicie o script.\n")
        sys.exit(0)

    main()
