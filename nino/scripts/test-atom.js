'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs/promises');
const os = require('os');
const path = require('path');
const { once } = require('events');
const { createAtomServer, inputWav, outputPcm } = require('../src/server/atom');

function wav(rate = 16000, size = 16000) {
  const b = Buffer.alloc(44 + size);
  b.write('RIFF'); b.writeUInt32LE(b.length - 8, 4); b.write('WAVEfmt ', 8);
  b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22);
  b.writeUInt32LE(rate, 24); b.writeUInt32LE(rate * 2, 28);
  b.writeUInt16LE(2, 32); b.writeUInt16LE(16, 34); b.write('data', 36); b.writeUInt32LE(size, 40);
  return b;
}

test('valida audio de entrada e rejeita formatos incorretos e truncados', () => {
  inputWav(wav());
  inputWav(wav(16000, 960000));
  assert.throws(() => inputWav(wav(22050)));
  assert.throws(() => inputWav(wav(16000, 8000).subarray(0, -1)));
  assert.throws(() => inputWav(wav(16000, 960002)));
  assert.throws(() => inputWav(wav(16000, 7998)));
  const stereo = wav(); stereo.writeUInt16LE(2, 22);
  assert.throws(() => inputWav(stereo));
});

test('extrai PCM e taxa real do Piper sem assumir 16000 Hz', () => {
  const audio = wav(22050);
  assert.equal(outputPcm(audio).rate, 22050);
  assert.deepEqual(outputPcm(audio).pcm, audio.subarray(44));
  assert.throws(() => outputPcm(audio.subarray(0, -2)));
  const invalid = wav(); invalid.writeUInt16LE(32, 34);
  assert.throws(() => outputPcm(invalid));
  const padded = Buffer.concat([audio.subarray(0, 36), Buffer.from('JUNK\x02\0\0\0xx', 'binary'), audio.subarray(36)]);
  padded.writeUInt32LE(padded.length - 8, 4);
  assert.deepEqual(outputPcm(padded).pcm, audio.subarray(44));
  assert.throws(() => outputPcm(Buffer.concat([audio, Buffer.from('\n')])));
});

test('rota autenticada: audio -> texto -> conversa -> voz e arquivos locais', async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'nino-atom-'));
  const token = 'a'.repeat(48);
  let asked;
  let fail = false;
  let played = false;
  const session = {
    ask: async (text, handlers, opts) => { asked = { text, opts }; return { ok: true, text: 'Olá, estou aqui.' }; },
    abort() {},
  };
  const server = createAtomServer({ token, directory, output: 'pc', session,
    transcribe: async (file) => { assert.deepEqual(await fs.readFile(file), wav()); return { text: fail ? '' : 'Olá, Nino' }; },
    synthesize: async () => wav(22050), play: async (file) => { assert.deepEqual(await fs.readFile(file), wav(22050)); played = true; },
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const url = `http://127.0.0.1:${server.address().port}`;
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'audio/wav' };
  try {
    assert.equal((await fetch(`${url}/voice`, { method: 'POST', body: wav() })).status, 401);
    const bad = await fetch(`${url}/voice`, { method: 'POST', headers, body: wav(22050) });
    assert.equal(bad.status, 400);
    const response = await fetch(`${url}/voice`, { method: 'POST', headers, body: wav() });
    const messages = (await response.text()).trim().split('\n').map(JSON.parse);
    assert.equal(messages[0].type, 'processing');
    const done = messages.at(-1);
    assert.equal(done.type, 'done'); assert.equal(done.text, 'Olá, Nino'); assert.equal(done.audio, null);
    assert.equal(asked.text, 'Olá, Nino'); assert.equal(asked.opts.semBase, true); assert.ok(played);
    const files = await fs.readdir(directory);
    const json = files.find((file) => file.endsWith('.json'));
    const id = path.basename(json, '.json');
    assert.equal((await fetch(`${url}/reply/${id}`)).status, 401);
    const audio = await fetch(`${url}/reply/${id}`, { headers });
    assert.equal(audio.headers.get('X-Sample-Rate'), '22050');
    assert.deepEqual(Buffer.from(await audio.arrayBuffer()), wav(22050).subarray(44));
    assert.equal((await fetch(`${url}/../settings.json`, { headers })).status, 404);
    fail = true;
    const empty = await fetch(`${url}/voice`, { method: 'POST', headers, body: wav() });
    assert.equal((await empty.text()).trim().split('\n').map(JSON.parse).at(-1).type, 'error');
  } finally {
    await new Promise((resolve) => server.close(resolve));
    await fs.rm(directory, { recursive: true, force: true });
  }
});

test('agente envia texto autenticado para exibir e falar, sem chamar modelo', async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'nino-speak-'));
  const token = 'b'.repeat(48);
  let shown;
  let spoken;
  const server = createAtomServer({ token, directory,
    session: { ask() { throw new Error('Nao deve chamar o modelo.'); } },
    synthesize: async (text) => { spoken = text; return wav(22050); },
    notify: async (key, event) => { assert.equal(key, token); shown = event; },
    play: async (file) => assert.deepEqual(await fs.readFile(file), wav(22050)),
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const url = `http://127.0.0.1:${server.address().port}/speak`;
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  try {
    assert.equal((await fetch(url, { method: 'POST', body: '{}' })).status, 401);
    assert.equal((await fetch(url, { method: 'POST', headers, body: '{' })).status, 400);
    assert.equal((await fetch(url, { method: 'POST', headers, body: JSON.stringify({ text: 'x'.repeat(2001) }) })).status, 400);
    const res = await fetch(url, { method: 'POST', headers, body: JSON.stringify({ text: 'Mensagem da ponte.' }) });
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { ok: true, output: 'pc' });
    assert.deepEqual(shown, { type: 'answer', text: 'Mensagem da ponte.' });
    assert.equal(spoken, 'Mensagem da ponte.');
  } finally {
    await new Promise((resolve) => server.close(resolve));
    await fs.rm(directory, { recursive: true, force: true });
  }
});
