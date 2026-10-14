'use strict';
const { app, BrowserWindow, ipcMain, screen } = require('electron');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const crypto = require('node:crypto');
const { pathToFileURL } = require('node:url');
const nino = 'C:/repositorio/nino/src/main';
const ch8 = require(path.join(nino, 'ch8'));
const stt = require(path.join(nino, 'stt'));
const tts = require(path.join(nino, 'tts'));
const { speechChunks, validQuestion } = require('./helpers');
const { createAutonomy } = require('./autonomy');

app.setPath('userData', path.join(app.getPath('appData'), 'CH8 Macropad'));
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
let window, ready = false, quitting = false, query;
let autonomyOverlay, overlayTimer;
const commands = [];
const autonomy = createAutonomy({ notify: state => {
  if (window && !window.isDestroyed()) window.webContents.send('autonomy-state', state);
  if (autonomyOverlay && !autonomyOverlay.isDestroyed()) autonomyOverlay.webContents.send('autonomy-state', state);
} });
const page = pathToFileURL(path.join(__dirname, 'index.html')).href;
function command(value) {
  if (!['warm', 'text', 'start', 'stop', 'autonomy-toggle', 'autonomy-more', 'autonomy-less'].includes(value)) return;
  if (!ready) { commands.push(value); return; }
  if (value === 'warm') return;
  if (value.startsWith('autonomy-')) {
    autonomyOverlay.webContents.send('autonomy-state', autonomy.snapshot());
    autonomyOverlay.showInactive();
    clearTimeout(overlayTimer);
    overlayTimer = setTimeout(() => autonomyOverlay.hide(), 6000);
    autonomy.change(value.slice('autonomy-'.length));
  }
  else {
    if (value !== 'stop') { window.show(); window.focus(); }
    window.webContents.send('command', value);
  }
  console.log(`CONTROL_COMMAND ${value} visible=${window.isVisible()}`);
}
const token = process.env.CH8_CONTROL_TOKEN || crypto.randomBytes(32).toString('hex');
delete process.env.CH8_CONTROL_TOKEN;
const service = http.createServer(async (request, response) => {
  const auth = Buffer.from(request.headers.authorization || '');
  const expected = Buffer.from(`Bearer ${token}`);
  if (request.method !== 'POST' || request.url !== '/command' || request.headers.origin ||
      auth.length !== expected.length || !crypto.timingSafeEqual(auth, expected)) {
    response.writeHead(403).end(); return;
  }
  let body = ''; let size = 0;
  try {
    for await (const chunk of request) {
      size += chunk.length;
      if (size > 256) { response.writeHead(413).end(); return; }
      body += chunk.toString('utf8');
    }
    const value = JSON.parse(body);
    if (!['warm', 'text', 'start', 'stop', 'quit', 'autonomy-toggle', 'autonomy-more', 'autonomy-less'].includes(value)) { response.writeHead(400).end(); return; }
    response.writeHead(204).end();
    if (value === 'quit') app.quit(); else command(value);
  } catch { if (!response.headersSent) response.writeHead(400).end(); }
});
service.on('error', error => { console.error('Canal local:', error.message); app.quit(); });

function handle(name, action) {
  ipcMain.handle(name, async (event, ...args) => {
    if (event.sender !== window.webContents || event.senderFrame.url !== page) {
      return { ok: false, error: 'Origem da solicitação inválida.' };
    }
    try { return { ok: true, value: await action(...args) }; }
    catch (error) { return { ok: false, error: error.message }; }
  });
}
handle('ask', async text => {
  validQuestion(text);
  if (query) throw new Error('Aguarde a resposta atual.');
  const controller = new AbortController(); query = controller;
  try { return (await ch8.ask(text, { signal: controller.signal })).text; }
  finally { if (query === controller) query = null; }
});
handle('transcribe', async audio => {
  if (!(audio instanceof Uint8Array) || !audio.length || audio.length > 12 * 1024 * 1024) {
    throw new Error('Gravação vazia ou grande demais.');
  }
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'ch8-mic-'));
  const file = path.join(directory, 'question.webm');
  try {
    await fs.writeFile(file, audio);
    const result = await stt.transcribe(file, 'pt'); validQuestion(result.text);
    return result.text.trim();
  } finally { await fs.rm(directory, { recursive: true, force: true }); }
});
handle('speech', async text => {
  if (typeof text !== 'string' || !text.trim() || text.length > 1400) throw new Error('Trecho de voz inválido.');
  const audio = await tts.synthesize(text);
  return audio ? new Uint8Array(audio) : null;
});
handle('chunks', speechChunks);
handle('cancel', () => { query?.abort(); });
handle('hide', () => { query?.abort(); window.hide(); });
handle('ready', () => {
  ready = true;
  for (const value of commands.splice(0)) command(value);
  console.log('CONTROL_READY');
  autonomy.load();
});

app.whenReady().then(async () => {
  window = new BrowserWindow({
    width: 820, height: 720, minWidth: 520, minHeight: 430,
    title: 'CH8 Control — Atalhos', show: false, backgroundColor: '#111827',
    webPreferences: { preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  window.setMenuBarVisibility(false);
  const area = screen.getPrimaryDisplay().workArea;
  autonomyOverlay = new BrowserWindow({
    width: 420, height: 180, x: area.x + area.width - 440, y: area.y + 24,
    show: false, frame: false, alwaysOnTop: true, skipTaskbar: true, focusable: false,
    backgroundColor: '#111827',
    webPreferences: { preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  autonomyOverlay.setIgnoreMouseEvents(true);
  autonomyOverlay.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  autonomyOverlay.webContents.on('will-navigate', event => event.preventDefault());
  await autonomyOverlay.loadFile(path.join(__dirname, 'autonomy-overlay.html'));
  window.webContents.on('preload-error', (_event, _file, error) => console.error('Preload:', error.message));
  const allowed = (contents, permission) => contents === window.webContents &&
    window.webContents.getURL() === page && permission === 'media';
  const session = window.webContents.session;
  session.setPermissionCheckHandler((contents, permission) => allowed(contents, permission));
  session.setPermissionRequestHandler((contents, permission, callback, details) =>
    callback(allowed(contents, permission) && details.mediaTypes?.every(type => type === 'audio')));
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', event => event.preventDefault());
  window.on('close', event => {
    if (!quitting) { event.preventDefault(); query?.abort(); window.webContents.send('command', 'cancel'); window.hide(); }
  });
  await window.loadURL(page);
  service.listen(Number(process.env.CH8_CONTROL_PORT || 0), '127.0.0.1');
}).catch(error => { console.error(error.message); app.quit(); });
app.on('before-quit', () => { quitting = true; query?.abort(); autonomy.stop(); service.close(); stt.stopWhisper(); });
module.exports = service;
