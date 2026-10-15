#!/usr/bin/env python3
"""Gateway da Placa Amarela neste PC.

Puxa o CONTROL na nuvem e serve a placa:
  LAN  — HTTP na rede local (192.168.x:8788)
  TS   — Tailscale Funnel HTTPS (placa em outra rede)

Acoes da placa seguem para a mesma fila /api/action do app.
"""
from __future__ import annotations

import html
import json
import os
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from datetime import datetime

from cyd_api import BRT, ascii, encode_ctrl, snapshot as cyd_snapshot
from voice_pc import LAST_PCM
from voice_pc import listen as voice_listen
from voice_pc import speak as voice_speak

HOST = "0.0.0.0"
PORT = 8788
CLOUD = "https://control.ch8ai.com.br"
ACTION = CLOUD + "/api/action"
CHAT = CLOUD + "/api/chat"
RAG = CLOUD + "/api/rag"
POLL = 3.0
CTX = ssl._create_unverified_context()
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gateway.log")
DIARY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diario")
_TOKEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".kiosk_token")
_live = {}


def _kiosk_token() -> str:
    try:
        return open(_TOKEN_PATH, encoding="utf-8").read().strip()
    except OSError:
        return os.environ.get("KIOSK_TOKEN", "").strip()


KIOSK_TOKEN = _kiosk_token()


def cloud_url(path: str) -> str:
    return CLOUD + path


def cloud_headers(extra: dict | None = None) -> dict:
    h = {"Accept": "*/*", "Cache-Control": "no-store"}
    if extra:
        h.update(extra)
    if KIOSK_TOKEN:
        h["Cookie"] = "ck=" + KIOSK_TOKEN
    return h


def log(msg: str) -> None:
    line = time.strftime("%H:%M:%S ") + msg + "\n"
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
    try:
        sys.stdout.write(line)
        sys.stdout.flush()
    except OSError:
        pass

_lock = threading.RLock()
_ctrl = "CTRL/1\nHEALTH=OFF\nBRIEF=gateway ligando\n"
_stamp = 0.0
_ok = False
_plate_seen = 0.0
_gets = 0
_last_get_log = 0.0
_ask = {"agent": "", "q": "", "a": "", "at": 0.0}


def http_get(url: str, timeout: float = 8.0) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=cloud_headers())
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        return resp.status, resp.read()


def http_post(url: str, payload: bytes, timeout: float = 8.0) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        data=payload,
        headers=cloud_headers({"Content-Type": "application/json", "Accept": "application/json"}),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        return resp.status, resp.read()


def inject_ask(body: str) -> str:
    with _lock:
        row = dict(_ask)
    if not (row.get("a") or row.get("q")):
        return body
    line = f"ASK={ascii(row.get('agent') or '', 16)}|{ascii(row.get('q') or '', 36)}|{ascii(row.get('a') or 'consultando...', 160)}"
    if "\nASK=" in body:
        i = body.find("\nASK=")
        j = body.find("\n", i + 1)
        if j < 0:
            j = len(body)
        return body[: i + 1] + line + body[j:]
    return body.rstrip("\n") + "\n" + line + "\n"


def natural_text(s: str) -> str:
    t = (s or "").replace("\r", "\n")
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"_([^_]+)_", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"^\s*[-*•]\s+", "", t, flags=re.M)
    for ch in "*_#`~•►▪":
        t = t.replace(ch, "")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def _plain(s, n=72):
    t = " ".join(str(s or "").replace("\n", " ").split())
    return t[:n]


def _items(live, key):
    return [x for x in (live.get(key) or []) if isinstance(x, dict)]


def _open_tasks(live):
    out = []
    for t in _items(live, "tasks"):
        st = str(t.get("status") or t.get("state") or "").lower()
        if st in ("done", "feita", "closed", "completo"):
            continue
        out.append(t)
    return out


def _decisions(live):
    return [
        o
        for o in _items(live, "outbound")
        if o.get("needsApproval") or str(o.get("status") or "") == "needsApproval"
    ]


def _agenda_ok(live):
    rows = []
    for a in _items(live, "agenda") or _items(live, "events"):
        st = str(a.get("status") or "").lower()
        title = str(a.get("title") or "")
        if "cancel" in st or title.lower().startswith("cancelado"):
            continue
        rows.append(a)
    return rows


def day_brief(live: dict) -> str:
    if not isinstance(live, dict):
        return "Ainda nao tenho o retrato do dia."
    bits = []
    inbox = [m for m in (live.get("inbox") or []) if isinstance(m, dict)]
    unread = [m for m in inbox if m.get("unread")] or inbox
    if unread:
        nomes = []
        for m in unread[:4]:
            nomes.append(_plain(m.get("subject") or m.get("title") or m.get("from") or "um recado", 48))
        bits.append(
            f"Tem {len(unread)} recados pedindo voce. Os primeiros: " + "; ".join(nomes) + "."
        )
    else:
        bits.append("A caixa de recados esta tranquila.")
    tasks = [t for t in (live.get("tasks") or []) if isinstance(t, dict)]
    abertas = [
        t
        for t in tasks
        if str(t.get("status") or t.get("state") or "").lower()
        not in ("done", "feita", "closed", "completo", "done")
    ]
    if abertas:
        tit = [_plain(t.get("title") or t.get("name") or "tarefa", 40) for t in abertas[:4]]
        bits.append(f"Ha {len(abertas)} tarefas em aberto, como " + ", ".join(tit) + ".")
    else:
        bits.append("Nao vejo tarefa aberta agora.")
    projs = [p for p in (live.get("projects") or []) if isinstance(p, dict)]
    if projs:
        quentes = []
        for p in projs[:5]:
            st = str(p.get("status") or "").lower()
            nome = _plain(p.get("name") or p.get("title") or p.get("id") or "projeto", 32)
            if "quente" in st or "risk" in st or "atras" in st or "block" in st:
                quentes.append(nome)
        if quentes:
            bits.append("Nos projetos, merece atencao: " + ", ".join(quentes) + ".")
        else:
            bits.append(
                "Projetos na mesa: "
                + ", ".join(_plain(p.get("name") or p.get("title") or "projeto", 28) for p in projs[:4])
                + "."
            )
    agenda = [a for a in (live.get("agenda") or live.get("events") or []) if isinstance(a, dict)]
    if agenda:
        bits.append(
            "Na agenda: "
            + "; ".join(
                _plain((a.get("start") or "") + " " + (a.get("title") or a.get("name") or "compromisso"), 50)
                for a in agenda[:3]
            )
            + "."
        )
    out = [o for o in (live.get("outbound") or []) if isinstance(o, dict)]
    need = [o for o in out if o.get("needsApproval") or str(o.get("status") or "") == "needsApproval"]
    if need:
        bits.append(
            f"{len(need)} envios esperando seu ok, por exemplo "
            + _plain(need[0].get("subject") or need[0].get("title") or "um rascunho", 50)
            + "."
        )
    counsel = live.get("counsel") if isinstance(live.get("counsel"), dict) else {}
    if counsel.get("headline"):
        bits.append("Lembrete: " + _plain(counsel.get("headline"), 80) + ".")
    text = " ".join(bits)
    return text[:900]


def answer_work(q: str, live: dict) -> str:
    ql = (q or "").lower()
    if not isinstance(live, dict) or not live:
        return "Ainda nao tenho o retrato do seu dia. Pergunte de novo em instantes."

    recados = [m for m in _items(live, "inbox") if m.get("unread")] or _items(live, "inbox")
    tarefas = _open_tasks(live)
    decisoes = _decisions(live)
    agenda = _agenda_ok(live)
    projetos = _items(live, "projects")

    def recado(m):
        quem = _plain(m.get("sender") or m.get("from") or m.get("who") or "", 28)
        assunto = _plain(m.get("subject") or m.get("title") or "um recado", 56)
        return f"{assunto}" + (f", de {quem}" if quem else "")

    def tarefa(t):
        return _plain(t.get("title") or t.get("name") or "uma tarefa", 50)

    def decisao(o):
        para = _plain(o.get("to") or "", 24)
        assunto = _plain(o.get("subject") or o.get("title") or "um envio", 50)
        return assunto + (f" para {para}" if para else "")

    def compromisso(a):
        hora = _plain(a.get("start") or "", 5)
        tit = _plain(a.get("title") or a.get("name") or "compromisso", 48)
        return (hora + " " + tit).strip()

    if any(w in ql for w in ("decid", "aprova", "assina", "enviar", "rascunho", "ok do")):
        if not decisoes:
            return "Nao vejo nada esperando o seu ok para enviar agora."
        trecho = ". ".join(decisao(o) for o in decisoes[:3])
        n = len(decisoes)
        rotulo = "uma coisa esperando a sua decisao" if n == 1 else f"{n} coisas esperando a sua decisao"
        return f"Tem {rotulo}. {trecho}."

    if any(w in ql for w in ("agenda", "hoje", "reuniao", "reuniao", "compromisso", "calendario", "horario")):
        if not agenda:
            return "Na agenda nao aparece compromisso aberto neste recorte. Se quiser, falo das pendencias."
        trecho = "; ".join(compromisso(a) for a in agenda[:4])
        return f"Na agenda: {trecho}."

    if any(w in ql for w in ("tarefa", "afazer", "a fazer", "todo", "fazer hoje")):
        if not tarefas:
            return "Nao vejo tarefa em aberto neste recorte."
        trecho = ", ".join(tarefa(t) for t in tarefas[:5])
        return f"Tarefas em aberto: {trecho}."

    if any(w in ql for w in ("projeto", "vale", "allied", "hatkg", "neovale", "cpqd")):
        if not projetos:
            return "Nao tenho resumo de projeto neste recorte."
        partes = []
        for p in projetos[:4]:
            nome = _plain(p.get("name") or p.get("title") or "projeto", 36)
            res = _plain(p.get("summary") or p.get("status") or "", 90)
            partes.append(nome + (": " + res if res else ""))
        return "Nos projetos: " + " ".join(partes)

    if any(w in ql for w in ("penden", "recado", "email", "caixa", "mensagem", "inbox", "fila")):
        if not recados:
            return "A caixa de recados esta tranquila neste recorte."
        trecho = ". ".join(recado(m) for m in recados[:4])
        return f"Tem {len(recados)} recados na mesa. Os primeiros: {trecho}."

    if any(w in ql for w in ("oi", "ola", "bom dia", "boa tarde", "e ai", "estado", "resumo", "como esta", "como vai")):
        partes = []
        if decisoes:
            partes.append(f"{len(decisoes)} envios esperando o seu ok")
        if recados:
            partes.append(f"{len(recados)} recados")
        if tarefas:
            partes.append(f"{len(tarefas)} tarefas em aberto")
        if agenda:
            partes.append("compromissos na agenda, o primeiro e " + compromisso(agenda[0]))
        if not partes:
            return "Por aqui esta calmo. Sem recado urgente nem decisao parada neste recorte."
        extra = ""
        if decisoes:
            extra = " Eu comecaria por " + decisao(decisoes[0]) + "."
        return "Oi. No seu dia: " + ", ".join(partes) + "." + extra

    # pergunta livre: responde com o retrato do dia, sem sistema
    return natural_text(day_brief(live))


def ask_worker(agent: str, q: str, target: str) -> None:
    global _ask
    with _lock:
        live = dict(_live) if isinstance(_live, dict) else {}
    answer = answer_work(q, live)
    tech = (
        "firmware",
        "wifi",
        "wi-fi",
        "bluetooth",
        "gpio",
        "esp32",
        "gateway",
        "api",
        "ctrl/",
        "tailscale",
        "cyd",
        "http",
    )
    low = answer.lower()
    if any(w in low for w in tech):
        answer = answer_work("resumo do dia", live)
    answer = natural_text(answer)
    spoken = answer or "Nao consegui montar o seu dia agora. Pergunte de novo."
    with _lock:
        _ask = {
            "agent": agent,
            "q": q,
            "a": ascii(spoken, 280),
            "at": time.time(),
        }
    log(f"ask ok agent={agent} chars={len(spoken)}")
    voice_speak(spoken)


def inject_stamp(body: str) -> str:
    if not body.startswith("CTRL/1"):
        return body
    stamp = datetime.now(BRT).strftime("%Y-%m-%dT%H:%M:%S")
    key = "\nSTAMP="
    i = body.find(key)
    if i >= 0:
        j = body.find("\n", i + 1)
        if j < 0:
            j = len(body)
        return body[: i + len(key)] + stamp + body[j:]
    return body.replace("CTRL/1\n", f"CTRL/1\nSTAMP={stamp}\n", 1)


def inject_via(body: str, via: str) -> str:
    if not body.startswith("CTRL/1"):
        return body
    key = "\nVIA="
    i = body.find(key)
    if i >= 0:
        j = body.find("\n", i + 1)
        if j < 0:
            j = len(body)
        return body[: i + len(key)] + via + body[j:]
    return body.replace("CTRL/1\n", f"CTRL/1\nVIA={via}\n", 1)


def via_for(client_ip: str) -> str:
    # Funnel/Serve entra em 127.0.0.1; peers Tailscale usam 100.x
    if client_ip in ("127.0.0.1", "::1") or client_ip.startswith("100."):
        return "TS"
    return "LAN"


def poller() -> None:
    global _ctrl, _stamp, _ok, _live
    last_talk = 0.0
    fails = 0
    while True:
        try:
            code, raw = http_get(cloud_url("/live.json"))
            live = json.loads(raw.decode("utf-8", "replace")) if code == 200 else {}
            if live:
                with _lock:
                    _live = live
            text = encode_ctrl(cyd_snapshot(live)) if live else ""
            if text.startswith("CTRL/1"):
                with _lock:
                    _ctrl = text
                    _stamp = time.time()
                    _ok = True
                fails = 0
            else:
                fails += 1
                log(f"live.json http={code} bytes={len(raw)} (sem CTRL)")
        except Exception as exc:
            fails += 1
            with _lock:
                _ok = False
            if fails <= 3 or fails % 10 == 0:
                log(f"live.json falhou ({fails}): {exc}")
        now = time.time()
        if now - last_talk >= 15:
            last_talk = now
            with _lock:
                age = now - _stamp if _stamp else -1
                plate = now - _plate_seen if _plate_seen else -1
            log(f"poller ok={_ok} cloud_age={round(age, 1)}s plate_age={round(plate, 1)}s")
        time.sleep(POLL)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def _send(self, code: int, body, ctype: str = "text/plain; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(204, "")

    def do_GET(self):
        path = urlparse(self.path).path
        via = via_for(self.client_address[0])
        if path == "/cyd/voice.pcm":
            try:
                data = open(LAST_PCM, "rb").read()
            except OSError:
                data = b""
            self._send(200 if data else 404, data, "application/octet-stream")
            return
        if path in ("/cyd", "/cyd.txt", "/cyd/ctrl"):
            global _plate_seen, _gets, _last_get_log
            with _lock:
                body = inject_ask(inject_stamp(inject_via(_ctrl, via)))
                _plate_seen = time.time()
                _gets += 1
                n = _gets
                age = time.time() - _stamp if _stamp else -1
            self._send(200, body)
            now = time.time()
            if now - _last_get_log >= 30:
                _last_get_log = now
                log(f"placa via={via} polls={n} cloud_age={round(age, 1)}s")
        elif path in ("/hoje", "/cyd/hoje"):
            import datetime as _dt

            day = _dt.datetime.now().strftime("%Y-%m-%d")
            notes = []
            err = ""
            try:
                req = urllib.request.Request(
                    f"https://diario.ch8ai.com.br/api/day/{day}",
                    headers={"Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                for rec in payload.get("recordings") or []:
                    if rec.get("kind") == "note":
                        notes.extend(rec.get("entries") or [])
                    else:
                        for e in rec.get("entries") or []:
                            notes.append(e)
            except Exception as exc:
                err = str(exc)
            rows = []
            for item in notes[-50:]:
                when = html.escape(str(item.get("occurred_at") or "")[11:19])
                speaker = html.escape(str(item.get("speaker") or "Echo"))
                text = html.escape(item.get("text") or "")
                rows.append(
                    f'<div class="entry"><div class="meta">{when} · {speaker}</div>'
                    f'<div class="text">{text}</div></div>'
                )
            body = "".join(rows) or f'<p class="empty">Sem notas em {html.escape(day)}. {html.escape(err)}</p>'
            page = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/>
<meta http-equiv="refresh" content="12"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Hoje no Diário</title>
<style>
body{{margin:0;background:#f4efe4;color:#1c1712;font:18px/1.55 Palatino,serif}}
main{{max-width:720px;margin:0 auto;padding:40px 20px 80px}}
h1{{margin:0 0 8px}}
.lead{{color:#7a6b58}}
.entry{{padding:12px 0;border-top:1px dashed #d9cbb6}}
.meta{{font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;color:#7a6b58}}
a{{color:#8b1e1e}}
</style></head><body><main>
<h1>Hoje · {html.escape(day)}</h1>
<p class="lead">O site diario.ch8ai.com.br abre em 20/02/2027. Esta página mostra o dia de hoje direto da API. Atualiza sozinha.</p>
<p><a href="https://diario.ch8ai.com.br/">site oficial</a> — no calendário clique ‹ até <b>setembro 2026</b>, dia 20, e role até Anotações escritas.</p>
<article>{body}</article>
</main></body></html>"""
            self._send(200, page, "text/html; charset=utf-8")
        elif path in ("/diario", "/cyd/diary"):
            query = parse_qs(urlparse(self.path).query)
            days = []
            try:
                if os.path.isdir(DIARY_DIR):
                    days = sorted(
                        (name[:-4] for name in os.listdir(DIARY_DIR) if name.endswith(".txt")),
                        reverse=True,
                    )
            except OSError:
                days = []
            today = time.strftime("%Y-%m-%d")
            days = [d for d in days if d != today]
            days = [today] + days
            day = (query.get("day") or [today])[0]
            day = "".join(ch for ch in day if ch.isdigit() or ch == "-")[:10]
            lines = []
            path_txt = os.path.join(DIARY_DIR, f"{day}.txt")
            try:
                with open(path_txt, encoding="utf-8") as handle:
                    lines = [ln.rstrip("\n") for ln in handle if ln.strip()]
            except OSError:
                lines = []
            if path == "/cyd/diary" and "text/html" not in (self.headers.get("Accept") or ""):
                self._send(
                    200,
                    json.dumps({"ok": True, "day": day, "days": days, "lines": lines}),
                    "application/json",
                )
                return
            nav = "".join(
                '<a href="/diario?day={0}"{1}>{2}</a>'.format(
                    d,
                    ' aria-current="page"' if d == day else "",
                    ("Hoje · " + d) if d == today else d,
                )
                for d in days
            )
            entries = []
            for ln in lines:
                if " | " in ln:
                    parts = ln.split(" | ", 2)
                    stamp = parts[0][-8:] if len(parts[0]) >= 8 else parts[0]
                    kind = parts[1] if len(parts) > 1 else "NOTA"
                    text = parts[2] if len(parts) > 2 else ln
                    entries.append(
                        f'<div class="entry"><div class="meta">{html.escape(stamp)} · {html.escape(kind)}</div>'
                        f'<div class="text">{html.escape(text)}</div></div>'
                    )
                else:
                    entries.append(f'<div class="entry"><div class="text">{html.escape(ln)}</div></div>')
            body_html = "".join(entries) or '<p class="empty">Nada neste dia.</p>'
            page = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Diário</title>
<style>
body{{margin:0;background:#f4efe4;color:#1c1712;font:18px/1.55 Palatino,serif}}
main{{max-width:720px;margin:0 auto;padding:48px 20px 80px}}
h1{{margin:0 0 8px;font-size:2.4rem}}
p.lead{{color:#7a6b58;margin:0 0 24px}}
nav{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:24px}}
nav a{{color:#1c1712;text-decoration:none;border:1px solid #d9cbb6;background:#fffaf2;padding:6px 12px;border-radius:999px;font-size:.85rem}}
nav a[aria-current=page]{{background:#1c1712;color:#f4efe4}}
article{{background:#fffaf2;border:1px solid #d9cbb6;border-radius:18px;padding:22px 24px}}
.entry{{padding:14px 0;border-top:1px dashed #d9cbb6}}
.entry:first-child{{border-top:0}}
.meta{{font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;color:#7a6b58}}
.empty{{color:#7a6b58}}
</style></head><body><main>
<h1>Diário</h1>
<p class="lead">Eventos da placa e transcrições do Echo, no horário de Brasília.</p>
<nav>{nav}</nav>
<article>{body_html}</article>
</main></body></html>"""
            self._send(200, page, "text/html; charset=utf-8")
        elif path in ("/health", "/cyd/health"):
            with _lock:
                age = time.time() - _stamp if _stamp else -1
                plate = time.time() - _plate_seen if _plate_seen else -1
                ok = _ok and age >= 0 and age < 20
            self._send(
                200,
                json.dumps(
                    {
                        "ok": ok,
                        "via": via.lower(),
                        "age": round(age, 1),
                        "plate_age": round(plate, 1),
                        "port": PORT,
                        "funnel": "https://cpqd8nr2jg4.taile5dcde.ts.net",
                    }
                ),
                "application/json",
            )
        else:
            self._send(404, "not_found\n")

    def do_POST(self):
        path = urlparse(self.path).path
        max_len = 200000 if path.endswith("/stt") else 8192
        length = min(int(self.headers.get("Content-Length") or 0), max_len)
        raw = self.rfile.read(length) if length else b"{}"
        if path not in (
            "/cyd/ack",
            "/cyd/later",
            "/cyd/act",
            "/cyd/action",
            "/cyd/ask",
            "/cyd/rag",
            "/cyd/diary",
            "/cyd/listen",
            "/cyd/stt",
        ):
            self._send(404, "not_found\n")
            return
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            body = {}
        if path.endswith("/diary"):
            day = str(body.get("day") or time.strftime("%Y-%m-%d"))
            line = str(body.get("line") or "").replace("\n", " ").strip()
            day = "".join(ch for ch in day if ch.isdigit() or ch == "-")[:10] or time.strftime("%Y-%m-%d")
            if line:
                try:
                    os.makedirs(DIARY_DIR, exist_ok=True)
                    with open(os.path.join(DIARY_DIR, f"{day}.txt"), "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                except OSError as exc:
                    self._send(500, json.dumps({"ok": False, "error": str(exc)}), "application/json")
                    return
            log(f"POST /cyd/diary {day} {line[:80]}")
            self._send(200, json.dumps({"ok": True, "day": day}), "application/json")
            return
        if path.endswith("/stt"):
            heard = ""
            try:
                import numpy as np
                from speech_recognition import AudioData, Recognizer

                audio = AudioData(raw, 8000, 2)
                heard = (Recognizer().recognize_google(audio, language="pt-BR") or "").strip()
            except Exception as exc:
                log(f"stt fail {exc}")
            log(f"POST /cyd/stt heard={heard[:80] if heard else '-'} bytes={len(raw)}")
            if heard:
                threading.Thread(
                    target=ask_worker, args=("orquestrador", heard, "chief"), daemon=True
                ).start()
            self._send(
                200,
                json.dumps({"ok": bool(heard), "text": ascii(heard, 80) if heard else ""}, separators=(",", ":")),
                "application/json",
            )
            return
        if path.endswith("/listen"):
            heard = voice_listen(8)
            log(f"POST /cyd/listen heard={heard[:80] if heard else '-'} ask={'1' if heard else '0'}")
            plate_text = ascii(heard, 80) if heard else ""
            if heard:
                threading.Thread(
                    target=ask_worker, args=("orquestrador", heard, "chief"), daemon=True
                ).start()
            self._send(
                200,
                json.dumps({"ok": bool(heard), "text": plate_text}, separators=(",", ":")),
                "application/json",
            )
            return
        if path.endswith("/ask"):
            agent = str(body.get("agent") or "control")
            q = str(body.get("q") or body.get("text") or "").strip()
            target = str(body.get("target") or ("gemma" if agent.lower() == "gemma" else "chief"))
            if target not in ("gemma", "chief"):
                target = "chief"
            with _lock:
                _ask["agent"] = agent
                _ask["q"] = q
                _ask["a"] = "consultando CONTROL..."
                _ask["at"] = time.time()
            if q:
                threading.Thread(target=ask_worker, args=(agent, q, target), daemon=True).start()
                note = {
                    "id": f"ask-{int(time.time())}",
                    "kind": "note",
                    "payload": {"note": f"placa consulta {agent}: {q[:80]}", "agent": agent},
                    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "source": "placa",
                }
                try:
                    http_post(cloud_url("/api/action"), json.dumps(note).encode())
                except Exception:
                    pass
            log(f"POST /cyd/ask agent={agent} q={q[:40]}")
            self._send(200, json.dumps({"ok": True, "queued": True, "agent": agent}), "application/json")
            return
        if path.endswith("/rag"):
            payload = json.dumps(
                {
                    "id": str(body.get("id") or ""),
                    "draft": str(body.get("draft") or ""),
                    "subject": str(body.get("subject") or ""),
                    "to": str(body.get("to") or ""),
                    "company": str(body.get("company") or ""),
                    "channel": str(body.get("channel") or "outlook"),
                    "source": "placa",
                }
            ).encode("utf-8")
            try:
                last_code, last_body = http_post(cloud_url("/api/rag"), payload, timeout=20.0)
            except Exception as exc:
                last_code, last_body = 502, json.dumps({"ok": False, "error": str(exc)}).encode()
            log(f"POST /cyd/rag id={body.get('id')} -> {last_code}")
            self._send(last_code, last_body, "application/json")
            return
        kind = str(body.get("kind") or "")
        if path.endswith("/later") or body.get("later"):
            kind = "defer"
        elif not kind:
            kind = "approve" if path.endswith("/ack") else "note"
        payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
        if body.get("rsvp"):
            payload = {**payload, "rsvp": body.get("rsvp")}
        action = {
            "id": str(body.get("id") or ""),
            "kind": kind,
            "payload": payload,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": "placa",
        }
        last_body = b'{"ok":true}'
        last_code = 200
        try:
            last_code, last_body = http_post(cloud_url("/api/action"), json.dumps(action).encode())
        except Exception as exc:
            last_code, last_body = 502, json.dumps({"ok": False, "error": str(exc)}).encode()
        hide = cloud_url("/cyd/ack")
        hide_payload = json.dumps(
            {"id": action["id"], "later": kind == "defer"}
        ).encode()
        try:
            http_post(hide, hide_payload)
        except Exception:
            pass
        log(f"POST {path} kind={kind} id={action['id']} -> {last_code}")
        self._send(last_code, last_body, "application/json")


def main() -> None:
    threading.Thread(target=poller, daemon=True).start()
    try:
        httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        log(f"porta {PORT} ocupada/falhou: {exc}")
        raise
    log(f"placa gateway on {HOST}:{PORT} -> {CLOUD}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("gateway parado")
    except Exception as exc:
        log(f"gateway crash: {exc}")
        raise


if __name__ == "__main__":
    main()
