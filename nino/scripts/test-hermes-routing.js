'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('events');
const hermes = require('../src/main/hermes');

test('encaminha prefixo e pedidos de agentes sem capturar conversas comuns', () => {
  assert.equal(hermes.command('Hermes, verifique o disco C'), 'verifique o disco C');
  assert.equal(hermes.command('/hermes liste arquivos'), 'liste arquivos');
  assert.equal(hermes.command('Crie um agente para revisar arquivos'), 'Crie um agente para revisar arquivos');
  assert.equal(hermes.command('Agende uma rotina a cada 2 horas'), 'Agende uma rotina a cada 2 horas');
  assert.equal(hermes.command('O que e um agente?'), null);
  assert.equal(hermes.command('ponte consulte o Pi'), null);
});

function launchResult(result, code = 0) {
  return (executable, args, options) => {
    assert.ok(executable.endsWith('python.exe'));
    assert.equal(args[1], '--task');
    assert.equal(options.shell, undefined);
    const child = new EventEmitter();
    child.stdout = new EventEmitter();
    child.stdin = new EventEmitter();
    child.stdin.end = task => {
      assert.equal(task, 'teste');
      process.nextTick(() => {
        child.stdout.emit('data', Buffer.from(JSON.stringify(result)));
        child.emit('close', code);
      });
    };
    return child;
  };
}
test('espera resultado real e propaga falhas sem fingir sucesso', async () => {
  const result = await hermes.ask('teste', { launch: launchResult({ ok: true, text: 'feito' }) });
  assert.equal(result.text, 'feito');
  assert.equal(result.stats.provider, 'hermes-local');
  await assert.rejects(hermes.ask('teste', { launch: launchResult({ ok: false, text: 'falha real' }) }), /falha real/);
  await assert.rejects(hermes.ask(''), /caracteres/);
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(hermes.ask('teste', { signal: controller.signal }), /cancelada/);
});

test('sessao compartilhada de texto e voz devolve resposta do Hermes', async () => {
  const chat = require('../src/main/chat');
  const original = hermes.ask;
  hermes.ask = async task => ({ text: `resultado: ${task}`, stats: { provider: 'hermes-local' } });
  try {
    let spoken;
    const result = await chat.createChatSession().ask('Hermes, consulte o disco', { onToken: text => { spoken = text; } });
    assert.equal(result.ok, true);
    assert.equal(spoken, 'resultado: consulte o disco');
    assert.equal(result.stats.provider, 'hermes-local');
  } finally { hermes.ask = original; }
});
