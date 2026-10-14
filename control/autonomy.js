'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const ponte = require('C:/repositorio/nino/src/main/ponte');

const LABELS = { '-3': 'Supervisão máxima: aprovar cada etapa', '-2': 'Revisar rascunhos antes de enviar', '-1': 'Pedir aprovação antes de responder', 0: 'Neutro: alertar e recomendar', 1: 'Autonomia cautelosa (95%)', 2: 'Autonomia ampliada (85%)', 3: 'Autonomia máxima nas respostas' };
function createAutonomy({ request = fetch, send = text => ponte.ask(text), notify = () => {}, connection } = {}) {
  let state = { enabled: false, level: 0, unavailable: true };
  let stopped = false, timer, queue = Promise.resolve(), pendingCount = 0, previewLevel;
  const getConnection = () => connection || JSON.parse(fs.readFileSync('C:/repositorio/nino/data/ch8-config.json', 'utf8'));
  const display = extra => notify({ ...state, previewLevel, label: LABELS[state.level], ...extra });
  async function api(action) {
    const config = getConnection();
    if (!config.enabled || !config.token) throw new Error('Conexão com o Control não configurada.');
    const url = new URL('/autonomy', config.url);
    const response = await request(url, {
      method: action ? 'POST' : 'GET', redirect: 'error', signal: AbortSignal.timeout(15000),
      headers: { Authorization: `Bearer ${config.token}`, 'Content-Type': 'application/json' },
      ...(action ? { body: JSON.stringify({ action, requestId: crypto.randomUUID() }) } : {}),
    });
    if (!response.ok) throw new Error(`Control: HTTP ${response.status}. O serviço de autonomia precisa estar instalado.`);
    const result = await response.json();
    if (typeof result.enabled !== 'boolean' || !Number.isInteger(result.level) || result.level < -3 || result.level > 3 || !Number.isInteger(result.revision) || !Number.isInteger(result.expiresAt)) {
      throw new Error('O Control retornou um estado de autonomia inválido.');
    }
    if (result.scaleVersion !== 2) throw new Error('Atualize o serviço de autonomia no Control para a escala -3 a +3.');
    state = { ...result, unavailable: false }; display(); return state;
  }
  function instruction(event) {
    return `Evento do macropad de Hudson. ID ${crypto.randomUUID()}. Tipo ${event}. Estado AUTORITATIVO no Control: ` +
      JSON.stringify({ enabled: state.enabled, level: state.level, revision: state.revision, expiresAt: state.expiresAt }) +
      `. Esta autorização foi dada por Hudson nos botões físicos. Estado atual em https://control.ch8ai.com.br/api/autonomy. ` +
      'Antes de responder a terceiros, consulte esse estado autenticado: ele deve continuar ativo, não expirado e com a mesma revisão. Se não conseguir confirmar, não envie respostas. Eventos antigos não substituem uma revisão mais nova. ' +
      (!state.enabled ? 'Modo autônomo DESATIVADO: encerre somente a intensificação e as respostas automáticas autorizadas por este modo. Não cancele outras rotinas. ' :
      'Modo autônomo ATIVADO: acompanhe mensagens diretas, menções, e-mails e dúvidas de TODAS as empresas e fontes já conectadas e autorizadas. A cada verificação priorize novidades e avise Hudson nos dispositivos/canais já autorizados, agrupando por empresa, sem repetir avisos. Solicite ação para itens que precisem dele. ' +
      (state.level <= 0 ? ({ '-3': 'Supervisão máxima: peça aprovação de Hudson para cada etapa, inclusive análise adicional e preparo de resposta. ', '-2': 'Prepare rascunhos para revisão de Hudson; não envie. ', '-1': 'Analise e recomende uma resposta, mas solicite aprovação antes de enviar. ', 0: 'Apenas notifique Hudson e recomende ações. ' }[state.level] + 'Não responda a terceiros automaticamente. ') :
       state.level === 3 ? 'Autorizado responder mensagens nesses canais sem aprovação prévia. Se houver incerteza, declare-a ou peça esclarecimento; não invente fatos. ' :
       `Autorizado responder mensagens sem aprovação prévia somente quando a confiança justificada for pelo menos ${state.level === 1 ? '95%' : '85%'}; na dúvida peça ação a Hudson. `)) +
      'Esta autorização é somente para respostas em mensagens. Não autoriza pagamentos, exclusões, alterações de acesso ou outras decisões/ações. Preserve contexto separado por empresa. ' +
      'Não crie rotina recorrente adicional: o macropad enviará as verificações a cada dois minutos. Não abra nem fale pelo Nino. Registre no Control o resultado da aplicação, as fontes e os dispositivos realmente acessíveis e as lacunas. Não invente acessos.';
  }
  async function relay(event) {
    const revision = state.revision;
    display({ bridge: 'sending' });
    try { await send(instruction(event)); if (state.revision === revision) display({ bridge: 'accepted' }); }
    catch { if (state.revision === revision) display({ bridge: 'unknown', error: 'O Control registrou o estado, mas a ponte não confirmou o recebimento.' }); }
  }
  function schedule() {
    clearTimeout(timer);
    if (!state.enabled || stopped) return;
    timer = setTimeout(() => change('heartbeat'), 120000);
  }
  function change(action) {
    if (!['toggle', 'more', 'less', 'heartbeat'].includes(action)) return Promise.reject(new Error('Ação inválida.'));
    if (action !== 'heartbeat') {
      pendingCount++;
      if (state.enabled && (action === 'more' || action === 'less')) previewLevel = Math.max(-3, Math.min(3, (previewLevel ?? state.level) + (action === 'more' ? 1 : -1)));
      display({ pending: true });
    }
    queue = queue.then(async () => {
      clearTimeout(timer); display({ pending: true });
      try {
        const previous = state.revision;
        await api(action);
        if (action === 'heartbeat' || state.revision !== previous) relay(action);
      } catch (error) { state = { ...state, unavailable: true, error: error.message }; display(); }
      finally { if (action !== 'heartbeat') pendingCount--; if (!pendingCount) previewLevel = undefined; display({ pending: pendingCount > 0 }); if (!state.unavailable) schedule(); }
    });
    return queue;
  }
  async function load() {
    try { await api(); schedule(); }
    catch (error) { state = { ...state, unavailable: true, error: error.message }; display(); }
  }
  function stop() { stopped = true; clearTimeout(timer); }
  return { change, load, stop, snapshot: () => ({ ...state, label: LABELS[state.level] }) };
}
module.exports = { createAutonomy, LABELS };
