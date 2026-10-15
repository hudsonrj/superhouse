'use strict';

const http = require('http');
const fs = require('fs/promises');
const path = require('path');
const crypto = require('crypto');
const { spawn } = require('child_process');
const config = require('../main/config');
const stt = require('../main/stt');
const tts = require('../main/tts');
const { createChatSession } = require('../main/chat');
const { notifyPresence } = require('./presence');
const { createAbsenceMonitor } = require('./absence');

const MAX_AUDIO = 44 + 16000 * 2 * 30;

function inputWav(data) {
  if (data.length < 44 || data.length > MAX_AUDIO || data.toString('ascii', 0, 4) !== 'RIFF' ||
      data.toString('ascii', 8, 16) !== 'WAVEfmt ' || data.readUInt32LE(16) !== 16 ||
      data.readUInt16LE(20) !== 1 || data.readUInt16LE(22) !== 1 ||
      data.readUInt32LE(24) !== 16000 || data.readUInt32LE(28) !== 32000 ||
      data.readUInt16LE(32) !== 2 || data.readUInt16LE(34) !== 16 ||
      data.toString('ascii', 36, 40) !== 'data' || data.readUInt32LE(40) !== data.length - 44 ||
      data.readUInt32LE(4) !== data.length - 8 || (data.length - 44) % 2 || data.length < 8044) {
    throw new Error('Envie WAV PCM mono, 16 bits, 16000 Hz, entre 250 ms e 30 s.');
  }
}

function outputPcm(wav) {
  if (!Buffer.isBuffer(wav) || wav.length < 44 || wav.toString('ascii', 0, 4) !== 'RIFF' ||
      wav.toString('ascii', 8, 12) !== 'WAVE' || wav.readUInt32LE(4) + 8 !== wav.length) throw new Error('Piper retornou WAV invalido.');
  let rate;
  for (let offset = 12; offset + 8 <= wav.length;) {
    const name = wav.toString('ascii', offset, offset + 4);
    const size = wav.readUInt32LE(offset + 4);
    const start = offset + 8;
    if (size > wav.length - start) throw new Error('WAV truncado.');
    if (name === 'fmt ') {
      if (size < 16 || wav.readUInt16LE(start) !== 1 || wav.readUInt16LE(start + 2) !== 1 ||
          wav.readUInt16LE(start + 14) !== 16) throw new Error('Piper precisa gerar PCM mono de 16 bits.');
      rate = wav.readUInt32LE(start + 4);
      if (rate < 8000 || rate > 48000) throw new Error('Taxa de audio invalida.');
    }
    if (name === 'data') {
      if (!rate || !size || size % 2) throw new Error('PCM invalido.');
      return { rate, pcm: wav.subarray(start, start + size) };
    }
    offset = start + size + (size % 2);
  }
  throw new Error('WAV sem audio.');
}

function playOnPc(file) {
  if (process.platform !== 'win32') throw new Error('Saida pc deste servico requer Windows.');
  return new Promise((resolve, reject) => {
    const child = spawn('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command',
      '(New-Object System.Media.SoundPlayer $env:NINO_REPLY_WAV).PlaySync()'], {
      windowsHide: true, env: { ...process.env, NINO_REPLY_WAV: file }, stdio: 'ignore',
    });
    child.on('error', reject);
    child.on('exit', (code) => code === 0 ? resolve() : reject(new Error('Falha ao tocar no computador.')));
  });
}

function createAtomServer({ token, output = 'atom', directory = path.join(config.DATA_DIR, 'atom'),
  transcribe = stt.transcribe, session = createChatSession(), synthesize = tts.synthesize,
  play = playOnPc, notify = notifyPresence, absence = createAbsenceMonitor() } = {}) {
  if (typeof token !== 'string' || token.length < 32) throw new Error('Configure uma chave de pelo menos 32 caracteres.');
  if (!['atom', 'pc'].includes(output)) throw new Error('Saida deve ser atom ou pc.');
  let busy = false;
  let reply = null;
  const expected = Buffer.from(`Bearer ${token}`);
  const server = http.createServer(async (req, res) => {
    const auth = Buffer.from(req.headers.authorization || '');
    if (auth.length !== expected.length || !crypto.timingSafeEqual(auth, expected)) {
      res.writeHead(401).end('Chave invalida.');
      req.resume();
      return;
    }
    if (req.method === 'POST' && req.url === '/presence') {
      req.resume();
      absence.touch();
      try { await notifyPresence(token); res.writeHead(204).end(); }
      catch { res.writeHead(503).end('Abra o Nino no computador.'); }
      return;
    }
    if (req.url === '/sensor-status' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify(absence.snapshot())); return;
    }
    if (req.url === '/sensor-status' && req.method === 'POST') {
      try {
        const chunks = []; let size = 0;
        for await (const chunk of req) {
          size += chunk.length;
          if (size > 1024) throw new Error('Evento grande demais.');
          chunks.push(chunk);
        }
        const event = JSON.parse(Buffer.concat(chunks).toString('utf8'));
        absence.heartbeat(event.motion);
        res.writeHead(204).end();
      } catch { res.writeHead(400).end('Evento de sensor invalido.'); }
      return;
    }
    if (req.method === 'POST' && req.url === '/speak') {
      const json = (status, value) => {
        res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
        res.end(JSON.stringify(value));
      };
      if (busy) { req.resume(); json(409, { error: 'Uma conversa ja esta em andamento.' }); return; }
      if (req.headers['content-type']?.split(';')[0].trim() !== 'application/json' ||
          !/^\d+$/.test(req.headers['content-length'] || '') || Number(req.headers['content-length']) > 16384) {
        req.resume(); json(400, { error: 'Envie application/json, ate 16 KB.' }); return;
      }
      busy = true;
      let text;
      try {
        const chunks = [];
        let bytes = 0;
        for await (const chunk of req) {
          bytes += chunk.length;
          if (bytes > 16384) throw new Error('Mensagem grande demais.');
          chunks.push(chunk);
        }
        const data = JSON.parse(Buffer.concat(chunks).toString('utf8'));
        if (!data || typeof data.text !== 'string' || !data.text.trim() || data.text.length > 2000) {
          throw new Error('Envie text com 1 a 2000 caracteres.');
        }
        text = data.text.trim();
      } catch (err) {
        busy = false; json(400, { error: err.message }); return;
      }
      try {
        await fs.mkdir(directory, { recursive: true });
        const file = path.join(directory, `${crypto.randomUUID()}-agent.wav`);
        await fs.writeFile(file, await synthesize(text));
        await notify(token, { type: 'answer', text });
        await play(file);
        console.log('[Nino] Mensagem do agente exibida e falada.');
        json(200, { ok: true, output: 'pc' });
      } catch (err) { json(503, { error: err.message }); }
      finally { busy = false; }
      return;
    }
    if (req.method === 'GET' && reply && req.url === `/reply/${reply.id}`) {
      console.log('[Atom] Audio solicitado:', reply.id, reply.pcm.length, 'bytes');
      res.writeHead(200, { 'Content-Type': 'application/octet-stream', 'Content-Length': reply.pcm.length,
        'X-Sample-Rate': reply.rate, 'Cache-Control': 'no-store' });
      res.end(reply.pcm);
      return;
    }
    if (req.method !== 'POST' || req.url !== '/voice') {
      res.writeHead(404).end();
      req.resume();
      return;
    }
    if (busy) {
      res.writeHead(409).end('Uma conversa ja esta em andamento.');
      req.resume();
      return;
    }
    if (req.headers['content-type'] !== 'audio/wav' ||
        !/^\d+$/.test(req.headers['content-length'] || '') || Number(req.headers['content-length']) > MAX_AUDIO) {
      res.writeHead(400).end('Envie audio/wav com Content-Length, ate 30 segundos.');
      req.resume();
      return;
    }
    busy = true;
    res.on('close', () => { if (!res.writableFinished) session.abort(); });
    let heartbeat;
    const send = (data) => { if (!res.destroyed) res.write(`${JSON.stringify(data)}\n`); };
    try {
      const chunks = [];
      let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > MAX_AUDIO) throw new Error('Audio grande demais.');
        chunks.push(chunk);
      }
      const audio = Buffer.concat(chunks);
      inputWav(audio);
      absence.touch();
      res.writeHead(200, { 'Content-Type': 'application/x-ndjson', 'Cache-Control': 'no-store', 'Connection': 'close' });
      send({ type: 'processing' });
      // Mantem o Atom conectado enquanto Whisper e o modelo trabalham na CPU.
      heartbeat = setInterval(() => send({ type: 'processing' }), 10000);
      await fs.mkdir(directory, { recursive: true });
      const id = crypto.randomUUID();
      const input = path.join(directory, `${id}-input.wav`);
      await fs.writeFile(input, audio);
      const started = Date.now();
      const result = await transcribe(input, 'pt');
      const transcribed = Date.now();
      console.log('[Atom] Transcricao:', transcribed - started, 'ms');
      const text = String(result.text || '').trim();
      if (!text) throw new Error('Nao reconheci fala. Tente novamente.');
      if (res.destroyed) throw new Error('Atom desconectou durante a transcricao.');
      console.log('[Atom] Voce:', text);
      await notifyPresence(token, { type: 'transcript', text }).catch(() => {});
      const answer = await session.ask(text, {}, { semBase: true, numPredict: 128,
        systemPrompt: 'Voce e Nino, assistente pessoal. Responda em portugues, de forma breve e clara, em ate tres frases.' });
      if (!answer.ok) throw new Error(answer.error || 'Conversa cancelada.');
      const answered = Date.now();
      console.log('[Atom] Modelo:', answered - transcribed, 'ms');
      await fs.writeFile(path.join(directory, `${id}.json`), JSON.stringify({ text, answer: answer.text }, null, 2));
      console.log('[Atom] Nino:', answer.text);
      await notifyPresence(token, { type: 'answer', text: answer.text }).catch(() => {});
      const wav = await synthesize(answer.text);
      console.log('[Atom] Sintese:', Date.now() - answered, 'ms');
      const decoded = outputPcm(wav);
      const replyFile = path.join(directory, `${id}-reply.wav`);
      await fs.writeFile(replyFile, wav);
      reply = { id, ...decoded };
      if (output === 'pc') await play(replyFile);
      send({ type: 'done', text, answer: answer.text, audio: output === 'atom' ? `/reply/${id}` : null });
    } catch (err) {
      console.error('[Atom]', err.message);
      await notifyPresence(token, { type: 'error', text: err.message }).catch(() => {});
      if (!res.headersSent) res.writeHead(400, { 'Content-Type': 'application/x-ndjson' });
      send({ type: 'error', error: err.message });
    } finally {
      clearInterval(heartbeat);
      busy = false;
      res.end();
    }
  });
  server.requestTimeout = 60000;
  const timer = setInterval(() => absence.tick(), 10000);
  timer.unref();
  server.on('close', () => clearInterval(timer));
  return server;
}

if (require.main === module) {
  const settings = require(path.join(config.DATA_DIR, 'atom-config.json'));
  const server = createAtomServer({ token: settings.token, output: process.env.NINO_ATOM_OUTPUT || settings.output || 'atom' });
  server.listen(3082, settings.host, () => console.log(`Atom Voice: http://${settings.host}:3082 (Atomic Chat local)`));
  const stop = () => { stt.stopWhisper(); server.close(); };
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
}

module.exports = { createAtomServer, inputWav, outputPcm };
