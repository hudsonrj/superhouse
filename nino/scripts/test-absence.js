'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createAbsenceMonitor } = require('../src/server/absence');
const flush = () => new Promise(resolve => setImmediate(resolve));

test('ausencia em 10 minutos, verificacoes em 5 minutos e retorno sem duplicar', async () => {
  let time = 0; const sent = [];
  const monitor = createAbsenceMonitor({ now: () => time, send: async text => sent.push(text), report: () => {} });
  monitor.tick(); assert.equal(sent.length, 0);
  monitor.heartbeat(true); await flush(); sent.length = 0;
  for (time = 30000; time < 600000; time += 30000) { monitor.heartbeat(false); monitor.tick(); }
  await flush(); assert.equal(sent.length, 0);
  monitor.heartbeat(false); monitor.tick(); await flush();
  assert.equal(monitor.snapshot().state, 'absent'); assert.equal(sent.length, 1);
  assert.match(sent[0], /Estado: absent/); assert.match(sent[0], /Nao responda a terceiros/);
  assert.match(sent[0], /Este evento nao ativa, desativa nem altera o modo autonomo/);
  assert.match(sent[0], /Com estado desconhecido, expirado ou desativado, nao responda a terceiros/);
  for (time = 630000; time <= 900000; time += 30000) { monitor.heartbeat(false); monitor.tick(); await flush(); }
  assert.equal(sent.length, 2); assert.match(sent[1], /Estado: check/);
  monitor.heartbeat(true); await flush(); monitor.heartbeat(true); monitor.tick(); await flush();
  assert.equal(sent.length, 3); assert.match(sent[2], /Estado: present/);
});

test('sensor desconectado, reinicio e pessoa em movimento nao geram ausencia', async () => {
  let time = 0; const sent = [];
  const monitor = createAbsenceMonitor({ now: () => time, send: async text => sent.push(text), report: () => {} });
  assert.throws(() => monitor.heartbeat('false'), /booleano/);
  monitor.heartbeat(false); await flush(); sent.length = 0;
  time = 600000; monitor.tick(); await flush();
  assert.equal(monitor.snapshot().state, 'unknown'); assert.match(sent[0], /Estado: unknown/);
  monitor.heartbeat(false); monitor.tick(); await flush();
  assert.equal(monitor.snapshot().state, 'present');
  for (time = 630000; time <= 1300000; time += 30000) { monitor.heartbeat(true); monitor.tick(); }
  await flush(); assert.ok(sent.every(text => !text.includes('Estado: absent')));
});

test('retorno durante envio pendente nao se perde; falha nao faz reenvio imediato', async () => {
  let time = 0; let finish; const sent = [];
  const monitor = createAbsenceMonitor({ now: () => time, send: text => { sent.push(text); return new Promise(resolve => { finish = resolve; }); }, report: () => {} });
  monitor.heartbeat(true); await flush(); finish(); await flush(); sent.length = 0;
  for (time = 30000; time <= 600000; time += 30000) { monitor.heartbeat(false); monitor.tick(); }
  await flush(); monitor.heartbeat(true); finish(); await flush();
  assert.equal(sent.length, 2); assert.match(sent[1], /Estado: present/); finish(); await flush();
});

test('rota do sensor exige autenticacao e valida movimento sem chamar a janela', async () => {
  const { once } = require('events');
  const { createAtomServer } = require('../src/server/atom');
  const monitor = createAbsenceMonitor({ send: async () => {}, report: () => {} });
  const token = 'a'.repeat(48);
  const server = createAtomServer({ token, absence: monitor });
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  const url = `http://127.0.0.1:${server.address().port}/sensor-status`;
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  try {
    assert.equal((await fetch(url)).status, 401);
    for (const body of ['{', '{"motion":"false"}', 'x'.repeat(1025)]) {
      assert.equal((await fetch(url, { method: 'POST', headers, body })).status, 400);
    }
    assert.equal((await fetch(url, { method: 'POST', headers, body: '{"motion":false}' })).status, 204);
    assert.equal((await (await fetch(url, { headers })).json()).state, 'present');
  } finally { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
});
