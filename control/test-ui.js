'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const { app, BrowserWindow } = require('electron');
const originalGetPath = app.getPath.bind(app);
const testAppData = path.join(os.tmpdir(), 'ch8-ui-test-' + process.pid);
app.getPath = name => name === 'appData' ? testAppData : originalGetPath(name);
const crypto = require('node:crypto');
const { validQuestion, speechChunks } = require('./helpers');
const { createAutonomy } = require('./autonomy');
let policy = { scaleVersion: 2, enabled: false, level: 0, revision: 0, expiresAt: 0 };
require('./autonomy').createAutonomy = options => createAutonomy({
  ...options, connection: { enabled: true, url: 'http://127.0.0.1:8810', token: 'test' },
  send: async () => ({ accepted: true }),
  request: async (_url, request) => {
    if (request.body) {
      const { action } = JSON.parse(request.body);
      if (action === 'toggle') policy = { ...policy, enabled: !policy.enabled, level: 0, revision: policy.revision + 1 };
      else if (policy.enabled && action === 'more') policy = { ...policy, level: Math.min(3, policy.level + 1), revision: policy.revision + 1 };
      else if (policy.enabled && action === 'less') policy = { ...policy, level: Math.max(-3, policy.level - 1), revision: policy.revision + 1 };
    }
    return Response.json(policy);
  },
});
const nino = 'C:/repositorio/nino/src/main/';
assert.throws(() => validQuestion(' '));
assert.throws(() => validQuestion('a'.repeat(8001)));
const full = 'Uma resposta longa. '.repeat(1000);
assert.equal(speechChunks(full).join(''), full);
assert(speechChunks(full).every(chunk => chunk.length <= 1201));
const requests = [];
const localToken = crypto.randomBytes(32).toString('hex');
process.env.CH8_CONTROL_TOKEN = localToken;
process.env.CH8_CONTROL_PORT = '0';
let audioBytes = 0, speechCalls = 0, fail = false;
require(nino + 'ch8').ask = async text => {
  requests.push(text);
  if (fail) throw new Error('Control indisponível para teste');
  return { text: '# Resultado\n\n**Confirmado**\n\n- Item um\n- Item dois\n\n```python\nprint("ok")\n```\n<img src=x onerror=alert(1)>' };
};
require(nino + 'stt').transcribe = async file => {
  audioBytes = (await fs.stat(file)).size;
  return { text: 'Pergunta de voz para teste' };
};
require(nino + 'tts').synthesize = async () => {
  speechCalls++;
  const wav = Buffer.alloc(44 + 3200);
  wav.write('RIFF'); wav.writeUInt32LE(wav.length - 8, 4); wav.write('WAVEfmt ', 8);
  wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(16000, 24); wav.writeUInt32LE(32000, 28);
  wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34); wav.write('data', 36); wav.writeUInt32LE(3200, 40);
  return wav;
};
app.commandLine.appendSwitch('use-fake-device-for-media-stream');
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
const service = require('./main');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(action, label) {
  for (let i = 0; i < 100; i++) { if (await action()) return; await sleep(100); }
  throw new Error('Tempo esgotado: ' + label);
}
app.whenReady().then(async () => {
  let window;
  await until(() => { window = BrowserWindow.getAllWindows().find(item => item.webContents.getURL().endsWith('/index.html')); return window && !window.webContents.isLoading(); }, 'janela');
  const evaluate = code => window.webContents.executeJavaScript(code);
  await until(() => evaluate('typeof window.control === "object"'), 'preload');
  await until(() => service.listening, 'canal local');
  const endpoint = `http://127.0.0.1:${service.address().port}/command`;
  const authorization = `Bearer ${localToken}`;
  assert.equal((await fetch(endpoint, { method: 'POST', body: '"text"' })).status, 403);
  assert.equal((await fetch(endpoint, { method: 'POST', headers: { authorization, Origin: 'https://example.com' }, body: '"text"' })).status, 403);
  assert.equal((await fetch(endpoint, { method: 'POST', headers: { authorization }, body: 'invalid' })).status, 400);
  assert.equal((await fetch(endpoint, { method: 'POST', headers: { authorization }, body: '"invalid-command"' })).status, 400);
  assert.equal((await fetch(endpoint, { method: 'POST', headers: { authorization }, body: '"warm"' })).status, 204);
  assert.equal(await evaluate('window.control.ask(" ").then(result => result.ok)'), false);
  assert.equal(await evaluate('window.control.transcribe(new Uint8Array()).then(result => result.ok)'), false);
  assert.equal(await evaluate('window.control.speech("x".repeat(1401)).then(result => result.ok)'), false);
  window.show(); window.webContents.send('command', 'text');
  await until(() => evaluate('document.activeElement.id === "question"'), 'foco do texto');
  await evaluate('document.getElementById("question").value = "Pergunta de texto"; document.getElementById("question").dispatchEvent(new KeyboardEvent("keydown", {key:"Enter",shiftKey:true,bubbles:true}));');
  assert.equal(requests.length, 0);
  await evaluate('document.getElementById("question").dispatchEvent(new KeyboardEvent("keydown", {key:"Enter",bubbles:true}));');
  await until(() => evaluate('document.getElementById("status").textContent === "Resposta recebida do Control."'), 'resposta de texto');
  assert.deepEqual(requests, ['Pergunta de texto']);
  assert.equal(await evaluate('document.querySelectorAll("#answer ul li").length'), 2);
  assert.equal(await evaluate('document.querySelectorAll("#answer pre code").length'), 1);
  assert.equal(await evaluate('document.querySelectorAll("#answer strong").length'), 1);
  assert.equal(await evaluate('document.querySelectorAll("#answer img").length'), 0);
  assert.equal(speechCalls, 0);
  await evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
  await sleep(300);
  await fs.writeFile(path.join(__dirname, 'preview.png'), (await window.webContents.capturePage()).toPNG());
  window.webContents.send('command', 'start');
  await until(() => evaluate('document.getElementById("status").className === "recording"'), 'gravacao');
  await sleep(600); window.webContents.send('command', 'stop');
  await until(() => evaluate('document.getElementById("status").textContent === "Resposta recebida do Control."'), 'voz completa');
  assert(audioBytes > 0); assert(speechCalls > 0);
  assert.equal(requests[1], 'Pergunta de voz para teste');
  fail = true;
  await evaluate('document.getElementById("form").requestSubmit()');
  await until(() => evaluate('document.getElementById("status").className === "error"'), 'erro visivel');
  assert.equal(await evaluate('document.getElementById("send").disabled'), false);
  window.webContents.send('command', 'text');
  await fetch(endpoint, { method: 'POST', headers: { authorization }, body: '"autonomy-toggle"' });
  await until(() => evaluate('document.getElementById("autonomy-status").className === "active"'), 'autonomia ativa');
  await fetch(endpoint, { method: 'POST', headers: { authorization }, body: '"autonomy-more"' });
  await until(() => evaluate('document.getElementById("autonomy-status").textContent.includes("+1 ·")'), 'autonomia nivel 1');
  const overlay = BrowserWindow.getAllWindows().find(item => item.webContents.getURL().endsWith('/autonomy-overlay.html'));
  assert(overlay.isVisible() && overlay.isAlwaysOnTop() && !overlay.isFocusable());
  await until(() => overlay.webContents.executeJavaScript('document.getElementById("level").textContent === "+1 · −3 a +3"'), 'indicador flutuante');
  assert.equal(await overlay.webContents.executeJavaScript('window.control.ask("teste").then(result => result.ok)'), false);
  await fetch(endpoint, { method: 'POST', headers: { authorization }, body: '"autonomy-less"' });
  await until(() => evaluate('document.getElementById("autonomy-status").textContent.includes("0 ·")'), 'reduzir autonomia');
  await fetch(endpoint, { method: 'POST', headers: { authorization }, body: '"autonomy-toggle"' });
  await until(() => evaluate('document.getElementById("autonomy-status").textContent.includes("desativado")'), 'desligar autonomia');
  console.log('UI_OK: canal autenticado, validacao, Enter, formatacao segura, gravacao/soltar, transcricao, consulta, audio, erro.');
  app.exit(0);
}).catch(error => { console.error(error); app.exit(1); });
