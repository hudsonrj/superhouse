from pathlib import Path

p = Path("/etc/caddy/Caddyfile")
t = p.read_text()
start = t.find("control.ch8ai.com.br {")
print("START", start)
print(repr(t[start:start + 420]))
if "handle /cyd*" in t[start:start + 800]:
    print("already")
else:
    # insert handle immediately after opening brace
    brace = t.find("{", start)
    insert = "{\n\thandle /cyd* {\n\t\treverse_proxy 127.0.0.1:8790\n\t}"
    t = t[:brace] + insert + t[brace + 1 :]
    p.write_text(t)
    print("patched")
    start = t.find("control.ch8ai.com.br {")
    print(repr(t[start:start + 420]))
