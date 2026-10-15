"""Teste somente leitura: Atomic escolhe ferramenta -> Hermes -> resposta Atomic."""
import asyncio
import json
import sys
import urllib.request
from datetime import timedelta
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

def chat(payload):
    request = urllib.request.Request('http://127.0.0.1:1337/v1/chat/completions', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)['choices'][0]['message']

async def main():
    root = Path(__file__).resolve().parent.parent
    model = json.loads((root / 'data/startup/atomic-model.json').read_text())['model']
    parameters = StdioServerParameters(command=sys.executable, args=[str(root / 'scripts/hermes_mcp.py')], env={'PYTHONIOENCODING': 'utf-8'})
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=300)) as client:
            await client.initialize()
            listed = await client.list_tools()
            tool = next(t for t in listed.tools if t.name == 'hermes_delegate_task')
            messages = [
                {'role': 'system', 'content': 'Para consultar ou agir neste computador, delegue a hermes_delegate_task. Nao invente resultados. Depois do resultado da ferramenta, responda brevemente em portugues.'},
                {'role': 'user', 'content': 'Consulte pelo terminal local o espaco livre do disco C em GB, somente leitura. Nao altere arquivos nem envie mensagens.'},
            ]
            payload = {'model': model, 'stream': False, 'max_tokens': 128, 'temperature': 0, 'chat_template_kwargs': {'enable_thinking': False}, 'messages': messages,
                       'tools': [{'type': 'function', 'function': {'name': tool.name, 'description': tool.description, 'parameters': tool.inputSchema}}], 'tool_choice': 'auto'}
            print('Atomic: identificando o pedido de acao.', flush=True)
            assistant = await asyncio.to_thread(chat, payload)
            calls = assistant.get('tool_calls', [])
            assert len(calls) == 1 and calls[0]['function']['name'] == tool.name, 'Atomic nao delegou a tarefa.'
            call = calls[0]
            arguments = json.loads(call['function']['arguments'])
            print('Atomic escolheu Hermes; aguardando a execucao.', flush=True)
            response = await client.call_tool(tool.name, arguments)
            assert not response.isError, response
            result = getattr(response, 'structuredContent', None)
            if result is None:
                result = json.loads(next(item.text for item in response.content if hasattr(item, 'text')))
            print('Hermes:', json.dumps(result, ensure_ascii=True), flush=True)
            assert result['ok'], 'Hermes nao concluiu a tarefa.'
            messages.extend([assistant, {'role': 'tool', 'tool_call_id': call['id'], 'content': json.dumps(result, ensure_ascii=False)}])
            payload.pop('tools')
            payload.pop('tool_choice')
            payload['max_tokens'] = 60
            answer = await asyncio.to_thread(chat, payload)
            assert answer.get('content', '').strip(), 'Atomic nao respondeu ao resultado.'
            print('Resposta final Atomic:', answer['content'], flush=True)

asyncio.run(main())
