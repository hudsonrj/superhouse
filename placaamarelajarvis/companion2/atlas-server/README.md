# Atlas-server (opcional, nao faz parte do produto)

O produto da Placa Amarela e o firmware na placa. Este servidor nao e necessario
para usar o dispositivo. Foi um experimento de app e permanece aqui so como
referencia.

O motor principal é **local e determinístico**: uma pergunta por vez, descoberta
pequena, próxima ação mínima. Sem internet, sem chave, sem nuvem. A DeepSeek
continua opcional e só entra com consentimento.

## Subir

```powershell
cd companion2/atlas-server
node server.mjs
```

Abra `http://localhost:8787`. Por segurança, o servidor aceita apenas conexões
desta máquina por padrão. Para usar no telefone da mesma rede, habilite isso
explicitamente antes de iniciar:

```powershell
$env:ATLAS_HOST = "0.0.0.0"
node server.mjs
```

Não habilite esse modo em uma rede que você não confia.

Para visualizar a frota real já fornecida por `firmware-cyd/cyd_api.py`:

```powershell
$env:ATLAS_FLEET_URL = "http://127.0.0.1:8790"
node server.mjs
```

A tela é somente leitura enquanto o endpoint de ações não tiver autenticação.

IA opcional:

```powershell
$env:DEEPSEEK_API_KEY = "chave-rotacionada"
node server.mjs
```

## O que o app faz

- Check-in do dia: crise / neutro / alta, humor, energia, sono
- Seis caminhos da placa: Como estou, Entender, Regular, Organizar, Decisão, Companhia
- Frota CONTROL: agentes reais, estado de execução e fila em fluxo, somente leitura
- Ferramentas reais: respirar, aterrar 5-4-3-2-1, adiar impulso, um passo, reunião, silêncio
- SOS permanente com SAMU 192 e CVV 188
- Mapa de descobertas e gatilhos
- Perfil adaptativo, local, apagável
- Funciona offline depois da primeira visita

## Endpoints

| Método | Caminho | Função |
| --- | --- | --- |
| `GET` | `/` | App |
| `GET` | `/health` | Status do motor |
| `GET` | `/api/state` | Estado `sistema_de_vida_v1` |
| `PUT` | `/api/state` | Grava estado |
| `POST` | `/api/journey` | Passo JSON para o app |
| `POST` | `/journey` | Protocolo `ATLAS/1` para a ESP32 |

Não publique a porta `8787` diretamente na internet. Em produção: HTTPS,
autenticação do dispositivo e limite de requisições.

O estado em `data/sistema.json` não deve ir para o git. Fica neste computador.

## Firmware

A Cheap Yellow Display continua independente. Se o Atlas estiver na mesma rede,
`POST /journey` devolve o protocolo antigo. Sem chave de IA, o dispositivo
recebe o motor local — o mesmo do telefone.
