# Configuração, rede e contratos

## Caminhos de configuração

| Arquivo / recurso | Conteúdo | Vai para o Git? |
|---|---|---|
| `nino/data/settings.json` | Preferências de modelo, voz, base e interface | Não |
| `nino/data/ch8-config.json` | Endpoint, protocolo e token do Control | Não |
| `nino/data/ponte-config.json` | URL e cabeçalho secreto do webhook | Não |
| `nino/data/atom-config.json` | IP do PC, token Atom e saída de áudio | Não |
| `nino/firmware/atom-voice/include/secrets.h` | Wi-Fi, URL do PC e chave do dispositivo | Não |
| `~/.config/nino/credenciais.json` | Credenciais Google/TypeSafe | Não |
| `placaamarelajarvis/companion2/firmware-cyd/.kiosk_token` | Token privado do kiosk/Control | Não |
| `/opt/control-autonomy/state.sqlite` | Estado e deduplicação da autonomia no servidor | Não |

`NINO_CONFIG_DIR` pode mudar o diretório do cofre. `~` significa a pasta pessoal do usuário que executa o processo. No Windows, revise as ACLs dos arquivos privados; a solicitação de modo POSIX `600` não substitui uma revisão de permissões NTFS.

## Exemplos de formato, sem credenciais reais

**Conexão CH8:**

```json
{
  "enabled": true,
  "url": "http://<IP_PRIVADO_DO_GATEWAY>:8810",
  "token": "<TOKEN_PRIVADO_DO_GATEWAY>",
  "protocol": "control"
}
```

O endpoint precisa ser a API do gateway, não uma página de login do site. `protocol: control` habilita o acompanhamento assíncrono por id. Não transfira esse token para o firmware CYD: são contratos distintos.

**Ponte:**

```json
{
  "enabled": true,
  "url": "https://<HOST_DO_WEBHOOK>/<CAMINHO_PRIVADO>",
  "authHeader": "Authorization",
  "authValue": "Bearer <SEGREDO_DO_WEBHOOK>"
}
```

O nome do cabeçalho e o formato do valor devem ser os exigidos pelo webhook. O cliente permite HTTPS ou HTTP em endereços privados, rejeita credenciais embutidas na URL e redirecionamentos e envia somente `{ "text": "..." }`.

**Atom:**

```json
{
  "host": "<IPV4_LOCAL_DO_PC>",
  "token": "<CHAVE_ALEATORIA_COM_PELO_MENOS_32_CARACTERES>",
  "output": "atom"
}
```

`host` é o endereço de escuta do PC e precisa estar atribuído a uma interface local. Use a mesma chave no firmware e no servidor. `output` pode ser `atom` ou `pc`; `NINO_ATOM_OUTPUT` sobrepõe essa preferência. A configuração de exemplo do firmware está em [secrets.example.h](../nino/firmware/atom-voice/include/secrets.example.h); confira os nomes das constantes ali, em vez de inventar um arquivo novo incompatível.

Não cole senhas em issues, Markdown ou comandos que fiquem no histórico. Edite os arquivos privados ou use os configuradores. Um `.gitignore` não remove uma credencial que já tenha sido commitada: nesse caso é necessário rotacioná-la e tratar o histórico separadamente.

## Portas e exposição

| Porta / endereço | Serviço | Escopo esperado |
|---|---|---|
| `127.0.0.1:1337/v1` | Atomic Chat | API de modelo local |
| `127.0.0.1:11434` | Ollama alternativo | API de modelo local |
| `127.0.0.1:3081` | Nino web padrão | Local; `NINO_HOST`/`NINO_PORT` podem alterar |
| `<IP_PC>:3082` | Servidor Atom | LAN confiável, chave obrigatória |
| `127.0.0.1:<porta aleatória>` | Python → Electron Control | Local, token efêmero por processo |
| `<gateway privado>:8810` | Gateway CH8/Control | Rede privada autenticada |
| `127.0.0.1:8791` no servidor | API Control usada pelo gateway | Serviço externo existente |
| `0.0.0.0:8788` | Gateway CYD no PC | Escuta todas as interfaces; restrinja firewall |
| `8790` | API CYD de infraestrutura | Variante de servidor; depende de arquivos e estado do Control |
| `127.0.0.1:8787` | Atlas-server opcional | Experimento separado; não necessário ao produto CYD |

Os endereços não são instrução para abrir portas no roteador. HTTP em LAN não cifra áudio, consultas ou tokens. Use rede confiável e regras de firewall restritas. O gateway CYD atual cria contexto TLS sem validação de certificado; esse limite está no código e exige correção antes de tratá-lo como um transporte endurecido para uso externo.

Os sites `control.ch8ai.com.br`, `monitor.ch8ai.com.br` e `chcontrol.ch8ai.com.br` são abertos pelo navegador e têm autenticação/infraestrutura próprias. Seus backends completos não são definidos por esta tabela.

## Contratos de chat e ponte

### Gateway CH8

- `POST /chat`: Bearer token; JSON com `messages`, `stream: false` e, na modalidade Control, `requestId` único.
- Resposta direta: JSON com `response` em texto.
- Resposta `202`: id correspondente à requisição; o cliente consulta `GET /jobs/<id>` até `done` ou `error`.
- O cliente tem limite global de espera de 180 segundos, valida JSON, id e texto final.

O script [ch8-gateway.py](../nino/scripts/ch8-gateway.py) é uma referência de implantação. A adaptação de autonomia é aplicada no gateway remoto pelo instalador do teclado; não presuma que todo gateway recém-copiado já tenha essa extensão.

### Atom

Todas as rotas do servidor Atom exigem Bearer com a chave configurada.

| Método / rota | Uso |
|---|---|
| `POST /voice` | WAV PCM mono 16-bit/16 kHz, 250 ms a 30 s, com tamanho declarado |
| `GET /reply/<id>` | Último áudio PCM; taxa indicada em cabeçalho |
| `POST /sensor-status` | JSON `motion` booleano; heartbeat do PIR |
| `GET /sensor-status` | Estado de presença e horários |
| `POST /presence` | Compatibilidade de evento de presença |
| `POST /speak` | Texto a exibir/falar no PC; até 2.000 caracteres e corpo JSON limitado |

O servidor evita duas conversas simultâneas e pode responder `409`. Não tente transformar essa resposta em repetição imediata de uma ação já iniciada.

### CYD

`GET /cyd` fornece o protocolo textual `CTRL/1`. As rotas `/cyd/act`, `/cyd/ask`, `/cyd/rag` e outras adaptam interações para o Control. `GET /health` ajuda a diagnosticar o gateway, mas não comprova áudio, hardware nem execução dos agentes. O token kiosk é lido da configuração privada; confirme a implantação antes de expor essas rotas fora da LAN.

## Contrato de autonomia

`GET /autonomy` pelo gateway e `GET /api/autonomy` na interface Control representam o mesmo estado de servidor. A autenticação do GET também depende da proteção do gateway/proxy; o módulo Python por si só autentica explicitamente os POSTs. Não o publique supondo que o handler GET tenha autenticação própria.

```json
{
  "enabled": true,
  "level": -1,
  "scaleVersion": 2,
  "revision": 42,
  "expiresAt": 2000000000,
  "label": "Pedir aprovação antes de responder",
  "expired": false
}
```

Esse é um exemplo, não o estado atual da instalação. `level` é inteiro entre −3 e +3; `revision` e `expiresAt` são inteiros. `expiresAt` usa segundos Unix. O cliente exige `scaleVersion: 2` para não interpretar o servidor antigo de 0 a 3 como a nova escala.

`POST /autonomy` recebe `action` entre `toggle`, `more`, `less` ou `heartbeat`, com `requestId` UUID. O servidor deduplica por id, limita a escala e altera a revisão quando há mudança de estado. O giro não liga o modo. A tecla A alterna o modo e reinicia o nível em 0. Em modo ativo, `less` pode chegar a −3 sem desligar.

O lease é renovado para cinco minutos e o cliente usa heartbeat de dois minutos. Ao expirar, o estado efetivo fica desligado; um heartbeat tardio não restaura a autorização. É necessário ativar novamente. A comparação de revisão e validade deve acontecer antes de cada resposta a terceiros.

## Caminhos fixos a revisar em outra máquina

| Arquivo | Dependência de ambiente |
|---|---|
| `teclado2/control_client.py` | Executável Electron em `C:\repositorio\nino` |
| `teclado2/control/main.js` | Módulos `src/main` do Nino |
| `teclado2/control/autonomy.js` | Conexão privada em `C:\repositorio\nino\data` |
| `teclado2/instalar_startup.ps1` | Python em `C:\Python313\pythonw.exe` |
| `teclado2/global_shortcuts.py` | Links/aliases de aplicativos do usuário Windows e Nino.bat |
| `teclado2/control/install-autonomy.py` | Host SSH e serviços de uma instalação Control existente |
| `nino/src/main/hermes.js` | Ambiente Hermes em `%LOCALAPPDATA%\hermes\hermes-agent` |
| `_build_lvgl.py` da placa | Usuário, versão e ferramentas do pacote Arduino15 |
| Firmware CYD | Endereços LAN/Tailscale/nuvem e configuração Wi-Fi |

Depois de mudar caminhos, rode os testes locais e valide a camada física. Instalar um novo startup não migra credenciais nem modelos automaticamente.
