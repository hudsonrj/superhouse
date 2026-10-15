import asyncio
import importlib.util
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

spec = importlib.util.spec_from_file_location('hermes_bridge', Path(__file__).with_name('hermes_mcp.py'))
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
result = bridge.parse_result(b'noise\n{"type":"result","exit_code":0,"text":"feito","session_id":"abc"}\n', 0)
assert result == {'ok': True, 'text': 'feito', 'session_id': 'abc'}
assert not bridge.parse_result(b'{"type":"result","exit_code":0,"text":"feito"}', 1)['ok']
assert not bridge.parse_result(b'nao houve resultado', 0)['ok']
assert not bridge.parse_result(b'{"type":"result","exit_code":0,"text":""}', 0)['ok']
async def validate():
    for task in ['', 'x' * 8001]:
        try:
            await bridge.hermes_delegate_task(task)
        except ValueError:
            pass
        else:
            raise AssertionError('Tarefa invalida aceita')
asyncio.run(validate())
async def interruption(cancelled):
    class Process:
        pid = 123
        returncode = None
        async def communicate(self, data):
            raise asyncio.CancelledError() if cancelled else asyncio.TimeoutError()
    with tempfile.TemporaryDirectory() as directory:
        with patch.object(bridge, 'ROOT', Path(directory)), patch.object(bridge.asyncio, 'create_subprocess_exec', AsyncMock(return_value=Process())), patch.object(bridge.subprocess, 'run') as kill:
            try:
                result = await bridge.hermes_delegate_task('teste de interrupcao simulado')
                assert not cancelled and not result['ok']
            except asyncio.CancelledError:
                assert cancelled
            kill.assert_called_once()
            assert kill.call_args.args[0][-4:] == ['/PID', '123', '/T', '/F']
            assert len(list((Path(directory) / 'data/hermes').glob('*.json'))) == 1
asyncio.run(interruption(False))
asyncio.run(interruption(True))
bridge.create_server()
print('Hermes MCP: validacao, resultado, interrupcao e registro de ferramenta passaram.')
