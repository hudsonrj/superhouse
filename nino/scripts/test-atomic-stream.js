'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const http = require('http');
const { once } = require('events');
test('SSE termina em DONE mesmo se a API mantiver a conexao aberta', async () => {
  const server = http.createServer((req, res) => {
    req.resume();
    if (req.url === '/v1/models') { res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify({data:[{id:'test-model'}]})); return; }
    res.setHeader('Content-Type', 'text/event-stream');
    res.write('data: '+JSON.stringify({choices:[{delta:{content:'Olá.'}}]})+'\n\n');
    res.write('data:[DONE]\n\n');
    // Nao encerra o socket: DONE precisa concluir o pedido.
  });
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  process.env.OLLAMA_HOST = `http://127.0.0.1:${server.address().port}/v1`;
  process.env.OPENAI_COMPATIBLE = 'true';
  const client = require('../src/main/ollama');
  let timer;
  try {
    const result = await Promise.race([client.chatStream({model:'test-model',messages:[]}), new Promise((_, reject) => { timer=setTimeout(()=>reject(new Error('Stream nao terminou')), 3000); })]);
    assert.equal(result.text, 'Olá.');
  } finally { clearTimeout(timer); server.closeAllConnections(); await new Promise(r => server.close(r)); }
});
