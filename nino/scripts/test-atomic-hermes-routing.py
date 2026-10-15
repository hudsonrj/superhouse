"""Confere selecao de ferramenta pelo modelo Atomic, sem executar a tarefa."""
import json
import urllib.request
from pathlib import Path

base = 'http://127.0.0.1:1337/v1'
selected = json.loads((Path(__file__).resolve().parent.parent / 'data/startup/atomic-model.json').read_text(encoding='utf-8'))
payload = {
    'model': selected['model'], 'stream': False, 'max_tokens': 200,
    'temperature': 0, 'chat_template_kwargs': {'enable_thinking': False},
    'messages': [
        {'role': 'system', 'content': 'Use hermes_delegate_task quando o usuario pedir uma acao neste computador. Para conversa comum, responda diretamente. Nao invente resultados de ferramentas.'},
        {'role': 'user', 'content': 'Consulte o nome deste computador pelo terminal local e traga o resultado, sem alterar arquivos.'},
    ],
    'tools': [{'type': 'function', 'function': {
        'name': 'hermes_delegate_task',
        'description': 'Delegue ao Hermes uma tarefa de acao neste computador e aguarde seu resultado.',
        'parameters': {'type': 'object', 'properties': {'task': {'type': 'string'}}, 'required': ['task']},
    }}],
    'tool_choice': 'auto',
}
request = urllib.request.Request(base + '/chat/completions', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=180) as response:
    result = json.load(response)
calls = result['choices'][0]['message'].get('tool_calls', [])
assert len(calls) == 1 and calls[0]['function']['name'] == 'hermes_delegate_task', 'Modelo nao escolheu a ferramenta para o pedido de acao.'
arguments = json.loads(calls[0]['function']['arguments'])
assert isinstance(arguments.get('task'), str) and arguments['task'].strip()
print('Atomic selecionou hermes_delegate_task com argumentos validos. Nenhuma acao executada neste teste.')
