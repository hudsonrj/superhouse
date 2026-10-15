'use strict';
const fs = require('fs');
const path = require('path');
const { DATA_DIR } = require('./config');

function command(text) {
  const match = String(text).match(/^\s*(?:\/ponte\b|ponte\b)[\s,:-]*(.+)$/is);
  return match ? match[1].trim() : null;
}

function settings() {
  const file = path.join(DATA_DIR, 'ponte-config.json');
  if (!fs.existsSync(file)) throw new Error('Webhook da ponte ainda não configurado.');
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function validate(connection) {
  if (!connection?.enabled || !connection.url || !connection.authHeader || !connection.authValue) {
    throw new Error('Configure URL e autenticação do webhook da ponte.');
  }
  let url;
  try { url = new URL(connection.url); } catch { throw new Error('URL do webhook da ponte inválida.'); }
  const privateHost = /^(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d+\.\d+)$/.test(url.hostname);
  if (url.username || url.password || (url.protocol !== 'https:' && !(url.protocol === 'http:' && privateHost))) {
    throw new Error('Use HTTPS para o webhook na nuvem ou HTTP em endereço privado.');
  }
  if (!/^[a-z0-9-]+$/i.test(connection.authHeader) ||
      /^(host|content-type|content-length|connection|transfer-encoding)$/i.test(connection.authHeader) ||
      typeof connection.authValue !== 'string' || /[\r\n]/.test(connection.authValue)) {
    throw new Error('Cabeçalho de autenticação do webhook inválido.');
  }
  return url;
}

async function ask(text, { signal, connection = settings(), request = fetch } = {}) {
  const url = validate(connection);
  if (typeof text !== 'string' || !text.trim() || text.length > 8000) throw new Error('Pergunta da ponte deve ter 1 a 8000 caracteres.');
  let response;
  try {
    response = await request(url, {
      method: 'POST', redirect: 'error',
      signal: AbortSignal.any([...(signal ? [signal] : []), AbortSignal.timeout(15000)]),
      headers: { 'Content-Type': 'application/json', [connection.authHeader]: connection.authValue },
      body: JSON.stringify({ text: text.trim() }),
    });
  } catch {
    // Do not expose webhook URLs or authentication values through transport errors.
    throw new Error('Não foi possível confirmar o envio à ponte. Confira a rotina antes de reenviar.');
  }
  if (!response.ok) {
    await response.body?.cancel();
    throw new Error(`Webhook da ponte retornou HTTP ${response.status}.`);
  }
  await response.body?.cancel();
  return {
    accepted: true,
    text: 'Pergunta enviada à ponte. A resposta chegará por voz.',
    stats: { provider: 'grokbot-ponte' },
  };
}

module.exports = { command, ask, validate };
