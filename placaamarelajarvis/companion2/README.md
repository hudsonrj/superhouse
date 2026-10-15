# Placa Amarela / Companion2

Firmware do console tatil de descoberta pessoal "Placa Amarela", integrado ao
conceito do aplicativo "Meu Sistema de Vida". O alvo inicial e a placa LCKFB
Lichuang ESP32-S3 (`lichuang-dev`).

A interface local e organizada nas estacoes Diagnostico, Ideias, Atividades,
Regulacao, Reconhecimento e Gatilhos. Tudo roda na placa. Nao ha aplicativo
externo nem servidor obrigatorio.

Na Cheap Yellow Display, grave `firmware-cyd/atlas_cyd`. Na Lichuang ESP32-S3,
grave este firmware. Os dois expõem o mesmo contrato: um toque, uma pergunta,
uma acao minima, SOS com CVV 188 e SAMU 192.

O contexto oficial do motor esta em `prompts/placa_amarela.system.md`. Ele
orienta o tom do firmware local e nao e enviado a nenhum servidor publico.

O projeto preserva o fluxo local de seguranca do Companion Life e acrescenta
camera, voz, som, toque e movimento. Sensores ampliam o contexto; eles nao
diagnosticam humor, doencas ou medicamentos.

## Hardware confirmado

- ESP32-S3-WROOM-1-N16R8: 16 MB flash e 8 MB PSRAM;
- camera GC0308 (VGA);
- LCD ST7789 320x240 e toque capacitivo FT5x06;
- entrada de audio ES7210 com dois microfones e canal de referencia de eco;
- saida ES8311, amplificador e alto-falante de 1 W;
- IMU QMI8658;
- cartao microSD e um botao de usuario.

## Privacidade inicial

- modo local por padrao: nao associa ao Wi-Fi, nao consulta OTA e nao abre o
  protocolo de audio/IA;
- nenhum servidor publico vem configurado no firmware;
- palavra de ativacao desabilitada; voz e iniciada pelo botao;
- camera bloqueada por padrao;
- pressao longa libera uma unica foto por no maximo 60 segundos;
- o quadro capturado e descartado depois da analise;
- nenhuma imagem ou audio e armazenado por padrao;
- toda resposta visual deve separar fatos observaveis de inferencias;
- sinais faciais nunca sao tratados como prova do estado emocional;
- medicamentos sao verificados por rotulo, embalagem, codigo de barras ou QR,
  sempre com confirmacao humana;
- comprimidos soltos nao sao identificados apenas pela aparencia;
- o sistema nao sugere dose nem alteracao de tratamento.

Veja [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e
[docs/SAFETY_PRIVACY.md](docs/SAFETY_PRIVACY.md). O reaproveitamento do primeiro
firmware esta descrito em [docs/MIGRATION.md](docs/MIGRATION.md).

## Base e compilacao

O hardware parte do XiaoZhi ESP32 `v2.0.3`, a mesma versao encontrada no
aparelho. Consulte [UPSTREAM.md](UPSTREAM.md) e o README original preservado em
[docs/UPSTREAM_README.md](docs/UPSTREAM_README.md).

Requisitos:

- ESP-IDF 5.5;
- alvo `esp32s3`;
- placa `lichuang-dev`;
- cabo USB conectado pela porta que expoe COM7 e COM13 neste computador.

Fluxo previsto:

```powershell
idf.py set-target esp32s3
idf.py build
idf.py -p COM13 flash monitor
```

No firmware local de diagnostico:

- clique curto: inicia a captura do microfone;
- outro clique curto: encerra e reproduz o trecho no alto-falante;
- pressao longa: autoriza uma foto, captura e mostra a previa na tela;
- nenhuma dessas operacoes inicia Wi-Fi ou envia dados.

Ainda nao grave este firmware como versao de uso diario. A etapa `0.1.0`
estabelece a base de hardware e as barreiras de consentimento; o fluxo local de
crise e o backend multimodal privado serao integrados antes da validacao final.

Para habilitar servicos remotos em uma compilacao futura, sera necessario ativar
`CONFIG_COMPANION_REMOTE_SERVICES` e informar um `CONFIG_OTA_URL` privado. Essa
opcao permanece desligada nos defaults.

## Limites

Companion2 nao substitui avaliacao medica, psicologica ou psiquiatrica,
cuidadores, pessoas de confianca ou servicos de emergencia. O dispositivo nao
garante seguranca por observacao de camera e nao declara diagnosticos.
