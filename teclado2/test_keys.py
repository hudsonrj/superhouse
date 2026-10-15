#!/usr/bin/env python3
"""
Testa as teclas do macropad e mostra qual é o código de cada uma
"""
from pynput import keyboard
import time

print("=" * 60)
print("TESTE DE TECLAS - Mini Teclado ALLOET")
print("=" * 60)
print("\nPressione cada uma das 4 teclas do seu macropad.")
print("O código de cada tecla será mostrado abaixo:\n")

pressed_keys = []

def on_press(key):
    global pressed_keys
    try:
        # Tenta pegar a representação da tecla
        key_name = key
        print(f"Tecla pressionada: {key_name}")
        print(f"  Tipo: {type(key)}")
        print(f"  String: '{str(key)}'")

        # Se for uma tecla nomeada
        if isinstance(key, keyboard.Key):
            print(f"  Valor: {key}")
        # Se for um caractere
        elif isinstance(key, keyboard.KeyCode):
            print(f"  Vchar: {key.char}")
            print(f"  Vcode: {key.vk}")

        pressed_keys.append(str(key))
        print()

        if len(pressed_keys) >= 4:
            print("\n" + "=" * 60)
            print("RESUMO DAS 4 TECLAS:")
            print("=" * 60)
            for i, key_code in enumerate(pressed_keys, 1):
                print(f"Tecla {i}: {key_code}")
            print("\nEnvie esses códigos ao Claude para atualizar o script!")
            return False  # Para o listener

    except AttributeError:
        pass

# Inicia o listener
with keyboard.Listener(on_press=on_press) as listener:
    listener.join()

print("\nFim do teste.")
