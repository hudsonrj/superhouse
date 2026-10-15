#!/usr/bin/env python3
"""Macropad ALLOET: Ctrl+G e Ctrl+Shift+O/K/L abrem os quatro aplicativos."""

import ctypes
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes

from pynput import keyboard
from control_client import ControlClient

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "macropad.log")
MUTEX_NAME = "Local\\TecladoAlloetMacropad"

# VK da letra que o macropad manda junto com Ctrl+Shift (ou Ctrl+Alt para H/Y).
APPS = {
    0x43: ("CH8 Control", "https://control.ch8ai.com.br", None),  # Shift+Win+C
    0x5A: ("Monitor e CHControl", ("https://monitor.ch8ai.com.br/", "https://chcontrol.ch8ai.com.br/"), None),  # Shift+Win+Z
    0x47: ("Grok Bot", "desktop", None),  # Ctrl+G
    0x4F: ("ChatGPT", r"C:\Users\hudson.santos\AppData\Local\Microsoft\WindowsApps\chatgpt-classic.exe", None),  # Ctrl+Shift+O
    0x4B: ("Claude", r"C:\Users\hudson.santos\AppData\Local\Microsoft\WindowsApps\claude-desktop.exe", None),  # Ctrl+Shift+K
    0x4C: ("Cursor", "desktop", None),  # Ctrl+Shift+L
    0x48: ("Nino", r"C:\repositorio\nino\Nino.bat", None),  # Ctrl+Alt+H
    0x59: ("Nino", r"C:\repositorio\nino\Nino.bat", None),  # Ctrl+Alt+Y
}

# Atalho do menu Iniciar e o final do executavel da janela.
DESKTOP = {
    "Grok Bot": (
        r"C:\Users\hudson.santos\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Grok Bot.lnk",
        "\\grok bot.exe",
    ),
    "Cursor": (
        r"C:\Users\hudson.santos\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Cursor\Cursor.lnk",
        "\\cursor.exe",
    ),
}

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
KEY_MESSAGES = (WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP)
PRESS_MESSAGES = (WM_KEYDOWN, WM_SYSKEYDOWN)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32
shell32.ShellExecuteW.argtypes = [
    ctypes.c_void_p,
    ctypes.c_wchar_p,
    ctypes.c_wchar_p,
    ctypes.c_wchar_p,
    ctypes.c_wchar_p,
    ctypes.c_int,
]
shell32.ShellExecuteW.restype = ctypes.c_void_p
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, ctypes.c_wchar_p]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.GetLastError.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

_mutex = None
_listener = None
_last_fire = {}
_control = None
_control_keys = set()


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    try:
        with open(LOG, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass
    if sys.stdout is not None:
        print(line, flush=True)


def claim_single_instance():
    global _mutex
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    already = kernel32.GetLastError() == 183
    if not handle:
        return True
    if already:
        kernel32.CloseHandle(handle)
        return False
    _mutex = handle
    return True


def process_image(pid):
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return ""
    buf = ctypes.create_unicode_buffer(520)
    size = wintypes.DWORD(520)
    ok = kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
    kernel32.CloseHandle(handle)
    return buf.value if ok else ""


def find_app_window(image_suffix):
    found = []
    suffix = image_suffix.lower()

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lp):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if process_image(pid.value).lower().endswith(suffix):
            found.append(hwnd)
        return True

    user32.EnumWindows(callback, 0)
    return found[-1] if found else None


def focus_window(hwnd):
    user32.ShowWindow(hwnd, 9)
    foreground = user32.GetForegroundWindow()
    foreground_thread = user32.GetWindowThreadProcessId(foreground, None)
    this_thread = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(this_thread, foreground_thread, True)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(this_thread, foreground_thread, False)


def open_desktop(name):
    lnk, suffix = DESKTOP[name]
    hwnd = find_app_window(suffix)
    if not hwnd:
        subprocess.Popen([r"C:\Windows\explorer.exe", lnk])
        for _ in range(20):
            time.sleep(0.5)
            hwnd = find_app_window(suffix)
            if hwnd:
                break
    if not hwnd:
        log(f"Erro ao abrir {name}: a janela nao apareceu")
        return
    focus_window(hwnd)
    log(f"Abrindo: {name}")


def open_app(name, target, params):
    if isinstance(target, tuple):
        for url in target:
            open_app(name, url, params)
        return
    if name in DESKTOP:
        open_desktop(name)
        return
    code = shell32.ShellExecuteW(None, "open", target, params, None, 1)
    if not code or code <= 32:
        log(f"Erro ao abrir {name}: ShellExecute={code}")
    else:
        log(f"Abrindo: {name}")


def handle_control_event(msg, data):
    vk = data.vkCode
    commands = {0x51: "start", 0x54: "text", 0x41: "autonomy-toggle",
                0xBB: "autonomy-more", 0x6B: "autonomy-more",
                0xBD: "autonomy-less", 0x6D: "autonomy-less"}
    if vk not in commands:
        return False
    if msg not in PRESS_MESSAGES:
        if vk not in _control_keys:
            return False
        _control_keys.remove(vk)
        if vk == 0x51:
            _control.send("stop")
        return True
    if vk in _control_keys:
        return True
    ctrl = user32.GetAsyncKeyState(0x11) & 0x8000
    alt = user32.GetAsyncKeyState(0x12) & 0x8000
    win = (user32.GetAsyncKeyState(0x5B) | user32.GetAsyncKeyState(0x5C)) & 0x8000
    knob = vk in (0xBB, 0x6B, 0xBD, 0x6D)
    # Option corresponde a Alt: Ctrl+Alt++ aumenta; Ctrl+Alt+- diminui.
    if not (ctrl and alt and (knob or win)):
        return False
    _control_keys.add(vk)
    _control.send(commands[vk])
    log(f"Control: {commands[vk]}")
    return True


def on_event(msg, data):
    if msg not in KEY_MESSAGES:
        return True
    if handle_control_event(msg, data):
        _listener.suppress_event()
        return False
    if msg not in KEY_MESSAGES or data.vkCode not in APPS:
        return True
    ctrl = user32.GetAsyncKeyState(0x11) & 0x8000
    shift = user32.GetAsyncKeyState(0x10) & 0x8000
    alt = user32.GetAsyncKeyState(0x12) & 0x8000
    # A KEY1 do macropad emite Ctrl+G (sem Shift). As demais teclas
    # continuam usando Ctrl+Shift para evitar alterar seus atalhos atuais.
    # Nino usa Ctrl+Alt+H ou Ctrl+Alt+Y.
    is_grok = data.vkCode == 0x47
    is_nino = data.vkCode in (0x48, 0x59)  # H ou Y
    if is_nino and msg in PRESS_MESSAGES and (ctrl or alt):
        log(f"Atalho Nino: VK={data.vkCode:02X}, Ctrl={bool(ctrl)}, Alt={bool(alt)}")
    if data.vkCode in (0x43, 0x5A):
        win = (user32.GetAsyncKeyState(0x5B) | user32.GetAsyncKeyState(0x5C)) & 0x8000
        if not (win and shift):
            return True
    elif not ctrl:
        return True
    elif is_grok:
        pass  # Ctrl+G é ok
    elif is_nino:
        if not alt:  # Ctrl+Alt+H/Y
            return True
    else:
        if not shift:  # Ctrl+Shift+O/K/L
            return True
    if msg in PRESS_MESSAGES:
        now = time.monotonic()
        if now - _last_fire.get(data.vkCode, 0) >= 0.6:
            _last_fire[data.vkCode] = now
            name, target, params = APPS[data.vkCode]
            threading.Thread(
                target=open_app, args=(name, target, params), daemon=True
            ).start()
    _listener.suppress_event()
    return False


def main():
    global _listener, _control
    if not claim_single_instance():
        log("Ja estava rodando. Esta copia vai sair.")
        return
    _control = ControlClient(log)
    _control.send("warm")
    log("Macropad ativo. Ctrl+Alt+Shift+Win+Q: voz; Ctrl+Alt+Shift+Win+T: texto.")
    _listener = keyboard.Listener(win32_event_filter=on_event)
    _listener.start()
    try:
        _listener.join()
    finally:
        _control.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"Falha: {exc!r}")
        raise
