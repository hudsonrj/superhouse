# Atom Voice como microfone do Nino

Firmware para Atom Voice / ATOM Echo C008-C, ESP32-PICO-D4, microfone SPM1423 e amplificador NS4168. Não usar em AtomS3/VoiceS3R.

Diagnostico USB a 115200: o comando `wifi` busca a rede configurada na banda
suportada pelo Atom e informa canal/sinal; desconexoes informam o codigo de motivo
do SDK, sem imprimir senha ou chave. A busca pode interromper momentaneamente a
conexao; use-a somente para diagnostico. O Atom suporta Wi-Fi de 2,4 GHz.

O Atom grava por botão, envia WAV ao PC pela rede Wi-Fi e recebe a resposta falada do Nino. Whisper, Atomic Chat e Piper rodam no computador. Nenhum serviço STT em nuvem é usado. Depois dos downloads iniciais dos modelos, a conversa pode funcionar sem internet.

## Configuração local

- `include/secrets.h`: SSID `Offline`, senha Wi-Fi, URL do PC e chave do serviço. Este arquivo está ignorado pelo Git.
- `data/atom-config.json` na raiz do Nino: endereço IPv4 do PC e a mesma chave. Ignorado pelo Git.
- PC configurado inicialmente como `192.168.15.3`, porta `3082`. Reserve esse IP no roteador ou atualize os dois arquivos e recompile quando o endereço mudar.
- O Atom precisa da banda **2,4 GHz** da rede Offline. O PC pode estar em 5 GHz, desde que as bandas compartilhem a LAN e não haja isolamento entre clientes.

## Computador

Requer Node/npm já instalados, `vendor/sttenv/Scripts/python.exe` com faster-whisper, Piper Windows em `vendor/piper-windows/piper/piper.exe`, vozes em `vendor/voices` e modelo Whisper em `data/models/whisper-windows` (cache separado no Windows para não reutilizar links Linux materializados como texto).

Abra Atomic Chat, carregue um modelo e habilite a API local na porta 1337. Inicie `Nino-Atom.bat` na raiz do projeto. O serviço usa a mesma conversa/prompt do Nino, com histórico próprio do Atom; a janela Electron não precisa ficar aberta.

Dependências de transcrição verificadas: `vendor/sttenv/Scripts/python.exe -m pip install -r scripts/requirements-atom.txt`. O PyAV 19 removeu uma opção usada pelo faster-whisper 1.2.1; a versão 16.1.0 é fixada para evitar essa incompatibilidade.

Para responder no computador, abra PowerShell na raiz e execute:

```powershell
$env:NINO_ATOM_OUTPUT='pc'
node src/server/atom.js
```

Áudio recebido, texto e resposta ficam em `data/atom/`. A pasta acumula gravações; apague arquivos antigos quando não precisar mais deles. A base de documentos dos projetos Atomic Chat não é incluída automaticamente pela API de chat; esta integração não promete acesso a ela.

O serviço expõe somente envio de voz e a última resposta de áudio, sempre com chave. Libere TCP 3082 no Firewall do Windows somente na rede local. HTTP não criptografa o tráfego: use apenas sua LAN confiável; não encaminhe essa porta no roteador.

## Compilar e instalar

Na raiz do projeto:

```powershell
python -m platformio run -d firmware/atom-voice
python -m platformio device list
python -m platformio run -d firmware/atom-voice -t upload --upload-port COMx
python -m platformio device monitor --port COMx --baud 115200
```

A primeira instalação exige USB e substitui o firmware existente. O SPIFFS é inicializado na flash interna e pode formatar a partição de arquivos no primeiro boot; preserve dados antigos antes de instalar. O cartão SD não é usado: a base SD e os pinos ainda não foram identificados. Não conecte uma base que reutilize GPIO19/22/23/33, reservados ao áudio.

Depois da instalação, o USB deixa de transportar áudio. Para operar sem cabo, conecte alimentação por bateria compatível; este Atom não possui bateria interna.

## Botão e LED

- Laranja: conectando ao Wi-Fi.
- Verde: pronto. Clique para iniciar a gravação.
- Amarelo: gravando. Clique novamente para enviar; limite automático de 30 segundos.
- Azul: transcrevendo/consultando o modelo.
- Roxo: resposta no alto-falante do Atom, com volume reduzido.
- Vermelho: erro; o monitor serial informa o motivo.

A gravação temporária usa a flash interna, sem reservar um áudio inteiro na RAM. Isso permite até 30 segundos no ESP32 sem PSRAM; uso muito frequente exige migrar para um SD compatível para reduzir desgaste da flash.

Pinos e configuração PDM/I2S seguem o [exemplo oficial M5Stack](https://github.com/m5stack/M5-ProductExampleCodes/blob/master/Core/Atom/AtomEcho/Arduino/Repeater/Repeater.ino) e o [manual do Atom Voice](https://docs.m5stack.com/en/atom/Atom_Voice).

## Verificação

`node --test scripts/test-atom.js` verifica validação WAV, chave de acesso e fluxo HTTP com transcrição/conversa/síntese simuladas. A calibração do microfone, alcance do Wi-Fi, botão e reprodução precisam do dispositivo real.

## Sensor de movimento

O Unit PIR no Grove abaixo do USB usa GPIO32 (fio branco). Presenca nao abre mais o Nino. O firmware atualizado envia estado autenticado a cada 30 segundos e ao detectar movimento, permitindo inferir ausencia provavel apos dez minutos e avisar o GrokBot pela ponte. Sem sinais por 90 segundos, o acompanhamento por ausencia e suspenso. O sensor nao inicia o microfone; o botao continua iniciando e encerrando a gravacao. Veja `docs/ausencia-grokbot.md` na raiz do projeto para periodicidade, limites e politica mobile.
