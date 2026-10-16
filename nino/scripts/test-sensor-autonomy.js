'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createSensorAutonomy } = require('../src/server/sensor-autonomy');
test('usa a mesma API do indicador com autenticacao e nao aceita estado antigo', async () => {
  const connection = { enabled: true, token: 'test', url: 'http://100.119.119.83:8810' };
  const sent = [];
  const client = createSensorAutonomy({ connection, request: async (url, options) => {
    assert.equal(url.pathname, '/autonomy'); assert.equal(options.headers.Authorization, 'Bearer test');
    sent.push(JSON.parse(options.body));
    return Response.json({ enabled: true, level: 0, scaleVersion: 2, revision: 1, expiresAt: 100, source: 'sensor' });
  } });
  await client({ state: 'absent', cycle: 'test-cycle' });
  await client({ state: 'unknown' });
  assert.equal(sent[0].action, 'sensor-absent'); assert.equal(sent[1].action, 'sensor-clear');
  assert.notEqual(sent[0].requestId, sent[1].requestId);
  const old = createSensorAutonomy({ connection, request: async () => Response.json({ enabled: true }) });
  await assert.rejects(old({ state: 'absent' }), /invalido/);
});
