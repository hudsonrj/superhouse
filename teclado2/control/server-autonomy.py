"""Estado autoritativo do macropad; instalado junto ao action-inbox do Control."""
import hmac
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

ROOT = Path(os.environ.get('CONTROL_AUTONOMY_DIR', '/opt/control-autonomy'))
TOKEN_FILE = Path(os.environ.get('CONTROL_AUTONOMY_TOKEN_FILE', '/opt/nino-ch8-gateway/token'))
LABELS = {-3: 'Supervisão máxima: aprovar cada etapa', -2: 'Revisar rascunhos antes de enviar', -1: 'Pedir aprovação antes de responder', 0: 'Neutro: alertar e recomendar', 1: 'Autonomia cautelosa (95%)', 2: 'Autonomia ampliada (85%)', 3: 'Autonomia máxima nas respostas'}

def database():
    ROOT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(ROOT / 'state.sqlite', timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, enabled INTEGER, level INTEGER, revision INTEGER, expires INTEGER)')
    db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, action TEXT, result TEXT)')
    db.execute('INSERT OR IGNORE INTO state VALUES (1,0,0,0,0)')
    db.commit()
    return db

def snapshot(row, now):
    enabled, level, revision, expires = row
    return {'enabled': bool(enabled and expires > now), 'level': level,
            'scaleVersion': 2, 'revision': revision, 'expiresAt': expires, 'label': LABELS[level],
            'expired': bool(enabled and expires <= now)}

def read_state():
    db = database()
    try:
        return snapshot(db.execute('SELECT enabled,level,revision,expires FROM state WHERE id=1').fetchone(), int(time.time()))
    finally:
        db.close()

def update(data):
    if not isinstance(data, dict) or data.get('action') not in ('toggle', 'more', 'less', 'heartbeat'):
        raise ValueError('Ação inválida.')
    request_id = str(uuid.UUID(data['requestId']))
    action = data['action']
    db = database()
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT action,result FROM requests WHERE id=?', (request_id,)).fetchone()
            if previous:
                if previous[0] != action:
                    raise ValueError('Identificador já usado.')
                return json.loads(previous[1])
            now = int(time.time())
            enabled, level, revision, expires = db.execute('SELECT enabled,level,revision,expires FROM state WHERE id=1').fetchone()
            active = bool(enabled and expires > now)
            changed = False
            if action == 'toggle':
                enabled, level = int(not active), 0
                changed = True
            elif action in ('more', 'less') and active:
                next_level = max(-3, min(3, level + (1 if action == 'more' else -1)))
                changed = next_level != level
                level = next_level
            elif not active:
                changed = bool(enabled)
                enabled, level = 0, 0
            if changed:
                revision += 1
            expires = now + 300 if enabled else 0
            db.execute('UPDATE state SET enabled=?,level=?,revision=?,expires=? WHERE id=1', (enabled, level, revision, expires))
            result = snapshot((enabled, level, revision, expires), now)
            db.execute('INSERT INTO requests VALUES (?,?,?)', (request_id, action, json.dumps(result)))
            return result
    finally:
        db.close()

def handle(handler, path, method, read_json_body=None):
    if path not in ('/api/autonomy', '/autonomy', '/api/autonomy/status.js'):
        return False
    if method == 'GET' and path == '/api/autonomy/status.js':
        code = Path(__file__).with_name('autonomy-status.js').read_bytes()
        handler.send_response(200)
        handler.send_header('Content-Type', 'text/javascript; charset=utf-8')
        handler.send_header('Cache-Control', 'no-store')
        handler.send_header('Content-Length', str(len(code)))
        handler.end_headers()
        handler.wfile.write(code)
        return True
    if method == 'GET':
        handler._json(200, read_state())
        return True
    if method != 'POST' or path == '/api/autonomy/status.js':
        handler._json(405, {'error': 'Método inválido.'})
        return True
    auth = handler.headers.get('Authorization', '')
    expected = 'Bearer ' + TOKEN_FILE.read_text().strip()
    if not hmac.compare_digest(auth.encode(), expected.encode()):
        handler._json(401, {'error': 'Não autorizado.'})
        return True
    try:
        handler._json(200, update(read_json_body(handler)))
    except (ValueError, KeyError, TypeError):
        handler._json(400, {'error': 'Solicitação de autonomia inválida.'})
    return True
