'use strict';
const assert = require('node:assert/strict');
const { createAutonomy } = require('./autonomy');
(async () => {
  let remote = { scaleVersion: 2, enabled: false, level: 0, revision: 0, expiresAt: 0 }, failed = false;
  const events = [], notifications = [];
  const client = createAutonomy({
    connection: { enabled: true, url: 'http://127.0.0.1:8810', token: 'test' },
    notify: state => notifications.push(state), send: async text => events.push(text),
    request: async (_url, options) => {
      if (failed) return new Response('', { status: 503 });
      if (options.body) {
        const { action, requestId } = JSON.parse(options.body); assert(requestId);
        if (action === 'toggle') remote = { ...remote, enabled: !remote.enabled, level: 0, revision: remote.revision + 1 };
        if (remote.enabled && action === 'more' && remote.level < 3) remote = { ...remote, level: remote.level + 1, revision: remote.revision + 1 };
        if (remote.enabled && action === 'less' && remote.level > -3) remote = { ...remote, level: remote.level - 1, revision: remote.revision + 1 };
      }
      return Response.json(remote);
    },
  });
  try {
    await client.load(); await client.change('more'); assert.equal(events.length, 0);
    await client.change('toggle'); assert.equal(client.snapshot().enabled, true);
    await Promise.all([client.change('more'), client.change('more'), client.change('more')]);
    assert.equal(client.snapshot().level, 3); assert.match(events.at(-1), /sem aprovação prévia/);
    await client.change('less'); assert.equal(client.snapshot().level, 2); assert.match(events.at(-1), /85%/);
    for (let i = 0; i < 6; i++) await client.change('less');
    assert.equal(client.snapshot().level, -3); assert.equal(client.snapshot().enabled, true); assert.match(events.at(-1), /cada etapa/);
    await client.change('toggle'); assert.equal(client.snapshot().enabled, false); assert.match(events.at(-1), /DESATIVADO/);
    failed = true; const count = events.length; await client.change('toggle');
    assert.equal(client.snapshot().unavailable, true); assert.equal(events.length, count);
    assert(notifications.some(state => state.bridge === 'accepted'));
    console.log('AUTONOMY_OK: níveis, limites, desligamento, sequência, evento para ponte e falha sem falsa ativação.');
  } finally { client.stop(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
