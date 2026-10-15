"""Deploy using an interactive password; never persist the SSH password."""
import getpass
import json
from pathlib import Path
import secrets
import paramiko

root = Path(__file__).resolve().parent.parent
host = '100.119.119.83'
client = paramiko.SSHClient()
client.load_system_host_keys()
client.set_missing_host_key_policy(paramiko.RejectPolicy())
client.connect(host, username='root', password=getpass.getpass('Senha SSH do Control: '),
               look_for_keys=False, allow_agent=False, timeout=15)
config_path = root / 'data/ch8-config.json'
config = json.loads(config_path.read_text()) if config_path.exists() else {}
token = config.get('token') or secrets.token_urlsafe(48)
remote = '/opt/nino-ch8-gateway'
def command(cmd):
    _, out, err = client.exec_command(cmd)
    code = out.channel.recv_exit_status()
    if code:
        raise RuntimeError(err.read().decode()[:300])
    return out.read().decode()

command('install -d -m 700 /opt/nino-ch8-gateway')
with client.open_sftp() as sftp:
    sftp.put(str(root / 'scripts/ch8-gateway.py'), remote + '/gateway.py')
    with sftp.file(remote + '/token', 'w') as f:
        f.write(token)
    sftp.chmod(remote + '/token', 0o600)
    service = '''[Unit]
Description=Nino CONTROL private chat integration
After=network-online.target tailscaled.service control-action-inbox.service
[Service]
ExecStart=/usr/bin/python3 /opt/nino-ch8-gateway/gateway.py
Environment=NINO_GATEWAY_HOST=100.119.119.83
Restart=on-failure
UMask=0077
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/nino-ch8-gateway
[Install]
WantedBy=multi-user.target
'''
    with sftp.file('/etc/systemd/system/nino-control.service', 'w') as f:
        f.write(service)
command('python3 -m py_compile /opt/nino-ch8-gateway/gateway.py && systemctl daemon-reload && systemctl enable nino-control.service && systemctl restart nino-control.service')
config.update(enabled=True, url='http://' + host + ':8810', token=token, protocol='control')
config_path.write_text(json.dumps(config, indent=2), encoding='utf8')
print(command('systemctl is-active nino-control.service').strip())
client.close()
