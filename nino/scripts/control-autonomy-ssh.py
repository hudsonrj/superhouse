"""Read/deploy the Control autonomy module with an interactive SSH password."""
import getpass
from pathlib import Path
import shlex
import sys
import paramiko

root = Path(__file__).resolve().parent.parent
client = paramiko.SSHClient()
client.load_system_host_keys()
client.set_missing_host_key_policy(paramiko.RejectPolicy())
client.connect('100.119.119.83', username='root', password=getpass.getpass('Senha SSH do Control: '), look_for_keys=False, allow_agent=False, timeout=15)
def execute(command):
    _, out, err = client.exec_command(command, timeout=30)
    result = out.read().decode()
    if out.channel.recv_exit_status():
        raise RuntimeError(err.read().decode()[:300])
    return result.strip()
try:
    command = execute('systemctl show -p ExecStart --value control-action-inbox.service')
    import re
    matches = re.findall(r'(/[\w./-]+/action-inbox\.py)\b', command)
    if len(set(matches)) != 1:
        raise RuntimeError('Nao foi possivel localizar o modulo ativo.')
    remote = matches[0].rsplit('/', 1)[0] + '/control_autonomy.py'
    local = root / 'scripts/control-autonomy-server.py'
    with client.open_sftp() as sftp:
        if '--deploy' not in sys.argv:
            sftp.get(remote, str(local))
            print('Modulo ativo obtido para revisao.')
        else:
            backup = remote + '.before-nino-sensor'
            try:
                sftp.stat(backup)
            except FileNotFoundError:
                execute('cp -- ' + shlex.quote(remote) + ' ' + shlex.quote(backup))
            sftp.put(str(local), remote + '.new')
            execute('python3 -m py_compile ' + shlex.quote(remote + '.new'))
            execute('mv -- ' + shlex.quote(remote + '.new') + ' ' + shlex.quote(remote))
            try:
                execute('systemctl restart control-action-inbox.service')
            except Exception:
                execute('cp -- ' + shlex.quote(backup) + ' ' + shlex.quote(remote))
                execute('systemctl restart control-action-inbox.service')
                raise
            print(execute('systemctl is-active control-action-inbox.service'))
finally:
    client.close()
