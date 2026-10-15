"""Conecta o Atomic Chat ao Hermes local, preservando os outros MCPs."""
import json
import os
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
local = Path(os.environ['LOCALAPPDATA'])
python = local / 'hermes/hermes-agent/venv/Scripts/python.exe'
bridge = root / 'scripts/hermes_mcp.py'
if not python.is_file() or not bridge.is_file():
    raise SystemExit('Ambiente Hermes ou adaptador ausente.')
config = Path(os.environ['APPDATA']) / 'Atomic Chat/data/mcp_config.json'
data = json.loads(config.read_text(encoding='utf-8-sig'))
backup = config.with_name('mcp_config.before-nino-hermes.json')
if not backup.exists():
    shutil.copy2(config, backup)
data.setdefault('mcpServers', {})['hermes-local'] = {
    'active': True, 'type': 'stdio', 'command': str(python),
    'args': [str(bridge)], 'cwd': str(root), 'env': {'PYTHONIOENCODING': 'utf-8'},
}
data.setdefault('mcpSettings', {})['toolCallTimeoutSeconds'] = max(300, data.get('mcpSettings', {}).get('toolCallTimeoutSeconds', 30))
temporary = config.with_suffix('.nino-tmp')
temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
os.replace(temporary, config)
verified = json.loads(config.read_text(encoding='utf-8'))
assert verified['mcpServers']['hermes-local']['command'] == str(python)
print('Conector hermes-local configurado. Backup da configuracao anterior preservado junto ao arquivo MCP.')
