'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const nino = 'C:/repositorio/nino/src/main/';
const ch8 = require(nino + 'ch8');
const tts = require(nino + 'tts');
const stt = require(nino + 'stt');
const { speechChunks } = require('./helpers');
(async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'ch8-live-test-'));
  try {
    const prompt = 'Somente um teste de conexão. Responda apenas: Control conectado. Não execute ações.';
    const wav = await tts.synthesize(prompt);
    assert.equal(wav.subarray(0, 4).toString(), 'RIFF');
    console.log('Piper: áudio neural gerado.');
    const file = path.join(directory, 'question.wav');
    await fs.writeFile(file, wav);
    const transcript = await stt.transcribe(file, 'pt');
    assert(transcript.text.trim());
    console.log('Whisper: transcrição recebida.');
    const response = await ch8.ask(transcript.text);
    assert(response.text.trim());
    console.log('Control: resposta em texto recebida.');
    const answer = await tts.synthesize(speechChunks(response.text)[0]);
    assert.equal(answer.subarray(0, 4).toString(), 'RIFF');
    console.log('LIVE_OK: voz → transcrição → Control → texto → áudio neural.');
  } finally { stt.stopWhisper(); await fs.rm(directory, { recursive: true, force: true }); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
