"""Delegacao local ao Hermes pelo SDK MCP ja instalado no agente."""
import asyncio
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERMES = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'hermes/bin/hermes.exe'
LOCK = asyncio.Lock()
MANAGEMENT = '''Quando o usuario pedir agentes, consulte hermes profile list e reutilize o perfil adequado.
Se nao existir, crie com hermes profile create NOME --clone-from default --no-alias --description DESCRICAO.
Nao altere o perfil padrao nem copie canais de mensagens. Execute tarefas do perfil com hermes -p NOME chat.
Para periodicidade, exija tarefa e intervalo fornecidos pelo usuario; nao invente rotinas.
Use o cron nativo do perfil default, que ja tem ticker ativo: consulte hermes cron list --all antes de criar,
reutilize uma rotina identica e nao modifique rotinas diferentes. Verifique hermes cron status depois.
Crie com hermes cron create INTERVALO TAREFA --name NOME --deliver local --workdir CAMINHO.
Se a tarefa usar outro perfil, inclua no prompt da rotina a instrucao para executar esse perfil.
Informe nome/id, intervalo e proxima execucao reais. Resultado recorrente fica no historico local do Hermes.
Nao prometa agendamento ativo se o ticker estiver parado. Nao use --yolo nem autoaprove permissoes.
'''

def parse_result(stdout, returncode):
    result = None
    for line in stdout.decode('utf-8', errors='replace').splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get('type') == 'result':
            result = event
    if result is None:
        return {'ok': False, 'text': 'Hermes nao devolveu resultado estruturado. Confira sua configuracao antes de reenviar.'}
    text = result.get('text')
    usable = isinstance(text, str) and bool(text.strip())
    return {
        'ok': returncode == 0 and result.get('exit_code') == 0 and usable,
        'text': text if usable else 'Hermes encerrou sem resposta. Confira a sessao antes de reenviar.',
        'session_id': result.get('session_id', ''),
    }

async def hermes_delegate_task(task: str) -> dict:
    """Delegue uma acao com arquivos ou terminal ao Hermes local e aguarde o resultado.
    task: pedido completo do usuario, incluindo caminhos relevantes.
    Pode criar/reutilizar agentes e agendar rotinas com tarefa e periodicidade explicitas.
    Retorna ok, text e session_id. Nao repita erros automaticamente.
    Preserva permissoes e modelo do Hermes, que pode usar a nuvem.
    """
    if not isinstance(task, str) or not task.strip() or len(task) > 8000:
        raise ValueError('A tarefa deve ter 1 a 8000 caracteres.')
    if LOCK.locked():
        raise ValueError('Hermes ocupado com outra tarefa; aguarde sua conclusao.')
    if not HERMES.is_file():
        raise ValueError('Executavel Hermes local nao encontrado.')
    async with LOCK:
        job_id = str(uuid.uuid4())
        directory = ROOT / 'data/hermes'
        directory.mkdir(parents=True, exist_ok=True)
        process = await asyncio.create_subprocess_exec(
            str(HERMES), 'chat', '--query-file', '-', '--oneshot', '--format', 'stream-json',
            '--source', 'nino-atomic', '--max-turns', '12', '--run-budget', '180', '--checkpoints',
            cwd=str(ROOT), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        cancelled = False
        try:
            stdout, _ = await asyncio.wait_for(process.communicate((MANAGEMENT + '\nPedido do usuario:\n' + task.strip()).encode('utf-8')), timeout=240)
            result = parse_result(stdout, process.returncode)
        except (asyncio.TimeoutError, asyncio.CancelledError) as error:
            # Encerra tambem os subprocessos no Windows; acoes ja executadas nao sao revertidas.
            cancelled = isinstance(error, asyncio.CancelledError)
            if process.returncode is None:
                taskkill = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/taskkill.exe'
                subprocess.run([str(taskkill), '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
            result = {'ok': False, 'text': 'Tarefa interrompida. Acoes ja realizadas podem permanecer; confira antes de reenviar.'}
        result['job_id'] = job_id
        (directory / f'{job_id}.json').write_text(json.dumps({'task': task, **result}, ensure_ascii=False, indent=2), encoding='utf-8')
        if cancelled:
            raise asyncio.CancelledError
        return result

def create_server():
    try:
        from mcp.server import MCPServer
    except ImportError:
        from mcp.server.fastmcp import FastMCP as MCPServer
    server = MCPServer('hermes_local_mcp', instructions='Delegue pedidos de acao do usuario ao Hermes local e use seu resultado para responder. Nao invente execucoes nem repita uma tarefa com erro automaticamente.')
    server.tool()(hermes_delegate_task)
    return server

if __name__ == '__main__':
    if '--task' in sys.argv:
        print(json.dumps(asyncio.run(hermes_delegate_task(sys.stdin.read())), ensure_ascii=False))
    else:
        server = create_server()
        asyncio.run(server.run_stdio_async())
