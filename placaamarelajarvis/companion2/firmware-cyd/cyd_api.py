#!/usr/bin/env python3
"""API compacta da Placa Amarela — frota, dia, futuro e gatilhos."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

LIVE = Path("/var/www/control-kiosk/live.json")
ORQ = Path("/opt/orquestra/state.json")
ACK = Path("/opt/placa/ack.json")
TRIG = Path("/opt/placa/triggers.json")
CONTROL_ACTION = os.environ.get("CONTROL_ACTION_URL", "http://127.0.0.1:8791/api/action")

BRT = timezone(timedelta(hours=-3))
SNOOZE_SEC = 4 * 3600

# Frota do kiosk CONTROL — Chief / Ops / Intel / Content.
ROSTER = [
    ("control", "control", "hub / parede", "CTL", "chief"),
    ("orquestrador", "orquestrador", "Chief · prato 3 MITs", "ORQ", "chief"),
    ("Servers CH8ai", "servers-ch8ai", "Ops · frota 8h/18h", "SRV", "ops"),
    ("agendas", "agendas", "Ops · calendario + msgs", "AGD", "ops"),
    ("vale", "vale", "Ops · Outlook/Teams Vale", "VAL", "ops"),
    ("alliedit", "alliedit", "Ops · Outlook/Teams Allied", "ALL", "ops"),
    ("Plaud", "plaud", "Intel · reunioes", "PLD", "intel"),
    ("ValeHatKG", "valehatkg", "Intel · RAG HatKG", "HKG", "intel"),
    ("Gemma", "gemma", "Intel · Ollama local", "GMA", "intel"),
    ("DeepSeek", "deepseek", "Intel · DeepSeek API", "DSK", "intel"),
    ("Jev", "jev", "Intel · triage inbox", "JEV", "intel"),
    ("Whatsapp", "whatsapp", "Ops · WhatsApp triage", "WA", "ops"),
    ("Diario", "diario", "Intel · diario.ch8ai", "DIA", "intel"),
    ("Conselheiro", "conselheiro", "Intel · conselho 18h", "CON", "intel"),
    ("x", "x", "Content · X + drafts", "X", "content"),
    ("heygen", "heygen", "Content · video sob brief", "HYG", "content"),
    ("Treinamento", "treinamento", "Content · estudo dados/IA", "TRN", "content"),
    ("Curriculo", "curriculo", "Ops · LinkedIn", "CUR", "ops"),
    ("Grana", "grana", "Ops · dinheiro", "GRN", "ops"),
    ("CONTROL Slack", "slack", "Ops · Slack CONTROL", "SLK", "ops"),
    ("Vale RAG", "vale-rag", "Intel · RAG Vale", "RAG", "intel"),
]
ID_TO_NAME = {rid.lower(): name for name, rid, *_ in ROSTER}
for name, rid, *_ in ROSTER:
    ID_TO_NAME[name.lower()] = name
ROSTER_INDEX = {name: i for i, (name, *_) in enumerate(ROSTER)}


def ascii(text, n=80):
    table = str.maketrans(
        "áàãâäéèêëíìîïóòõôöúùûüçÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    s = str(text or "").translate(table)
    s = "".join(ch if 32 <= ord(ch) < 127 else " " for ch in s)
    return " ".join(s.split())[:n]


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def persist_ack(data: dict):
    ACK.parent.mkdir(parents=True, exist_ok=True)
    data["at"] = time.time()
    ACK.write_text(json.dumps(data), encoding="utf-8")


def store():
    return load_json(ACK)


def hidden_ids():
    data = store()
    seen = set(data.get("ids") or [])
    now = time.time()
    later = data.get("later") or {}
    seen.update(k for k, until in later.items() if isinstance(until, (int, float)) and until > now)
    return seen


def save_ack(item_id: str):
    data = store()
    ids = list(dict.fromkeys((data.get("ids") or []) + [item_id]))[-80]
    later = data.get("later") or {}
    later.pop(item_id, None)
    persist_ack({"ids": ids, "later": later})


def save_later(item_id: str, seconds: int = SNOOZE_SEC):
    data = store()
    later = dict(data.get("later") or {})
    later[item_id] = time.time() + seconds
    persist_ack({"ids": data.get("ids") or [], "later": later})


def forward_control(item_id: str, kind: str, payload=None):
    if not item_id:
        return
    row = {
        "id": item_id,
        "kind": kind,
        "payload": payload or {},
        "at": datetime.now(timezone.utc).isoformat(),
        "source": "placa",
    }
    data = json.dumps(row, ensure_ascii=True).encode("utf-8")
    req = urllib.request.Request(
        CONTROL_ACTION,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        pass


def kind_for_ack(item_id: str) -> tuple[str, dict]:
    if item_id.startswith("t-"):
        return "task", {"status": "done"}
    if any(item_id.startswith(p) for p in ("hatkg-", "cpqd-", "hudsonrj-", "alliedit-", "vale-", "ev-")):
        return "rsvp", {"rsvp": "accept"}
    if item_id.startswith("sv-"):
        return "note", {"note": "placa: server tratado"}
    if str(item_id).startswith("out-"):
        return "approve", {"send": True}
    return "approve", {}


def save_trigger(agent: str, item_id: str, action: str):
    data = load_json(TRIG)
    items = list(data.get("items") or [])
    items.append(
        {
            "agent": ascii(agent, 24),
            "id": str(item_id or ""),
            "action": ascii(action or "go", 24),
            "at": time.time(),
        }
    )
    TRIG.parent.mkdir(parents=True, exist_ok=True)
    TRIG.write_text(json.dumps({"items": items[-40:], "at": time.time()}), encoding="utf-8")


def blob(*parts):
    return " ".join(str(p or "") for p in parts).lower()


def inbox_score(m):
    ch = (m.get("channel") or "").lower()
    sa = ascii(m.get("suggestedAction") or m.get("subject") or "", 80).lower()
    if ch in ("teams", "chat", "whatsapp"):
        return 80
    if sa.startswith("nenhum") or "ja respondido" in sa or "ja aceito" in sa:
        return 0
    if sa.startswith("so acompanhar") or sa.startswith("aguardar"):
        return 4
    if any(x in sa for x in ("rsvp", "aprovar", "enviar", "decidir")):
        return 70
    if any(x in sa for x in ("abrir", "pagar", "preencher", "confirmar", "checar", "ler o")):
        return 50
    return 20


def live_age_sec(live, now):
    raw = str(live.get("updatedAt") or "")
    if not raw:
        return 0
    try:
        ts = datetime.fromisoformat(raw)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=BRT)
        return max(0, int((now - ts).total_seconds()))
    except Exception:
        return 0


def canon_agent(label):
    lab = ascii(label, 24).lower()
    if lab in ID_TO_NAME:
        return ID_TO_NAME[lab]
    for name, rid, *_ in ROSTER:
        n = name.lower()
        if n == lab or n.startswith(lab) or lab.startswith(n) or rid.lower() == lab:
            return name
    return ""


def route_inbox(m):
    b = blob(m.get("company"), m.get("sender"), m.get("channel"), m.get("projectId"), m.get("subject"), m.get("source"))
    pid = (m.get("projectId") or "").lower()
    if (m.get("channel") or "").lower() in ("whatsapp", "wa"):
        return "Whatsapp"
    if any(x in b for x in ("whatsapp", "whats app")):
        return "Whatsapp"
    if "jev" in b or str(m.get("id") or "").startswith("jev-"):
        return "Jev"
    if "diario" in b:
        return "Diario"
    if "deepseek" in b:
        return "DeepSeek"
    if "slack" in b:
        return "CONTROL Slack"
    if "vale rag" in b or "valerag" in b:
        return "Vale RAG"
    if any(x in b for x in ("tesouro", "grana", "investimento", "selic")):
        return "Grana"
    if any(x in b for x in ("linkedin", "vaga", "curriculo")):
        return "Curriculo"
    if "allied" in b:
        return "alliedit"
    if any(x in b for x in ("hatkg", "openrag", "vale silver")):
        return "ValeHatKG"
    if pid in ("vale-integration", "projeto-seguro", "govgpt") or "vale" in b or "neovale" in b:
        return "vale"
    if pid == "projeto-5" or "cpqd" in b or "primeira" in b:
        return "agendas"
    if (m.get("channel") or "").lower() in ("teams", "calendar", "agenda", "meet"):
        return "agendas"
    return "control"


def route_task(t):
    b = blob(t.get("title"), t.get("projectId"), t.get("owner"))
    pid = t.get("projectId") or ""
    if pid == "dados-financas" or "allied" in b:
        return "alliedit"
    if pid in ("vale-integration", "projeto-seguro") or any(x in b for x in ("vale", "router", "neovale")):
        return "vale"
    if "hatkg" in b:
        return "ValeHatKG"
    if any(x in b for x in ("grana", "invest", "tesouro")):
        return "Grana"
    if any(x in b for x in ("curriculo", "candidat", "linkedin")):
        return "Curriculo"
    if any(x in b for x in ("treino", "curso", "zoomcamp")):
        return "Treinamento"
    if pid == "projeto-5" or "cpqd" in b:
        return "agendas"
    return "control"


def route_event(a):
    co = (a.get("company") or "").lower()
    title = (a.get("title") or "").lower()
    if "allied" in co:
        return "alliedit"
    if "hatkg" in co or "hatkg" in title:
        return "ValeHatKG"
    if "vale" in co or "neovale" in title:
        return "vale"
    return "agendas"


def route_outbound(o):
    b = blob(o.get("company"), o.get("to"), o.get("channel"), o.get("subject"))
    if "allied" in b:
        return "alliedit"
    if "hatkg" in b:
        return "ValeHatKG"
    if "vale" in b:
        return "vale"
    return "control"


def ev_line(a):
    return ascii(f"{a.get('start', '')} {a.get('title', '')}", 36)


PROJECT_COMPANY = {
    "vale-integration": "Vale",
    "projeto-seguro": "Vale",
    "projeto-5": "CPQD",
    "dados-financas": "Allied",
    "govgpt": "CH8",
}


def norm_company(raw, pid=""):
    pid = (pid or "").lower()
    if pid in PROJECT_COMPANY:
        return PROJECT_COMPANY[pid]
    s = ascii(raw or "", 24)
    b = s.lower()
    if "hatkg" in b:
        return "HatKG"
    if "vale" in b or "neovale" in b:
        return "Vale"
    if "cpqd" in b or "primeira" in b:
        return "CPQD"
    if "allied" in b:
        return "Allied"
    if "ch8" in b:
        return "CH8"
    if "hudson" in b:
        return "Hudson"
    if not s or ":" in s or len(s.split()) > 2:
        return "outros"
    return s[:10]


def bump(bag, key, field, n=1):
    if not key:
        return
    row = bag.setdefault(key, {"p": 0, "m": 0, "open": 0, "done": 0})
    row[field] = row.get(field, 0) + n


def snapshot(live=None):
    live = live if isinstance(live, dict) and live else load_json(LIVE)
    hidden = hidden_ids()
    now = datetime.now(BRT)
    today = now.strftime("%Y-%m-%d")
    hm = now.strftime("%H:%M")

    inbox = [m for m in live.get("inbox") or [] if m.get("id") not in hidden and m.get("unread")]
    todo = [
        t
        for t in live.get("tasks") or []
        if t.get("id") not in hidden and t.get("status") in ("todo", "doing", "blocked")
    ]
    agenda = live.get("agenda") or []
    meetings = live.get("meetings") or []
    projects = live.get("projects") or []
    cycles = live.get("cycles") or []

    apps = []
    for srv in live.get("servers") or []:
        for app in srv.get("apps") or []:
            st = "UP" if app.get("status") == "up" else "DOWN"
            apps.append(
                {
                    "n": ascii(app.get("name") or app.get("id"), 20),
                    "st": st,
                    "host": ascii(srv.get("id"), 12),
                    "id": ascii(app.get("id") or app.get("name"), 24),
                }
            )
    apps.sort(key=lambda a: 0 if a["st"] != "UP" else 1)
    down = [a for a in apps if a["st"] != "UP"]

    tagged = []
    for o in live.get("outbound") or []:
        st = (o.get("status") or "").lower()
        if not (o.get("needsApproval") or st == "needsapproval"):
            continue
        if o.get("id") in hidden:
            continue
        tagged.append(
            {
                "kind": "IN",
                "ag": route_outbound(o),
                "a": ascii(o.get("subject") or "Aprovar e enviar", 36),
                "b": ascii(o.get("to") or o.get("channel"), 20),
                "id": o.get("id"),
            }
        )
    ranked = sorted(inbox, key=inbox_score, reverse=True)
    for m in ranked:
        who = ascii(m.get("sender"), 16)
        ch = (m.get("channel") or "").lower()
        if ch == "whatsapp":
            who = ascii("WA " + who, 20)
        elif ch in ("teams", "chat"):
            who = ascii("Teams " + who, 20)
        tagged.append(
            {
                "kind": "IN",
                "ag": route_inbox(m),
                "a": ascii(m.get("suggestedAction") or m.get("subject"), 36),
                "b": who,
                "id": m.get("id"),
            }
        )
    for t in todo:
        ag = route_task(t)
        tagged.append(
            {
                "kind": "TK",
                "ag": ag,
                "a": ascii(t.get("title"), 36),
                "b": ascii(t.get("due") or t.get("status"), 12),
                "id": t.get("id"),
            }
        )
    for a in agenda:
        if (a.get("status") or "") == "done":
            continue
        tagged.append(
            {
                "kind": "EV",
                "ag": route_event(a),
                "a": ev_line(a),
                "b": ascii(a.get("company"), 14),
                "id": a.get("id") or f"ev-{a.get('start')}",
            }
        )
    for mt in meetings[:4]:
        tagged.append(
            {
                "kind": "EV",
                "ag": "Plaud",
                "a": ascii(mt.get("title"), 36),
                "b": ascii(f"{mt.get('empresa')} {mt.get('when')}", 20),
                "id": mt.get("id"),
            }
        )
    for p in projects[:4]:
        pid = p.get("id") or ""
        ag = "ValeHatKG" if pid in ("vale-integration", "projeto-seguro") else "control"
        tagged.append(
            {
                "kind": "TK",
                "ag": ag,
                "a": ascii(p.get("name"), 36),
                "b": ascii(p.get("status"), 16),
                "id": p.get("id"),
            }
        )
    for a in down:
        tagged.append(
            {
                "kind": "SV",
                "ag": "Servers CH8ai",
                "a": ascii(f"{a['n']} caiu", 36),
                "b": a["host"],
                "id": f"sv-{a['id']}",
            }
        )
    jobs = ((live.get("jobApplications") or {}).get("submitted") or [])[:2]
    for j in jobs:
        tagged.append(
            {
                "kind": "TK",
                "ag": "Curriculo",
                "a": ascii(j.get("title"), 36),
                "b": ascii(j.get("company"), 16),
                "id": j.get("id"),
            }
        )
    tr = live.get("training") or {}
    if tr.get("headline"):
        tagged.append(
            {
                "kind": "TK",
                "ag": "Treinamento",
                "a": ascii(tr.get("headline"), 36),
                "b": ascii(tr.get("status"), 12),
                "id": "trn-head",
            }
        )
    inv = live.get("investments") or {}
    if inv.get("headline"):
        tagged.append(
            {
                "kind": "IN",
                "ag": "Grana",
                "a": ascii(inv.get("headline"), 36),
                "b": "Grana",
                "id": "grana-head",
            }
        )
    for note in live.get("fleetNotes") or []:
        if not isinstance(note, dict):
            continue
        tagged.append(
            {
                "kind": "IN",
                "ag": canon_agent(note.get("agent") or "Jev") or "Jev",
                "a": ascii(note.get("text") or note.get("headline"), 36),
                "b": ascii(note.get("agent") or "Jev", 16),
                "id": note.get("id") or "jev-note",
            }
        )
    cn = live.get("counsel") or {}
    if cn.get("headline"):
        tagged.append(
            {
                "kind": "IN",
                "ag": "Conselheiro",
                "a": ascii(cn.get("headline"), 36),
                "b": "Conselheiro",
                "id": "con-head",
            }
        )

    load, head, tagged_fix = {}, {}, []
    for it in tagged:
        name = canon_agent(it["ag"])
        if not name:
            continue
        it["ag"] = name
        tagged_fix.append(it)
        load[name] = load.get(name, 0) + 1
        head.setdefault(name, it["a"])
    tagged = tagged_fix

    cycle_by = {}
    for c in cycles:
        name = canon_agent(c.get("owner") or "")
        if not name:
            continue
        prev = cycle_by.get(name)
        st = (c.get("status") or "").lower()
        if prev is None or st in ("running", "blocked", "doing"):
            cycle_by[name] = c

    agents = []
    for name, rid, role, short, team in ROSTER:
        cyc = cycle_by.get(name)
        st = ((cyc or {}).get("status") or "").lower()
        run = st in ("running", "blocked", "doing")
        act = ascii((cyc or {}).get("name") or "", 22)
        agents.append(
            {
                "n": name,
                "st": "RUN" if run else "IDLE",
                "act": act,
                "nwork": int(load.get(name, 0)),
                "head": ascii(head.get(name) or (cyc or {}).get("note") or role, 36),
                "role": ascii(role, 40),
                "short": short,
                "team": team,
                "evh": 0,
                "rank": 0 if run else 1,
            }
        )
    # ordem da parede do kiosk (Chief / Ops / Intel / Content)

    def timed(a):
        st, en = a.get("start") or "", a.get("end") or ""
        if st in ("00:00", "0:00") and en in ("23:59", "24:00"):
            return False
        return True

    open_ev = [a for a in agenda if timed(a) and (a.get("status") or "") != "done"]
    hoje_ev = sorted(
        [a for a in open_ev if (a.get("date") or "") == today],
        key=lambda a: a.get("start") or "",
    )
    remaining = [a for a in hoje_ev if (a.get("start") or "") >= hm]
    futuro_ev = sorted(
        [a for a in open_ev if (a.get("status") == "later") or (a.get("date") or "") > today],
        key=lambda a: ((a.get("date") or ""), a.get("start") or ""),
    )
    done_today = any((a.get("date") or "") == today and a.get("status") == "done" for a in agenda)
    if remaining:
        hoje_line = ascii(" / ".join(ev_line(a) for a in remaining[:2]), 48)
    elif hoje_ev or done_today:
        hoje_line = "dia encerrado"
    else:
        hoje_line = "sem agenda hoje"
    futuro_line = ascii(" / ".join(ev_line(a) for a in futuro_ev[:2]), 48) or "nada depois na grade"
    next_src = remaining[0] if remaining else (futuro_ev[0] if futuro_ev else {})

    health = ascii(live.get("fleetHealth") or "ok", 8).upper() or "OK"
    if down or inbox or any(c.get("status") == "blocked" for c in cycles):
        health = "WARN"
    age = live_age_sec(live, now)
    if age > 7200:
        health = "OLD"
    elif age > 1800 and health == "OK":
        health = "WARN"

    all_apps = []
    for srv in live.get("servers") or []:
        all_apps.extend(srv.get("apps") or [])
    hosts_up = sum(1 for a in all_apps if a.get("status") == "up")
    hosts_dn = max(0, len(all_apps) - hosts_up)

    by_co = {}
    for p in projects:
        co = norm_company(p.get("name") or p.get("company"), p.get("id"))
        bump(by_co, co, "p")
    meet_today = [a for a in agenda if timed(a) and (a.get("date") or "") == today]
    for a in meet_today:
        bump(by_co, norm_company(a.get("company") or a.get("title")), "m")
    for t in live.get("tasks") or []:
        co = norm_company(t.get("title"), t.get("projectId"))
        st = (t.get("status") or "").lower()
        bump(by_co, co, "done" if st == "done" else "open")
    for ds in live.get("doneSignals") or []:
        bump(by_co, norm_company(ds.get("taskHint") or ds.get("evidence") or ""), "done")

    co_rows = sorted(by_co.items(), key=lambda kv: (-(kv[1]["p"] + kv[1]["m"] + kv[1]["open"] + kv[1]["done"]), kv[0]))[:6]
    day_map = {}
    for a in agenda:
        if not timed(a):
            continue
        day = a.get("date") or ""
        if not day:
            continue
        rec = day_map.setdefault(day, {"n": 0, "done": 0})
        rec["n"] += 1
        if (a.get("status") or "") == "done":
            rec["done"] += 1
    dy_rows = []
    for day in sorted(day_map.keys())[:5]:
        rec = day_map[day]
        label = day[8:10] + "/" + day[5:7] if len(day) >= 10 else day
        dy_rows.append({"d": label, "n": rec["n"], "done": rec["done"]})

    jobs_n = int((live.get("jobApplications") or {}).get("submittedCount") or 0)
    blk = sum(1 for c in cycles if (c.get("status") or "") == "blocked")
    done_n = len(live.get("doneSignals") or []) + sum(
        1 for a in agenda if timed(a) and (a.get("date") or "") == today and a.get("status") == "done"
    )

    return {
        "t": live.get("updatedAt") or "",
        "health": health,
        "alerts": len(inbox) + sum(
            1
            for o in live.get("outbound") or []
            if (o.get("needsApproval") or (o.get("status") or "").lower() == "needsapproval")
            and o.get("id") not in hidden
        ),
        "tasks": len(todo),
        "agents": len(agents),
        "working": sum(1 for a in agents if a["st"] == "RUN"),
        "down": len(down),
        "hoje": hoje_line,
        "futuro": futuro_line,
        "next": ascii(ev_line(next_src) if next_src else "", 42),
        "brief": ascii(
            (
                f"live {age // 3600}h atrasado  "
                if age > 1800
                else ""
            )
            + f"{len(inbox)} inbox {len(todo)} tarefas {len(down)} down",
            48,
        ),
        "foco": ascii(
            next((x["a"] for x in tagged if x["kind"] == "IN"), None)
            or (todo[0].get("title") if todo else hoje_line),
            42,
        ),
        "ancora": ascii(
            ((live.get("ancora") or {}) if isinstance(live.get("ancora"), dict) else {}).get("headline")
            or (live.get("ancora") if isinstance(live.get("ancora"), str) else "")
            or "",
            48,
        ),
        "consel": ascii(((live.get("counsel") or {}) or {}).get("headline") or "", 48),
        "mit": ascii(
            " · ".join(
                [
                    x
                    for x in [
                        ascii(((live.get("counsel") or {}) or {}).get("headline") or "", 28),
                        ascii(ev_line(remaining[0]) if remaining else "", 24),
                        next(
                            (
                                ascii(p.get("name"), 22)
                                for p in projects
                                if "quente" in (p.get("status") or "").lower()
                            ),
                            "",
                        ),
                    ]
                    if x
                ][:3]
            )
            or hoje_line,
            72,
        ),
        "inbox": [x for x in tagged if x["kind"] == "IN"][:8],
        "tasks_list": [x for x in tagged if x["kind"] == "TK"][:8],
        "agenda": [x for x in tagged if x["kind"] == "EV"][:6],
        "servers": [x for x in tagged if x["kind"] == "SV"][:6],
        "agents_list": agents[:24],
        "kpi": [
            len(projects),
            len(meet_today),
            done_n,
            len(inbox),
            hosts_up,
            hosts_dn,
            jobs_n,
            blk,
        ],
        "companies": [
            {
                "n": ascii(name, 10),
                "p": int(row["p"]),
                "m": int(row["m"]),
                "open": int(row["open"]),
                "done": int(row["done"]),
            }
            for name, row in co_rows
            if name
        ],
        "days": dy_rows,
    }


def pack_item(x):
    return f"{x['ag']}|{x['a']}|{x['b']}|{x['id']}"


def encode_ctrl(p: dict) -> str:
    lines = [
        "CTRL/1",
        f"HEALTH={p['health']}",
        f"ALERTS={p['alerts']}",
        f"TASKS={p['tasks']}",
        f"AGENTS={p['agents']}",
        f"WORKING={p['working']}",
        f"DOWN={p['down']}",
        f"HOJE={p['hoje']}",
        f"FUTURO={p['futuro']}",
        f"NEXT={p['next']}",
        f"BRIEF={p['brief']}",
        f"FOCO={p.get('foco') or p['brief']}",
        f"MIT={p.get('mit') or ''}",
        f"ANC={p.get('ancora') or ''}",
        f"CON={p.get('consel') or ''}",
        f"STAMP={datetime.now(BRT).strftime('%Y-%m-%dT%H:%M:%S')}",
        "KPI=" + "|".join(str(int(x)) for x in (p.get("kpi") or [0] * 8)[:8]),
    ]
    for i, a in enumerate(p["agents_list"][:24], 1):
        lines.append(
            f"AG{i}={a['n']}|{a['st']}|{a['act']}|{a['nwork']}|{a['head']}|{a['role']}|{a.get('short') or a['n'][:3]}|{a.get('team') or 'ops'}"
        )
    for i, m in enumerate(p["inbox"][:8], 1):
        lines.append(f"IN{i}={pack_item(m)}")
    for i, t in enumerate(p["tasks_list"][:8], 1):
        lines.append(f"TK{i}={pack_item(t)}")
    for i, a in enumerate(p["agenda"][:6], 1):
        lines.append(f"EV{i}={pack_item(a)}")
    for i, s in enumerate(p["servers"][:6], 1):
        lines.append(f"SV{i}={pack_item(s)}")
    for i, c in enumerate((p.get("companies") or [])[:6], 1):
        lines.append(f"CO{i}={c['n']}|{c['p']}|{c['m']}|{c['open']}|{c['done']}")
    for i, d in enumerate((p.get("days") or [])[:5], 1):
        lines.append(f"DY{i}={d['d']}|{d['n']}|{d['done']}")
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
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
        snap = snapshot()
        if path in ("/cyd", "/cyd.txt", "/cyd/ctrl"):
            self._send(200, encode_ctrl(snap))
        elif path in ("/cyd.json", "/cyd/json"):
            self._send(200, json.dumps(snap, ensure_ascii=True), "application/json")
        elif path in ("/health", "/cyd/health"):
            self._send(200, json.dumps({"ok": True, "health": snap["health"]}), "application/json")
        else:
            self._send(404, "not_found\n")

    def do_POST(self):
        path = urlparse(self.path).path
        length = min(int(self.headers.get("Content-Length") or 0), 4096)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            body = {}
        if path in ("/cyd/ack", "/cyd/act", "/cyd/later"):
            item_id = str(body.get("id") or "")
            agent = str(body.get("agent") or "")
            action = str(body.get("action") or "")
            kind = str(body.get("kind") or "")
            payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
            if path.endswith("/later") or body.get("later") or kind == "defer":
                if item_id:
                    save_later(item_id)
                    forward_control(item_id, "defer", {})
            elif kind in ("reject", "approve", "rsvp", "task", "note"):
                if item_id:
                    if kind == "reject":
                        save_ack(item_id)
                    elif kind != "note":
                        save_ack(item_id)
                    forward_control(item_id, kind, payload)
            elif path.endswith("/act") or agent:
                save_trigger(agent, item_id, action or "go")
                note = f"placa {ascii(agent, 18)} {ascii(action or 'go', 12)}".strip()
                forward_control(item_id or f"ag-{ascii(agent, 16)}", "note", {"note": note})
            elif item_id:
                save_ack(item_id)
                kind, payload = kind_for_ack(item_id)
                forward_control(item_id, kind, payload)
            self._send(200, json.dumps({"ok": True, "id": item_id, "agent": agent}), "application/json")
            return
        self._send(404, "not_found\n")


if __name__ == "__main__":
    port = int(os.environ.get("PLACA_PORT", "8790"))
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
