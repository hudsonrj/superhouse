'use strict';
// Run on NoteAlliedIT. Loads authentication locally; never prints the key.
const fs = require('fs');
const path = require('path');
const { DATA_DIR } = require('../src/main/config');

async function main() {
  const text = process.argv.slice(2).join(' ').trim();
  if (!text) throw new Error('Uso: node scripts/nino-speak.js "texto para falar"');
  const config = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'atom-config.json'), 'utf8'));
  const response = await fetch(`http://${config.host}:3082/speak`, {
    method: 'POST', signal: AbortSignal.timeout(60000),
    headers: { Authorization: `Bearer ${config.token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
  console.log('Mensagem exibida no Nino e falada no computador.');
}
main().catch((err) => { console.error(err.message); process.exitCode = 1; });
