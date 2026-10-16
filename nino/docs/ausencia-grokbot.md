# Ausencia provavel e acompanhamento mobile

Verificacao fisica em 15/10/2026: Atom ESP32-PICO-D4 identificado na COM20;
firmware gravado pelo PlatformIO a 115200, com hash verificado. O Atom encontrou
a rede Offline de 2,4 GHz no canal 1, mas a conexao falhou com motivo 2
(`WIFI_REASON_AUTH_EXPIRE`). O servico continuou com `lastHeartbeat:null` e
autonomia desligada. A instalacao do firmware nao comprova funcionamento do
detector; faltam conexao Wi-Fi e o teste fisico de dez minutos sem movimento.
A tentativa de backup completo da flash foi interrompida; nao ha backup novo
validado. O checkpoint anterior permanece preservado.

O Atom envia `POST /sensor-status` autenticado, com `{"motion":true|false}`,
a cada 30 segundos e quando detecta movimento. O Nino nao abre sua janela.
Dez minutos sem movimento iniciam uma verificacao pela ponte existente; novas
verificacoes ocorrem a cada cinco minutos enquanto a ausencia persistir.
O detector registra `sensor-absent` no estado autoritativo do Control, em nivel
neutro 0 (alertar e recomendar), sem habilitar respostas automaticas a terceiros.
Renovacoes a cada 30 segundos mantem um lease de 90 segundos. No retorno ou
desconexao, `sensor-clear` desliga apenas uma ativacao ainda pertencente ao sensor.
Controles manuais assumem prioridade, inclusive se desligarem durante a ausencia:
o mesmo ciclo nao reativa o modo. O indicador existente do Control le a mesma API.
O webhook solicita que o indicador existente do GrokBot use essa fonte; aceitacao
do webhook nao confirma que a interface remota foi atualizada.
Movimento ou voz pelo Atom encerram esse modo. `GET /sensor-status`, autenticado,
permite consultar estado e horarios do ultimo sinal e da ultima atividade.
Inclui tambem `autonomy`, o ultimo estado recebido do Control; `unavailable:true`
significa que ele nao foi confirmado. Nessa condicao, o evento nao solicita
intensificacao de acompanhamento nem envio de alertas mobile.

Sem sinais por 90 segundos, o estado vira desconhecido e a intensificacao e
suspensa. Reiniciar o servico tambem reinicia a contagem; o primeiro sinal informa
estado desconhecido a ponte para limpar uma ausencia anterior. Sem firmware novo,
nenhuma ausencia e inferida somente pela falta de eventos antigos `/presence`.
Durante uma conversa longa, o firmware pode parar de enviar sinais: nesse caso
o modo e suspenso, em vez de presumir que a pessoa saiu.

Cada mensagem da ponte inclui identificador e instrucoes para acompanhar todas
as empresas/fontes ja autorizadas, priorizar mencoes, mensagens diretas, emails
urgentes e decisoes pendentes e avisar Hudson pelos canais mobile ja autorizados.
O agente deve agrupar por empresa, evitar duplicacoes e informar acessos ausentes.
Responder a terceiros exige autorizacao manual vigente no Control; o sensor
nao eleva o nivel. Executar outras decisoes requer aprovacao. As verificacoes
sao disparadas pelo Nino; nenhuma rotina recorrente adicional e criada na nuvem.

Aceitacao HTTP do webhook confirma envio, nao confirma execucao do GrokBot ou
entrega mobile. Falhas nao sao repetidas imediatamente; consulte os logs privados
`data/startup/atom.log` e o painel da rotina. Computador, Atom e internet precisam
estar disponiveis. Um PIR mede movimento: uma pessoa imovel pode parecer ausente.

Testes: `node scripts/test-absence.js`, `node scripts/test-presence.js` e
`node scripts/test-atom.js`. Firmware: `python -m platformio run -d firmware/atom-voice`.
Instalacao depende do Atom conectado por USB e da porta confirmada; nao use portas
Bluetooth e nao apague a flash inteira.

Modulo remoto: `scripts/control-autonomy-server.py`, instalado no action-inbox
existente por `scripts/control-autonomy-ssh.py --deploy`, com senha interativa e
backup `.before-nino-sensor`. O gateway e a interface existentes continuam usando
`/autonomy` e `/api/autonomy`. Uma reinstalacao antiga do modulo do macropad pode
remover as novas acoes: reaplique esta versao, sem apagar o banco de estado.
Testes de servidor: `python scripts/test-control-absence.py`. Teste real opcional:
`node scripts/test-sensor-autonomy-live.js` ativa brevemente nivel 0 e limpa o
estado, recusando executar se o modo ja estiver ativo. Nao comprova o sensor fisico.

## Integração Superhouse

Consulte a [operação conjunta](../../docs/OPERACAO.md), os [contratos de autonomia](../../docs/CONFIGURACAO.md) e o [guia do Nino](../GUIA-SUPERHOUSE.md).
