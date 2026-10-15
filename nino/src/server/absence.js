'use strict';
const ponte = require('../main/ponte');

const TEN_MINUTES = 10 * 60 * 1000;
const HEARTBEAT_LIMIT = 90 * 1000;
const CHECK_INTERVAL = 5 * 60 * 1000;

function createAbsenceMonitor({ now = Date.now, send = text => ponte.ask(text), report = console.log } = {}) {
  let seen = null;
  let activity = null;
  let state = 'unknown';
  let notified = null;
  let sequence = 0;
  let sending = false;
  let pending = null;
  function event(kind) {
    if (sending) { pending = kind; return; }
    sending = true;
    const id = `nino-presenca-${now()}-${++sequence}`;
    const instruction = kind === 'absent' || kind === 'check'
      ? 'Ausencia provavel: pelo menos 10 minutos sem movimento, com sensor conectado. Nesta verificacao, acompanhe mencoes, mensagens diretas, emails urgentes e decisoes pendentes de TODAS as empresas e contas JA autorizadas e conectadas. Priorize urgencias e notifique Hudson nos canais mobile JA autorizados; agrupe por empresa e evite notificacoes duplicadas. A intensificacao por ausencia apenas analisa, prioriza e notifica Hudson. Nao responda a terceiros sem autorizacao vigente confirmada no modo autonomo do Control em https://control.ch8ai.com.br/api/autonomy; respeite o nivel, a revisao e a validade antes de cada resposta. Com estado desconhecido, expirado ou desativado, nao responda a terceiros. Este evento nao ativa, desativa nem altera o modo autonomo. Nao aprove nem execute outras decisoes sem aprovacao. Nao invente acessos: informe canais ou fontes indisponiveis. Nino enviara novas verificacoes a cada 5 minutos enquanto a ausencia persistir; nao crie outra rotina recorrente nem envie a resposta para a voz do computador.'
      : kind === 'present'
        ? 'Movimento voltou a ser detectado. Encerre a intensificacao por ausencia e volte ao acompanhamento normal. Nao abra nem fale pelo Nino. Nao cancele outras rotinas do usuario.'
        : 'Sensor indisponivel ou reiniciando: presenca desconhecida. Suspenda apenas a intensificacao causada pela ausencia; mantenha as outras rotinas. Nao interprete desconexao como ausencia.';
    notified = now();
    report(`[Ausencia] ${kind}; evento ${id}`);
    Promise.resolve().then(() => send(`Evento automatico do Nino. ID: ${id}. Estado: ${kind}. ${instruction}`))
      .then(() => report(`[Ausencia] Ponte aceitou ${id}; execucao e entrega mobile dependem do agente remoto.`))
      .catch(() => report(`[Ausencia] Falha ao confirmar evento ${id}; nao reenviado automaticamente.`))
      .finally(() => {
        sending = false;
        if (pending) { const next = pending; pending = null; event(next); }
      });
  }
  function heartbeat(motion) {
    if (typeof motion !== 'boolean') throw new Error('motion deve ser booleano.');
    const time = now();
    if (seen === null || time - seen > HEARTBEAT_LIMIT) {
      activity = time;
      state = 'unknown';
      event('unknown');
    }
    seen = time;
    if (motion) activity = time;
    if (state === 'unknown' || (motion && state === 'absent')) {
      const returning = state === 'absent';
      state = 'present';
      if (returning) event('present');
    }
  }
  function touch() {
    if (seen === null) return;
    activity = now();
    if (state === 'absent') { state = 'present'; event('present'); }
  }
  function tick() {
    if (seen === null) return;
    const time = now();
    if (time - seen > HEARTBEAT_LIMIT) {
      if (state !== 'unknown') { state = 'unknown'; event('unknown'); }
      return;
    }
    if (state === 'present' && time - activity >= TEN_MINUTES) {
      state = 'absent'; event('absent');
    } else if (state === 'absent' && time - notified >= CHECK_INTERVAL) event('check');
  }
  return { heartbeat, touch, tick, snapshot: () => ({ state, lastHeartbeat: seen, lastActivity: activity }) };
}
module.exports = { createAbsenceMonitor };
