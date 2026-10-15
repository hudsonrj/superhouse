"""Instala o estado de autonomia no Control, sem salvar a senha SSH."""
import getpass
import re
import shlex
from pathlib import Path
import paramiko
from find_index import application_index, candidates

HERE = Path(__file__).resolve().parent
HOST = '100.119.119.83'
client = paramiko.SSHClient()
client.load_system_host_keys()
client.set_missing_host_key_policy(paramiko.RejectPolicy())
client.connect(HOST, username='root', password=getpass.getpass('Senha SSH do Control (não será salva): '),
               look_for_keys=False, allow_agent=False, timeout=15)

def execute(command):
    _, output, error = client.exec_command(command, timeout=30)
    result = output.read().decode()
    if output.channel.recv_exit_status():
        raise RuntimeError('Comando remoto falhou: ' + error.read().decode()[:250])
    return result.strip()

def script_path(service, filename):
    value = execute(f'systemctl show -p ExecStart --value {shlex.quote(service)}')
    matches = re.findall(r'(/[\w./-]+/' + re.escape(filename) + r')\b', value)
    if len(set(matches)) != 1:
        raise RuntimeError(f'Não foi possível identificar o arquivo ativo de {service}.')
    return matches[0]

try:
    action_file = script_path('control-action-inbox.service', 'action-inbox.py')
    gateway_file = script_path('nino-control.service', 'gateway.py')
    with client.open_sftp() as sftp:
        def read(file):
            with sftp.file(file, 'rb') as handle:
                return handle.read()
        def write(file, value):
            with sftp.file(file, 'wb') as handle:
                handle.write(value)
        action = read(action_file).decode('utf-8')
        gateway = read(gateway_file).decode('utf-8')
        index_candidates = []
        application = None
        try:
            caddy = read('/etc/caddy/Caddyfile').decode('utf-8')
            listeners = execute("ss -ltnp 'sport = :8792'")
            process_ids = set(re.findall(r'pid=(\d+)', listeners))
            if len(process_ids) == 1:
                pid = next(iter(process_ids))
                command = read(f'/proc/{pid}/cmdline').decode('utf-8').split('\0')
                scripts = [argument for argument in command if argument.startswith('/') and argument.endswith('/server.py')]
                if len(scripts) == 1:
                    source = read(scripts[0]).decode('utf-8')
                    environment = read(f'/proc/{pid}/environ').decode('utf-8')
                    application = application_index(source, environment)
            index_candidates = candidates(caddy, read, application)
        except OSError:
            pass
        if len(set(index_candidates)) != 1:
            print('Não foi possível escolher automaticamente a página ativa do Control.')
            if application:
                print('Página identificada no serviço: ' + application)
            for candidate in index_candidates:
                print('Candidato: ' + candidate)
            while True:
                index_file = input('Caminho do arquivo index.html (exemplo: /opt/app-unica/novo/index.html): ').strip()
                if not index_file.startswith('/') or not index_file.endswith('/index.html'):
                    print('Informe um arquivo absoluto terminado em /index.html, não o domínio nem uma pasta.')
                    continue
                try:
                    html = read(index_file).decode('utf-8')
                    if '</body>' not in html.lower():
                        print('O arquivo não é uma página HTML válida.')
                        continue
                except OSError:
                    print('Esse arquivo não existe ou não está acessível no servidor.')
                    continue
                break
        else:
            index_file = index_candidates[0]
        print('Página do Control: ' + index_file)
        index = read(index_file).decode('utf-8')
        if '</body>' not in index:
            raise RuntimeError('A página selecionada não contém um documento HTML válido.')
        originals = {action_file: action.encode(), gateway_file: gateway.encode(), index_file: index.encode()}
        if 'from control_autonomy import handle' not in action:
            for method, arguments in [('GET', ''), ('POST', ', read_json_body')]:
                needle = f'        if handle(self, path, "{method}"{arguments}):'
                if action.count(needle) != 1:
                    raise RuntimeError('O action-inbox mudou. Não foi alterado.')
                insert = ('        from control_autonomy import handle as autonomy_handle\n'
                          f'        if autonomy_handle(self, path, "{method}"{arguments}):\n'
                          '            return\n')
                action = action.replace(needle, insert + needle, 1)
        if 'def forward_autonomy' not in gateway:
            needle = 'class Handler(BaseHTTPRequestHandler):\n'
            if gateway.count(needle) != 1:
                raise RuntimeError('O gateway mudou. Não foi alterado.')
            method = '''    def forward_autonomy(self, method):
        try:
            body = None
            if method == 'POST':
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 2048:
                    self.send(400, {'error': 'Pedido invalido.'})
                    return
                self.connection.settimeout(10)
                body = self.rfile.read(size)
            request = urllib.request.Request('http://127.0.0.1:8791/api/autonomy', data=body, method=method,
                headers={'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=10) as response:
                self.send(200, json.load(response))
        except Exception:
            self.send(502, {'error': 'Estado de autonomia indisponivel no Control.'})

'''
            gateway = gateway.replace(needle, needle + method, 1)
            for needle, method in [("        if self.path == '/health':", 'GET'), ("        if self.path != '/chat':", 'POST')]:
                if gateway.count(needle) != 1:
                    raise RuntimeError('As rotas do gateway mudaram. Não foram alteradas.')
                gateway = gateway.replace(needle, f"        if self.path == '/autonomy':\n            self.forward_autonomy('{method}')\n            return\n" + needle, 1)
        tag = '<script src="/api/autonomy/status.js"></script>'
        if tag not in index:
            index = index.replace('</body>', tag + '\n</body>', 1)
        compile(action, action_file, 'exec')
        compile(gateway, gateway_file, 'exec')
        compile((HERE / 'server-autonomy.py').read_text(encoding='utf-8'), 'control_autonomy.py', 'exec')
        directory = action_file.rsplit('/', 1)[0]
        service_user = execute('systemctl show -p User --value control-action-inbox.service') or 'root'
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', service_user):
            raise RuntimeError('Usuário do serviço inválido.')
        execute('install -d -m 700 /opt/control-autonomy; install -d /etc/systemd/system/control-action-inbox.service.d')
        token = read('/opt/nino-ch8-gateway/token')
        write('/opt/control-autonomy/token', token)
        sftp.chmod('/opt/control-autonomy/token', 0o600)
        execute(f'chown -R {shlex.quote(service_user)} /opt/control-autonomy')
        override = b'[Service]\nEnvironment=CONTROL_AUTONOMY_TOKEN_FILE=/opt/control-autonomy/token\nReadWritePaths=/opt/control-autonomy\n'
        write('/etc/systemd/system/control-action-inbox.service.d/macropad-autonomy.conf', override)
        write(directory + '/control_autonomy.py', (HERE / 'server-autonomy.py').read_bytes())
        write(directory + '/autonomy-status.js', (HERE / 'autonomy-status.js').read_bytes())
        for file, original in originals.items():
            backup = file + '.before-macropad-autonomy'
            try:
                sftp.stat(backup)
            except OSError:
                write(backup, original)
        try:
            write(action_file, action.encode())
            write(gateway_file, gateway.encode())
            write(index_file, index.encode())
            execute('systemctl daemon-reload && systemctl restart control-action-inbox.service && systemctl restart nino-control.service')
            execute('systemctl is-active control-action-inbox.service nino-control.service')
        except Exception:
            for file, original in originals.items():
                write(file, original)
            execute('systemctl restart control-action-inbox.service nino-control.service')
            raise
    print('Autonomia instalada no Control. Estado inicial: desativado. Reinicie o ativador do teclado.')
finally:
    client.close()
