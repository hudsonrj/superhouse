"""Identifica a página do Control sem executar o código do servidor."""
import ast
import re

def site_config(caddy):
    match = re.search(r'(?m)^[^\n]*\bcontrol\.ch8ai\.com\.br\b[^\n]*\{', caddy)
    if not match:
        return ''
    start = caddy.index('{', match.start())
    depth = 0
    for index in range(start, len(caddy)):
        if caddy[index] == '{':
            depth += 1
        elif caddy[index] == '}':
            depth -= 1
            if depth == 0:
                return caddy[start:index + 1]
    return ''

def application_index(source, environment):
    tree = ast.parse(source)
    roots = [node.value for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == 'ROOT' for target in node.targets)]
    if len(roots) != 1:
        return None
    root = roots[0]
    if not (isinstance(root, ast.Call) and len(root.args) >= 2
            and isinstance(root.args[0], ast.Constant) and root.args[0].value == 'APP_UNICA_ROOT'
            and isinstance(root.args[1], ast.Constant) and isinstance(root.args[1].value, str)):
        return None
    values = dict(item.split('=', 1) for item in environment.split('\0') if '=' in item)
    directory = values.get('APP_UNICA_ROOT', root.args[1].value)
    if not directory.startswith('/'):
        return None
    return directory.rstrip('/') + '/novo/index.html'

def candidates(caddy, read, application=None):
    config = site_config(caddy)
    # O site usa reverse proxy para o app-unica; não há root de arquivos no Caddy.
    if re.search(r'\breverse_proxy\b[^\n]*\b(?:127\.0\.0\.1|localhost):8792\b', config) and application:
        paths = [application]
    else:
        paths = [root.rstrip('/') + '/index.html'
                 for root in re.findall(r'\broot\s+(?:\*\s+)?([^\s}]+)', config) if root.startswith('/')]
    result = []
    for file in dict.fromkeys(paths):
        try:
            html = read(file).decode('utf-8')
            if '</body>' in html.lower() and 'control' in html.lower():
                result.append(file)
        except (OSError, UnicodeDecodeError):
            pass
    return result
