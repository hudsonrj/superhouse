'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { DATA_DIR } = require('../main/config');

function createSensorAutonomy({ request = fetch, connection } = {}) {
  return async ({ state, cycle }) => {
    const config = connection || JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'ch8-config.json'), 'utf8'));
    if (!config.enabled || !config.token) throw new Error('Control nao configurado.');
    const url = new URL('/autonomy', config.url);
    const privateHost = /^(127\.0\.0\.1|localhost|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d+\.\d+)$/.test(url.hostname);
    if (url.username || url.password || (url.protocol !== 'https:' && !(url.protocol === 'http:' && privateHost))) throw new Error('Endereco do Control invalido.');
    const response = await request(url, {
      method: 'POST', redirect: 'error', signal: AbortSignal.timeout(10000),
      headers: { Authorization: `Bearer ${config.token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: state === 'absent' ? 'sensor-absent' : 'sensor-clear', cycle, requestId: crypto.randomUUID() }),
    });
    if (!response.ok) throw new Error(`Control HTTP ${response.status}`);
    const result = await response.json();
    if (typeof result.enabled !== 'boolean' || !Number.isInteger(result.level) || result.level < -3 || result.level > 3 || !Number.isInteger(result.revision) || !Number.isInteger(result.expiresAt) || result.scaleVersion !== 2 || !['sensor', 'manual', 'none'].includes(result.source)) throw new Error('Estado de autonomia invalido.');
    return result;
  };
}
module.exports = { createSensorAutonomy };
