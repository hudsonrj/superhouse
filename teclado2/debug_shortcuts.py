#!/usr/bin/env python3
"""
Debug - mostra todas as teclas pressionadas
"""
from pynput import keyboard
import time

print("=" * 60)
print("DEBUG - Monitorando TODAS as teclas")
print("=" * 60)
print("\nPressione qualquer tecla para ver o código dela.")
print("Pressione ESC para parar.\n")

def on_press(key):
    try:
        if key == keyboard.Key.esc:
            print("\nParado.")
            return False

        # Mostra a tecla pressionada
        print(f"Pressionou: {key}")

        # Se tiver um char
        if hasattr(key, 'char'):
            print(f"  char: {key.char}")

        # Se for uma tecla nomeada
        if isinstance(key, keyboard.Key):
            print(f"  Key: {key}")

    except AttributeError:
        pass

print("(Aguardando teclas...)\n")

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
