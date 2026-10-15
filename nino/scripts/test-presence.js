'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { once } = require('events');
const { createPresenceServer } = require('../src/server/presence');
test('presenca autenticada nao abre Nino; eventos de voz continuam funcionando', async () => {
  let opened = 0;
  const events = [];
  const token = 'a'.repeat(48);
  const server = createPresenceServer({ token, onPresence: () => opened++, onVoice: e => events.push(e) });
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  const url = `http://127.0.0.1:${server.address().port}`;
  const headers = { Authorization: `Bearer ${token}` };
  try {
    assert.equal((await fetch(url + '/presence', { method: 'POST' })).status, 401);
    assert.equal((await fetch(url + '/presence', { headers })).status, 404);
    assert.equal(opened, 0);
    for (let i = 0; i < 2; i++) assert.equal((await fetch(url + '/presence', { method: 'POST', headers })).status, 204);
    assert.equal(opened, 0);
    const event = { type: 'transcript', text: 'Olá, Nino' };
    assert.equal((await fetch(url + '/voice-event', { method: 'POST', headers, body: JSON.stringify(event) })).status, 204);
    assert.deepEqual(events, [event]);
    assert.equal((await fetch(url + '/voice-event', { method: 'POST', headers, body: JSON.stringify({type: 'execute', text: 'x'}) })).status, 400);
    assert.equal(events.length, 1);
  } finally { server.closeAllConnections(); await new Promise(r => server.close(r)); }
});
