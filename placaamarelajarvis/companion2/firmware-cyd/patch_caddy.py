from pathlib import Path

api = Path("/opt/placa/cyd_api.py")
t = api.read_text()
needle = '"st": "RUN" if a.get("lastType") in ("shell_command", "computer_use_session", "mcp_tool_call") else "IDLE"'
repl = '"st": "RUN" if str(a.get("lastTs") or "")[:13] >= __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H") else "IDLE"'
if needle in t:
    api.write_text(t.replace(needle, repl, 1))
    print("api patched")
else:
    print("api needle missing")

caddy = Path("/etc/caddy/Caddyfile")
ct = caddy.read_text()
if "handle /cyd*" in ct:
    print("caddy already has cyd")
else:
    marker = "control.ch8ai.com.br {\nencode zstd gzip\n"
    insert = "control.ch8ai.com.br {\nhandle /cyd* {\nreverse_proxy 127.0.0.1:8790\n}\nencode zstd gzip\n"
    if marker in ct:
        caddy.write_text(ct.replace(marker, insert, 1))
        print("caddy patched")
    else:
        print("caddy marker missing")
        i = ct.find("control.ch8ai.com.br")
        print(repr(ct[i:i + 250]))
