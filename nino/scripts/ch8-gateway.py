"""Private Nino adapter for the existing CONTROL kiosk chat API."""
import concurrent.futures
from contextlib import contextmanager
import hmac
import json
import os
from pathlib import Path
import sqlite3
import threading
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(os.environ.get('NINO_GATEWAY_DIR', '/opt/nino-ch8-gateway'))
TOKEN = (ROOT / 'token').read_text().strip()
DB = ROOT / 'jobs.sqlite'
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2)
LOCK = threading.Lock()

@contextmanager
def database():
    connection = sqlite3.connect(DB)
    try:
        with connection:
            yield connection
    finally:
        connection.close()

with database() as db:
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, text TEXT, status TEXT, response TEXT, error TEXT)')
    # Do not replay interrupted requests: the upstream may already have stored them.
    db.execute("UPDATE jobs SET status='error', error='Servico reiniciado; confira o pedido no Control antes de reenviar.' WHERE status='pending'")


def run(job_id, text):
    try:
        body = json.dumps({'text': text, 'clientId': 'nino-' + job_id, 'target': 'Gemma'}).encode()
        req = urllib.request.Request('http://127.0.0.1:8791/api/chat', data=body,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=150) as res:
            result = json.load(res)
        reply = result.get('reply') or {}
        answer = reply.get('text')
        if not isinstance(answer, str) or not answer.strip() or answer.startswith('(Gemma offline:'):
            raise ValueError('O modelo do Control nao retornou uma resposta valida.')
        with database() as db:
            db.execute("UPDATE jobs SET status='done', response=? WHERE id=?", (answer, job_id))
    except Exception as exc:
        # Do not return upstream exception details, which can contain credentials.
        error = str(exc) if isinstance(exc, ValueError) else 'Falha ao consultar o modelo do Control.'
        with database() as db:
            db.execute("UPDATE jobs SET status='error', error=? WHERE id=?", (error, job_id))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def auth(self):
        if not hmac.compare_digest(self.headers.get('Authorization', '').encode(), ('Bearer ' + TOKEN).encode()):
            self.send(401, {'error': 'Nao autorizado.'})
            self.close_connection = True
            return False
        return True

    def do_GET(self):
        if not self.auth():
            return
        if self.path == '/health':
            self.send(200, {'ok': True, 'service': 'nino-control', 'target': 'Gemma'})
            return
        if self.path.startswith('/jobs/'):
            job_id = self.path[len('/jobs/'):]
            with database() as db:
                row = db.execute('SELECT status,response,error FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row:
                self.send(200, {'id': job_id, 'status': row[0], 'response': row[1], 'error': row[2]})
                return
        self.send(404, {'error': 'Pedido nao encontrado.'})

    def do_POST(self):
        if not self.auth():
            return
        if self.path != '/chat':
            self.send(404, {'error': 'Rota nao encontrada.'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 32768:
                raise ValueError()
            self.connection.settimeout(10)
            data = json.loads(self.rfile.read(size))
            messages = data['messages']
            if not isinstance(messages, list) or len(messages) != 1 or not isinstance(messages[0], dict) or messages[0].get('role') != 'user':
                raise ValueError()
            text = messages[0]['content']
            if not isinstance(text, str) or not text.strip() or len(text) > 8000:
                raise ValueError()
            job_id = str(uuid.UUID(data['requestId']))
        except (ValueError, KeyError, TypeError, IndexError):
            self.send(400, {'error': 'Pedido invalido.'})
            self.close_connection = True
            return
        with LOCK, database() as db:
            old = db.execute('SELECT text FROM jobs WHERE id=?', (job_id,)).fetchone()
            if old and old[0] != text:
                self.send(409, {'error': 'Identificador ja usado para outro pedido.'})
                return
            if not old:
                pending = db.execute("SELECT count(*) FROM jobs WHERE status='pending'").fetchone()[0]
                if pending >= 8:
                    self.send(429, {'error': 'Fila cheia. Tente depois.'})
                    return
                db.execute("INSERT INTO jobs(id,text,status) VALUES(?,?,'pending')", (job_id, text))
                db.commit()
                POOL.submit(run, job_id, text)
        self.send(202, {'id': job_id, 'status': 'pending'})


if __name__ == '__main__':
    ThreadingHTTPServer((os.environ['NINO_GATEWAY_HOST'], 8810), Handler).serve_forever()
