# Instalação do Superhouse

## 1. Escolha o que precisa instalar

Não é necessário instalar todos os componentes de uma vez.

| Objetivo | Mínimo necessário |
|---|---|
| Abrir os painéis com o macropad | Windows, Python, pynput e teclado2 |
| Perguntar ao Control por texto | Acima + Electron instalado no Nino + conexão CH8 configurada |
| Perguntar por voz e ouvir resposta | Acima + Whisper, Python de transcrição, Piper, voz e microfone |
| Conversar com IA local | Nino + Atomic Chat ou Ollama com modelo disponível |
| Usar Atom Voice | Núcleo Nino, voz/transcrição, servidor Atom e firmware compatível |
| Usar placa amarela | Gateway da placa, Control configurado e firmware CYD |
| Ajustar autonomia | Teclado2, API de autonomia instalada no Control e ponte configurada |

Os serviços externos do Control, GrokBot e ponte precisam existir. Este repositório não provisiona do zero toda a infraestrutura dessas aplicações.

## 2. Obter os fontes

```powershell
git clone https://github.com/hudsonrj/superhouse.git C:\repositorio\superhouse
Set-Location C:\repositorio\superhouse
```

Se a pasta já existir, use a rotina de atualização em [Desenvolvimento](DESENVOLVIMENTO.md). Não clone sobre uma instalação que contenha dados privados.

### Fonte consolidado e instalação de execução

Há dois conjuntos de caminhos na máquina original:

- `C:\repositorio\superhouse`: cópia consolidada e versionada.
- `C:\repositorio\nino`, `C:\repositorio\teclado2` e `C:\repositorio\placaamarelajarvis`: instalações existentes que continuam em uso.

Alguns caminhos são absolutos. Apenas clonar o monorepositório não faz os atalhos procurarem o Nino dentro dele. Para uma **máquina nova**, o caminho mais próximo da instalação atual é preparar essas pastas separadas com o código dos componentes. Antes de copiar, confirme que os destinos ainda não existem:

```powershell
$raizSuperhouse = 'C:\repositorio\superhouse'
foreach ($componente in @('nino', 'teclado2', 'placaamarelajarvis')) {
    $destinoSuperhouse = Join-Path 'C:\repositorio' $componente
    if (Test-Path -LiteralPath $destinoSuperhouse) {
        throw "Destino já existe: $destinoSuperhouse. Use a rotina de atualização, preservando os dados locais."
    }
    Copy-Item -LiteralPath (Join-Path $raizSuperhouse $componente) -Destination $destinoSuperhouse -Recurse
}
```

Esse exemplo instala fontes; não instala dependências e não cria repositórios independentes. Alternativamente, um mantenedor pode adaptar os caminhos fixos para executar diretamente do monorepositório. Veja a lista de caminhos em [Configuração](CONFIGURACAO.md). Não há configuração global que faça essa migração automaticamente.

## 3. Pré-requisitos no Windows

Instale Git, Node.js/npm e Python. O JavaScript usa `fetch`, `AbortSignal.any` e `AbortSignal.timeout`; escolha um Node que exponha essas APIs. A instalação do teclado usa atualmente `C:\Python313\pythonw.exe`; se o Python estiver em outro caminho, adapte `instalar_startup.ps1` antes de registrar a tarefa.

```powershell
git --version
node --version
npm --version
python --version
node -p "typeof fetch + ' / ' + typeof AbortSignal.any + ' / ' + typeof AbortSignal.timeout"
```

O último comando deve indicar funções. Para as placas, também serão necessários driver USB, cabo de dados e ferramenta de compilação adequada ao hardware.

## 4. Nino e Electron

```powershell
Set-Location C:\repositorio\nino
npm ci
```

O lockfile fixa a árvore de dependências. O pacote inclui Electron, mas a primeira instalação pode precisar de internet para baixar seu executável. Não copie `node_modules` de outro sistema operacional.

### Modelo local

**Atomic Chat:** instale o aplicativo separadamente, carregue um modelo e ative sua API local. O cliente atual tem padrão `http://127.0.0.1:1337/v1`. Verifique:

```powershell
Invoke-RestMethod 'http://127.0.0.1:1337/v1/models'
```

**Ollama:** é alternativa. Antes de iniciar o Nino no terminal escolhido:

```powershell
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
$env:OPENAI_COMPATIBLE = 'false'
npm start
```

O serviço e o modelo precisam estar instalados/carregados. Os nomes `qwen3.5:2b` e `bge-m3` aparecem nos scripts históricos; confirme que o backend escolhido disponibiliza os modelos antes de selecioná-los. Não há garantia de que o projeto/documentos de um aplicativo de IA sejam expostos pela API de chat.

### Whisper no Windows

Na raiz do Nino:

```powershell
python -m venv vendor\sttenv
.\vendor\sttenv\Scripts\python.exe -m pip install -r scripts\requirements-atom.txt
```

As versões registradas são `faster-whisper==1.2.1` e `av==16.1.0`. Elas evitam a incompatibilidade PyAV descrita no manual Atom. Prepare o modelo local no cache Windows:

```powershell
.\vendor\sttenv\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8', download_root='data/models/whisper-windows')"
```

Esse comando baixa o modelo se ele estiver ausente; precisa de rede nessa primeira execução. Não reutilize um cache Linux copiado com links simbólicos materializados como texto.

### Piper e voz

Os binários e modelos não são enviados ao Git. Instale o pacote Piper Windows compatível com a máquina, preservando seus arquivos auxiliares, de modo que exista:

```text
C:\repositorio\nino\vendor\piper-windows\piper\piper.exe
C:\repositorio\nino\vendor\voices\pt_BR-faber-medium.onnx
C:\repositorio\nino\vendor\voices\pt_BR-faber-medium.onnx.json
```

Confirme os caminhos e o executável antes de testar voz:

```powershell
Test-Path .\vendor\piper-windows\piper\piper.exe
Test-Path .\vendor\voices\pt_BR-faber-medium.onnx
Test-Path .\vendor\voices\pt_BR-faber-medium.onnx.json
.\vendor\piper-windows\piper\piper.exe --help
```

O projeto não inclui um instalador Windows único que baixe todos esses recursos. O script `scripts/setup.sh` é Linux e não prepara os binários Windows. A configuração de voz do Nino precisa apontar para uma voz realmente instalada.

### Primeiro uso

```powershell
npm start
```

Converse por texto primeiro. Depois teste uma resposta curta falada e a transcrição. Configure documentos, Google, TypeSafe e integrações remotas apenas conforme a necessidade. Consulte [Configuração](CONFIGURACAO.md); nenhuma dessas credenciais está no clone.

## 5. Teclado2

```powershell
Set-Location C:\repositorio\teclado2
python -m pip install pynput paramiko
python global_shortcuts.py
```

`paramiko` é usado pelo instalador remoto; o hook das teclas usa `pynput`. O Python usado para instalar os pacotes precisa corresponder ao usado no startup.

Configure no aplicativo físico do teclado os atalhos de [Operação](OPERACAO.md). Salve no dispositivo; selecionar somente Ctrl/Alt/Shift sem a tecla final não produz um comando distinguível. Q/T precisam do Electron e dos módulos do Nino nos caminhos esperados. Microfone, alto-falantes e suas permissões precisam funcionar na sessão do Windows.

Valide T antes de Q: primeiro texto → Control → resposta; depois gravação → transcrição → resposta → fala. Só então configure autonomia e startup.

## 6. Integração Control e ponte

Prepare `nino/data/ch8-config.json` com o endpoint e token reais, de forma privada. O formato está em [Configuração](CONFIGURACAO.md). Para a ponte, garanta que a pasta `data` existe e use o assistente:

```powershell
Set-Location C:\repositorio\nino
New-Item -ItemType Directory -Force -Path data | Out-Null
python scripts\configure-ponte.py
```

Ele grava a configuração local e oculta URL/valor de autenticação na entrada. Não cria um webhook no provedor e não configura os canais do agente.

### Instalar/atualizar o módulo de autonomia no servidor existente

Pré-condições: acesso à rede privada do servidor, SSH com chave de host conhecida, serviços existentes `control-action-inbox.service` e `nino-control.service`, gateway/token já instalados e página HTML ativa identificável.

```powershell
Set-Location C:\repositorio\teclado2
python control\install-autonomy.py
```

O script tem host e usuário SSH fixos. Leia-os e confira o destino antes de executar. A senha é solicitada sem ser salva. A política SSH rejeita host desconhecido: valide a identidade do servidor e prepare o arquivo de hosts conhecidos antes, sem desativar essa proteção.

O instalador localiza arquivos dos serviços, instala o módulo Python e o indicador, adapta as rotas e reinicia os serviços. Ele mantém backups dos arquivos originais principais. Essa rotina modifica uma instalação existente; não é um provisionador completo e seu rollback não é um snapshot de todo o servidor.

Se solicitar o HTML, informe o **arquivo absoluto** que termina em `/index.html`, por exemplo `/opt/app-unica/novo/index.html` quando esse for realmente o arquivo ativo. Não informe domínio nem apenas a pasta. Após atualizar servidor e cliente para `scaleVersion: 2`, reinicie o ativador local.

## 7. Startup do Windows

### Teclado

Na instalação de execução:

```powershell
Set-Location C:\repositorio\teclado2
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\instalar_startup.ps1
Start-ScheduledTask -TaskName 'CH8 Macropad'
Get-ScheduledTask -TaskName 'CH8 Macropad' | Select-Object TaskName,State
```

O script cria tarefa de logon interativo do usuário, usa `pythonw`, não eleva privilégios, evita instâncias duplicadas e configura reinício após falha em um minuto. Não há limite de tempo para a tarefa. A política de reinício não detecta um processo travado que continue vivo, nem mantém interface interativa após logout.

### Nino e Atom

O instalador Nino captura o modelo atual do Atomic Chat antes de registrar `Nino-Startup`. Configure o Atom e carregue um modelo primeiro:

```powershell
Set-Location C:\repositorio\nino
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\install-windows-startup.ps1
```

A tarefa roda o orquestrador de startup; ela não é o mesmo watchdog de `CH8 Macropad`. Consulte [Operação](OPERACAO.md) sobre dependências, logs e limites.

## 8. Atom Voice e placa amarela

Siga os manuais específicos: [Nino/Atom](../nino/GUIA-SUPERHOUSE.md) e [CYD](../placaamarelajarvis/GUIA-SUPERHOUSE.md). Confirme o modelo da placa e a porta USB antes do flash. Não use instruções de AtomS3 para o Atom Voice ESP32-PICO-D4.

Para o ESPClaw, não há fontes suficientes para fornecer uma instalação completa. `atom2`, `esp32` e `house` também não oferecem um instalador independente nesta cópia.

## Critérios de conclusão

Considere cada etapa pronta somente quando a camada correspondente responder: modelo local por `/models`; Nino por texto; áudio curto transcrito/falado; T pelo Control; Q completo; indicador com estado confirmado; Atom/CYD com o hardware real. Por fim faça um logout/login ou reinício planejado e verifique as tarefas. Não habilite respostas automáticas como simples teste de conectividade.
