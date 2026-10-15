'use strict';
// Manual live check: sends one real request, shows the reply and speaks on Windows.
const fs = require('fs/promises');
const path = require('path');
const { spawn } = require('child_process');
const { createChatSession } = require('../src/main/chat');
const { notifyPresence } = require('../src/server/presence');
const { synthesize } = require('../src/main/tts');
const { DATA_DIR } = require('../src/main/config');

async function main() {
  const settings = JSON.parse(await fs.readFile(path.join(DATA_DIR, 'atom-config.json'), 'utf8'));
  const question = 'CH8, responda apenas: Nino conectado ao Control.';
  const result = await createChatSession().ask(question);
  if (!result.ok) throw new Error(result.error);
  await notifyPresence(settings.token, { type: 'transcript', text: question });
  await notifyPresence(settings.token, { type: 'answer', text: result.text });
  const file = path.join(DATA_DIR, 'atom', 'ch8-live-reply.wav');
  await fs.writeFile(file, await synthesize(result.text));
  await new Promise((resolve, reject) => {
    const child = spawn('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command',
      '(New-Object System.Media.SoundPlayer $env:NINO_REPLY_WAV).PlaySync()'], {
      windowsHide: true, env: { ...process.env, NINO_REPLY_WAV: file }, stdio: 'ignore',
    });
    child.on('error', reject);
    child.on('exit', (code) => code === 0 ? resolve() : reject(new Error('Falha na voz do Windows.')));
  });
  console.log('Control -> Nino -> voz no Windows:', result.text);
}
main().catch((err) => { console.error(err.message); process.exitCode = 1; });
