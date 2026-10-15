'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { setTimeout: sleep } = require('timers/promises');
const { DATA_DIR } = require('./config');

function command(text) {
  const match = String(text).match(/^\s*(?:\/ch8\b|ch\s*(?:8|oito)\b|c[eê]\s+ag[aá]\s+oito\b)[\s,:-]*(.+)$/is);
  return match ? match[1].trim() : null;
}

function settings() {
  const file = path.join(DATA_DIR, 'ch8-config.json');
  if (!fs.existsSync(file)) throw new Error('Integração CH8 ainda não configurada.');
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (!data.enabled || !data.url || !data.token) throw new Error('Integração CH8 ainda não habilitada.');
  const url = new URL(data.url);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error('Endereço CH8 inválido.');
  return data;
}

async function ask(text, { signal, connection = settings(), request = fetch } = {}) {
  // O contrato /chat foi inspecionado no orquestrador da ponte Raspberry Pi.
  // Cada pedido envia somente a mensagem explícita, sem o histórico/local KB.
  const combinedSignal = AbortSignal.any([...(signal ? [signal] : []), AbortSignal.timeout(180000)]);
  const headers = { Authorization: `Bearer ${connection.token}`, 'Content-Type': 'application/json' };
  const requestId = crypto.randomUUID();
  const response = await request(new URL('/chat', connection.url), {
    method: 'POST', redirect: 'error',
    signal: combinedSignal,
    headers,
    body: JSON.stringify({ messages: [{ role: 'user', content: text }], stream: false,
      ...(connection.protocol === 'control' ? { requestId } : {}) }),
  });
  if (!response.ok) throw new Error(`Ponte CH8 retornou HTTP ${response.status}.`);
  if (!response.headers.get('content-type')?.includes('application/json')) {
    throw new Error('Ponte CH8 retornou uma página, não uma resposta da API. Verifique a autenticação.');
  }
  let result = await response.json();
  if (connection.protocol === 'control' && response.status === 202) {
    if (result.id !== requestId) throw new Error('Identificador inválido da ponte CH8.');
    while (result.status === 'pending') {
      await sleep(1000, undefined, { signal: combinedSignal });
      const poll = await request(new URL(`/jobs/${requestId}`, connection.url), {
        headers, redirect: 'error', signal: combinedSignal,
      });
      if (!poll.ok || !poll.headers.get('content-type')?.includes('application/json')) {
        throw new Error('Não foi possível acompanhar o pedido no Control.');
      }
      result = await poll.json();
    }
    if (!['done', 'error'].includes(result.status)) throw new Error('Estado inválido do pedido CH8.');
  }
  if (result.error) throw new Error(String(result.error));
  if (typeof result.response !== 'string' || !result.response.trim()) throw new Error('Ponte CH8 não retornou resposta.');
  if (!result.response.replace(/_\(IA local sem resposta[^\n]*\)_/g, '').trim()) {
    throw new Error('O modelo da ponte CH8 não respondeu; o aviso de fallback não é uma resposta.');
  }
  return { text: result.response, stats: { provider: 'ch8' } };
}

module.exports = { command, ask };
