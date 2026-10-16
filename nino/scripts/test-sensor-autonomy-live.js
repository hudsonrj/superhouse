'use strict';
const assert = require('node:assert/strict');
const { randomUUID } = require('crypto');
const { createSensorAutonomy } = require('../src/server/sensor-autonomy');
const config = require('../data/ch8-config.json');
async function read() {
  const response = await fetch(new URL('/autonomy', config.url), { headers: { Authorization: `Bearer ${config.token}` }, signal: AbortSignal.timeout(10000), redirect: 'error' });
  assert.equal(response.status, 200); return response.json();
}
async function main() {
  const before = await read();
  if (before.enabled) throw new Error('Teste nao executado: modo ja ativo; preserve o controle manual.');
  const sync = createSensorAutonomy();
  try {
    const active = await sync({ state: 'absent', cycle: randomUUID() });
    assert.equal(active.enabled, true); assert.equal(active.level, 0); assert.equal(active.source, 'sensor');
    assert.equal((await read()).revision, active.revision);
    console.log('API compartilhada: sensor ativa nivel neutro confirmado.');
  } finally {
    const cleared = await sync({ state: 'present' });
    console.log('Estado apos limpeza:', JSON.stringify(cleared));
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
