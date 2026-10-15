# Ausencia provavel e acompanhamento mobile

O Atom envia `POST /sensor-status` autenticado, com `{"motion":true|false}`,
a cada 30 segundos e quando detecta movimento. O Nino nao abre sua janela.
Dez minutos sem movimento iniciam uma verificacao pela ponte existente; novas
verificacoes ocorrem a cada cinco minutos enquanto a ausencia persistir.
Movimento ou voz pelo Atom encerram esse modo. `GET /sensor-status`, autenticado,
permite consultar estado e horarios do ultimo sinal e da ultima atividade.

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
O evento de ausencia nao concede autorizacao para responder a terceiros nem
executar decisoes. Respostas automaticas exigem confirmacao do estado manual
vigente no Control, respeitando nivel, revisao e validade; decisoes fora desse
escopo continuam exigindo aprovacao. As verificacoes sao disparadas pelo Nino;
nenhuma rotina recorrente adicional e criada na nuvem. Veja a [politica de
autonomia](../../docs/OPERACAO.md).

Aceitacao HTTP do webhook confirma envio, nao confirma execucao do GrokBot ou
entrega mobile. Falhas nao sao repetidas imediatamente; consulte os logs privados
`data/startup/atom.log` e o painel da rotina. Computador, Atom e internet precisam
estar disponiveis. Um PIR mede movimento: uma pessoa imovel pode parecer ausente.

Testes: `node scripts/test-absence.js`, `node scripts/test-presence.js` e
`node scripts/test-atom.js`. Firmware: `python -m platformio run -d firmware/atom-voice`.
Instalacao depende do Atom conectado por USB e da porta confirmada; nao use portas
Bluetooth e nao apague a flash inteira.
