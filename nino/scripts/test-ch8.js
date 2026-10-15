'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const ch8 = require('../src/main/ch8');

test('encaminha somente pedidos explicitamente endereçados ao CH8', () => {
  assert.equal(ch8.command('CH8, consulte minhas tarefas'), 'consulte minhas tarefas');
  assert.equal(ch8.command('/ch8 consulte minhas tarefas'), 'consulte minhas tarefas');
  assert.equal(ch8.command('CH oito, consulte minhas tarefas'), 'consulte minhas tarefas');
  assert.equal(ch8.command('cê agá oito, consulte minhas tarefas'), 'consulte minhas tarefas');
  assert.equal(ch8.command('o que é CH8?'), null);
  assert.equal(ch8.command('ch80 teste'), null);
});

test('acompanha o pedido assíncrono pelo identificador devolvido', async () => {
  const connection = { url: 'http://127.0.0.1:8810', token: 'test', protocol: 'control' };
  let id;
  const result = await ch8.ask('oi', { connection, request: async (url, options) => {
    if (options.method === 'POST') {
      id = JSON.parse(options.body).requestId;
      return Response.json({ id, status: 'pending' }, { status: 202 });
    }
    assert.equal(url.pathname, `/jobs/${id}`);
    return Response.json({ id, status: 'done', response: 'Conectado.' });
  } });
  assert.equal(result.text, 'Conectado.');
});

test('usa contrato da ponte e não aceita página de login nem falha como resposta', async () => {
  const connection = { url: 'http://127.0.0.1:7879', token: 'test-token' };
  const result = await ch8.ask('consulta', { connection, request: async (url, options) => {
    assert.equal(url.pathname, '/chat');
    assert.equal(options.redirect, 'error');
    assert.equal(options.headers.Authorization, 'Bearer test-token');
    assert.deepEqual(JSON.parse(options.body), { messages: [{ role: 'user', content: 'consulta' }], stream: false });
    return Response.json({ response: 'Resposta da ponte', node: 'raspberrypi' });
  } });
  assert.equal(result.text, 'Resposta da ponte');
  await assert.rejects(ch8.ask('consulta', { connection, request: async () => new Response('<html>login</html>', { headers: { 'Content-Type': 'text/html' } }) }), /página/);
  await assert.rejects(ch8.ask('consulta', { connection, request: async () => new Response('', { status: 401 }) }), /401/);
  await assert.rejects(ch8.ask('consulta', { connection, request: async () => Response.json({ response: '' }) }), /não retornou/);
  await assert.rejects(ch8.ask('consulta', { connection, request: async () => Response.json({ response: '_(IA local sem resposta - usando Groq como alternativa temporaria)_\n\n' }) }), /modelo da ponte/);
});
