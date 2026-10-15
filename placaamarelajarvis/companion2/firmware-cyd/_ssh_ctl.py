import os
import paramiko

pw = os.environ.get("PLACA_SSH")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("100.119.119.83", username="root", password=pw, timeout=20, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=40):
    i, o, e = c.exec_command(cmd, timeout=timeout)
    out = o.read().decode("utf-8", "replace")
    err = e.read().decode("utf-8", "replace")
    print(f"=== {cmd[:140]} ===")
    if out:
        print(out.rstrip()[:10000])
    if err:
        print("ERR", err[-800:].rstrip())


run("python3 - <<'PY'\nfrom pathlib import Path\np=Path('/etc/caddy/Caddyfile')\nt=p.read_text()\nold='''\t@anon {\n\t\tnot header_regexp Cookie (^|;\\s*)ck={$KIOSK_TOKEN}(;|$)\n\t\tnot remote_ip {$KIOSK_IPS}\n\t\tnot query k={$KIOSK_TOKEN}\n\t}'''\nnew='''\t@anon {\n\t\tnot header_regexp Cookie (^|;\\s*)ck={$KIOSK_TOKEN}(;|$)\n\t\tnot remote_ip {$KIOSK_IPS}\n\t\tnot query k={$KIOSK_TOKEN}\n\t\tnot path /cyd*\n\t}'''\nif old not in t:\n    print('BLOCK_NOT_FOUND')\n    i=t.find('@anon')\n    print(repr(t[i:i+350]))\nelse:\n    p.write_text(t.replace(old,new,1))\n    print('PATCHED')\nPY")
run("systemctl reload caddy")
run("systemctl is-active placa-cyd.service caddy")
run("curl -sS -o /tmp/cyd.out -w '%{http_code} %{size_download}' https://control.ch8ai.com.br/cyd")
run("head -c 200 /tmp/cyd.out; echo")
c.close()
