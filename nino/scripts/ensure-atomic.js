'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const { setTimeout: sleep } = require('node:timers/promises');
const directory = path.join(__dirname, '..', 'data', 'startup');
const modelFile = path.join(directory, 'atomic-model.json');

async function connect() {
  const core = path.join(os.homedir(), 'AppData', 'Roaming', 'Atomic Chat', 'data', 'atomic-core');
  const instance = JSON.parse(await fs.readFile(path.join(core, 'instance.lock'), 'utf8'));
  if (!Number.isInteger(instance.control_port) || instance.control_port < 1 || instance.control_port > 65535) throw new Error('Porta de controle Atomic invalida.');
  const token = (await fs.readFile(path.join(core, 'control-token'), 'utf8')).trim();
  return async (route, body) => {
    const response = await fetch(`http://127.0.0.1:${instance.control_port}/atomic/v1${route}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      redirect: 'error', signal: AbortSignal.timeout(body === undefined ? 5000 : route.endsWith('/load') ? 600000 : 30000),
    });
    if (!response.ok) throw new Error(`Controle Atomic: HTTP ${response.status}.`);
    return response.json();
  };
}

async function main() {
  if (process.argv.includes('--capture')) {
    const call = await connect();
    const { sessions } = await call('/sessions');
    const session = sessions.find(s => !s.is_embedding);
    if (!session) throw new Error('Carregue um modelo de conversa no Atomic antes de configurar.');
    await fs.mkdir(directory, { recursive: true });
    await fs.writeFile(modelFile, JSON.stringify({ provider: session.provider, model: session.model_id }, null, 2));
    console.log('Modelo atual salvo para retomada no login.');
    return;
  }
  const selected = JSON.parse(await fs.readFile(modelFile, 'utf8'));
  if (!/^[a-z0-9-]+$/i.test(selected.provider) || typeof selected.model !== 'string' || !selected.model || /[?#\r\n]/.test(selected.model)) throw new Error('Modelo de retomada invalido.');
  const deadline = Date.now() + 120000;
  let call, sessions;
  while (true) {
    try { call = await connect(); ({ sessions } = await call('/sessions')); break; }
    catch (err) { if (Date.now() >= deadline) throw err; await sleep(2000); }
  }
  const state = await call('/server');
  if (!state.running) await call('/server/start', { host: '127.0.0.1', port: 1337, prefix: '/v1', state_file: true });
  if (!sessions.some(s => s.provider === selected.provider && s.model_id === selected.model)) {
    await call(`/models/${selected.provider}/${selected.model.split('/').map(encodeURIComponent).join('/')}/load`, {});
  }
  console.log('API e modelo do Atomic prontos.');
}
main().catch(err => { console.error(err.message); process.exitCode = 1; });
