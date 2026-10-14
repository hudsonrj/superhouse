#!/usr/bin/env python3
"""
Teste de detecção - mostra quando detecta a combinação Ctrl+Shift
"""
from pynput import keyboard
import subprocess

ctrl_pressed = False
shift_pressed = False
combo_detected = False

def on_press(key):
    global ctrl_pressed, shift_pressed, combo_detected

    try:
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            ctrl_pressed = True
            print("✓ Ctrl pressionado")
        elif key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
            shift_pressed = True
            print("✓ Shift pressionado")
        else:
            # Mostra tudo que é pressionado
            if hasattr(key, 'char'):
                print(f"  + Tecla: '{key.char}' (char)")
                if key.char == '\x07':
                    print("    → Tecla 1 (Grok Bot) detectada!")
                    if ctrl_pressed and shift_pressed:
                        print("      ✅ COMBO DETECTADA! Abrindo Grok Bot...")
                        subprocess.Popen(r"C:\Program Files\Grok Bot\Grok Bot.exe")
            else:
                print(f"  + Tecla: {key}")

    except AttributeError:
        pass

def on_release(key):
    global ctrl_pressed, shift_pressed
    try:
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            ctrl_pressed = False
            print("✗ Ctrl solto")
        elif key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
            shift_pressed = False
            print("✗ Shift solto")
    except AttributeError:
        pass

print("=" * 60)
print("TESTE DE DETECÇÃO")
print("=" * 60)
print("\nPressione as teclas do macropad...")
print("Pressione ESC para sair.\n")

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
