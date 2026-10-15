"""Teste real somente leitura: MCP -> Hermes -> resultado."""
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    bridge = Path(__file__).with_name('hermes_mcp.py').resolve()
    parameters = StdioServerParameters(command=sys.executable, args=[str(bridge)], env={'PYTHONIOENCODING': 'utf-8'})
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=300)) as client:
            await client.initialize()
            tools = await client.list_tools()
            assert 'hermes_delegate_task' in [tool.name for tool in tools.tools]
            print('MCP conectado; ferramenta encontrada.', flush=True)
            response = await client.call_tool('hermes_delegate_task', {
                'task': 'Pedido de teste somente leitura: use o terminal local para consultar o nome deste computador (hostname). Nao altere arquivos nem envie mensagens. Responda em portugues com o nome obtido.',
            })
            assert not response.isError, response
            content = getattr(response, 'structuredContent', None)
            if content is None:
                content = json.loads(next(item.text for item in response.content if hasattr(item, 'text')))
            print(json.dumps(content, ensure_ascii=True), flush=True)
            assert content['ok'], 'Hermes nao concluiu o teste; confira o resultado acima.'

asyncio.run(main())
