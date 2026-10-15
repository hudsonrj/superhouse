import ast, pathlib, types
source = ast.parse(pathlib.Path('global_shortcuts.py').read_text())
functions = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in ('on_event', 'handle_control_event')]
keys = {0x11: 0x8000, 0x10: 0, 0x12: 0x8000}
launched = []; suppressed = []; logs = []
class Thread:
    def __init__(self, target, args, daemon): self.args = args
    def start(self): launched.append(self.args)
namespace = dict(KEY_MESSAGES=(256,257,260,261), PRESS_MESSAGES=(256,260), APPS={0x59: ('Nino', 'Nino.bat', None)}, user32=types.SimpleNamespace(GetAsyncKeyState=lambda key: keys.get(key, 0)), log=logs.append, time=types.SimpleNamespace(monotonic=lambda: 1), _last_fire={}, threading=types.SimpleNamespace(Thread=Thread), open_app=None, _listener=types.SimpleNamespace(suppress_event=lambda: suppressed.append(True)))
commands = []
namespace.update(_control_keys=set(), _control=types.SimpleNamespace(send=commands.append))
exec(compile(ast.Module(body=functions, type_ignores=[]), '<on_event>', 'exec'), namespace)
assert namespace['on_event'](260, types.SimpleNamespace(vkCode=0x59)) is False
assert launched == [('Nino', 'Nino.bat', None)] and suppressed == [True]
assert 'Ctrl=True, Alt=True' in logs[-1]
keys[0x12] = 0
assert namespace['on_event'](256, types.SimpleNamespace(vkCode=0x59)) is True
assert len(launched) == 1
print('Ctrl+Alt+Y reconhecido; Ctrl+Y sem Alt ignorado.')

apps = next(n.value for n in source.body if isinstance(n, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'APPS' for target in n.targets))
namespace['APPS'] = ast.literal_eval(apps)
keys.update({0x11: 0, 0x10: 0x8000, 0x12: 0})
for win_key in (0x5B, 0x5C):
    keys[win_key] = 0x8000
    namespace['_last_fire'].clear()
    assert namespace['on_event'](256, types.SimpleNamespace(vkCode=0x43)) is False
    assert launched[-1] == ('CH8 Control', 'https://control.ch8ai.com.br', None)
    count = len(launched)
    assert namespace['on_event'](256, types.SimpleNamespace(vkCode=0x43)) is False
    assert namespace['on_event'](257, types.SimpleNamespace(vkCode=0x43)) is False
    assert len(launched) == count
    keys[win_key] = 0
assert namespace['on_event'](256, types.SimpleNamespace(vkCode=0x43)) is True
keys.update({0x5B: 0x8000, 0x10: 0})
assert namespace['on_event'](256, types.SimpleNamespace(vkCode=0x43)) is True
assert len(launched) == count
print('Shift+Win+C verificado com ambas as teclas Win, modificadores ausentes e repeticao.')

keys.update({0x11: 0x8000, 0x10: 0x8000, 0x12: 0x8000, 0x5B: 0x8000})
q = types.SimpleNamespace(vkCode=0x51)
t = types.SimpleNamespace(vkCode=0x54)
assert namespace['on_event'](256, q) is False
assert namespace['on_event'](256, q) is False
assert commands == ['start']
keys.clear()
assert namespace['on_event'](257, q) is False
assert commands == ['start', 'stop']
assert namespace['on_event'](256, q) is True
for missing in (0x11, 0x12, 0x5B):
    keys.update({key: 0x8000 for key in (0x11, 0x10, 0x12, 0x5B)})
    keys[missing] = 0
    assert namespace['on_event'](256, t) is True
keys.update({0x11: 0x8000, 0x10: 0x8000, 0x12: 0x8000, 0x5B: 0, 0x5C: 0x8000})
assert namespace['on_event'](260, t) is False
assert namespace['on_event'](260, t) is False
keys.clear()
assert namespace['on_event'](261, t) is False
assert commands == ['start', 'stop', 'text']
print('Q/T verificados: todos os modificadores, repeticao e liberacao apos soltar modificadores.')
keys.update({0x11: 0x8000, 0x12: 0x8000, 0x5B: 0x8000})
assert namespace['on_event'](256, q) is False
assert namespace['on_event'](256, q) is False
keys.clear()
assert namespace['on_event'](257, q) is False
keys.update({0x11: 0x8000, 0x12: 0x8000, 0x5B: 0x8000})
assert namespace['on_event'](256, t) is False
keys.clear()
assert namespace['on_event'](257, t) is False
assert commands[-3:] == ['start', 'stop', 'text']
print('Combinação real do macropad (Ctrl+Alt+Win sem Shift) verificada para Q e T.')
for vk, command in [(0x41, 'autonomy-toggle'), (0xBB, 'autonomy-more'), (0x6B, 'autonomy-more'),
                    (0xBD, 'autonomy-less'), (0x6D, 'autonomy-less')]:
    keys.update({0x11: 0x8000, 0x12: 0x8000, 0x5B: 0x8000})
    event = types.SimpleNamespace(vkCode=vk)
    count = len(commands)
    assert namespace['on_event'](256, event) is False
    assert namespace['on_event'](256, event) is False
    assert commands[-1] == command and len(commands) == count + 1
    keys.clear()
    assert namespace['on_event'](257, event) is False
    assert len(commands) == count + 1
print('A e +/- do teclado principal e numerico verificados, sem duplicar ao segurar.')
for vk, command in [(0xBB, 'autonomy-more'), (0x6B, 'autonomy-more'),
                    (0xBD, 'autonomy-less'), (0x6D, 'autonomy-less')]:
    keys.update({0x11: 0x8000, 0x12: 0x8000})
    event = types.SimpleNamespace(vkCode=vk)
    assert namespace['on_event'](256, event) is False
    assert commands[-1] == command
    keys.clear()
    assert namespace['on_event'](257, event) is False
    for missing in (0x11, 0x12):
        keys.update({0x11: 0x8000, 0x12: 0x8000, 0x10: 0x8000})
        keys[missing] = 0
        assert namespace['on_event'](256, event) is True
keys.update({0x11: 0x8000, 0x12: 0x8000, 0x10: 0x8000})
for vk in (0x41, 0x51, 0x54):
    assert namespace['on_event'](256, types.SimpleNamespace(vkCode=vk)) is True
print('Giratorio Ctrl+Alt++ aumenta e Ctrl+Alt+- diminui verificado; A/Q/T continuam exigindo Win.')

keys.clear()
z = types.SimpleNamespace(vkCode=0x5A)
for win_key in (0x5B, 0x5C):
    keys.update({0x10: 0x8000, win_key: 0x8000})
    namespace['_last_fire'].clear()
    count = len(launched)
    assert namespace['on_event'](256, z) is False
    assert namespace['on_event'](256, z) is False
    assert namespace['on_event'](257, z) is False
    assert len(launched) == count + 1
    assert launched[-1][1] == ('https://monitor.ch8ai.com.br/', 'https://chcontrol.ch8ai.com.br/')
    keys.clear()
for modifiers in ({}, {0x10: 0x8000}, {0x5B: 0x8000}):
    keys.clear(); keys.update(modifiers)
    assert namespace['on_event'](256, z) is True
opened = []
open_function = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'open_app')
open_namespace = dict(DESKTOP={}, shell32=types.SimpleNamespace(ShellExecuteW=lambda *args: opened.append(args[2]) or 33), log=logs.append)
exec(compile(ast.Module(body=[open_function], type_ignores=[]), '<open_app>', 'exec'), open_namespace)
open_namespace['open_app'](*launched[-1])
assert opened == ['https://monitor.ch8ai.com.br/', 'https://chcontrol.ch8ai.com.br/']
print('Shift+Win+Z: duas URLs, ambas as teclas Win, modificadores e repeticao verificados.')
