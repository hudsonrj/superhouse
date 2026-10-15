'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const ponte = require('../src/main/ponte');
const connection = { enabled: true, url: 'https://example.test/routines/webhook/123', authHeader: 'X-Sending-Key', authValue: 'test-key' };

test('encaminha perguntas explícitas para a ponte preservando o restante', () => {
  assert.equal(ponte.command('Ponte, verifique o Pi'), 'verifique o Pi');
  assert.equal(ponte.command('/ponte verifique o Pi'), 'verifique o Pi');
  assert.equal(ponte.command('o que é uma ponte?'), null);
  assert.equal(ponte.command('pontes do Brasil'), null);
});

test('envia apenas text com a autenticação configurada e confirma recebimento', async () => {
  const result = await ponte.ask('verifique o Pi', { connection, request: async (url, options) => {
    assert.equal(url.href, connection.url);
    assert.equal(options.method, 'POST');
    assert.equal(options.redirect, 'error');
    assert.equal(options.headers['X-Sending-Key'], 'test-key');
    assert.deepEqual(JSON.parse(options.body), { text: 'verifique o Pi' });
    return new Response('', { status: 202 });
  } });
  assert.equal(result.accepted, true);
  assert.match(result.text, /enviada/);
});

test('não relata envio em falhas e não expõe chave ou URL em erros', async () => {
  await assert.rejects(ponte.ask('oi', { connection, request: async () => new Response('', { status: 401 }) }), /401/);
  await assert.rejects(ponte.ask('oi', { connection, request: async () => { throw new Error(connection.url + connection.authValue); } }), (error) => !error.message.includes('test-key') && !error.message.includes('example.test'));
  assert.throws(() => ponte.validate({ ...connection, url: 'http://public.example.com/webhook' }), /HTTPS/);
  assert.throws(() => ponte.validate({ ...connection, authValue: 'secret\nkey' }), /inválido/);
});
