"""Configure the webhook locally, without echoing or persisting credentials in Git."""
import getpass
import json
from pathlib import Path

url = getpass.getpass('URL completa do webhook (oculta): ').strip()
header = input('Nome do cabecalho de autenticacao, conforme o painel: ').strip()
value = getpass.getpass('Valor completo do cabecalho (oculto; inclua Bearer se exigido): ').strip()
if not url or not header or not value:
    raise SystemExit('Configuracao incompleta; nenhum arquivo foi salvo.')
file = Path(__file__).resolve().parent.parent / 'data' / 'ponte-config.json'
file.write_text(json.dumps({'enabled': True, 'url': url, 'authHeader': header, 'authValue': value}, indent=2), encoding='utf8')
print('Configuracao privada da ponte salva. Nenhum pedido foi enviado.')
