'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require.resolve('./ensure-atomic'), 'utf8');

async function check(loaded) {
  const calls = [];
  const fakeFs = {
    readFile: async name => name.endsWith('instance.lock') ? JSON.stringify({ control_port: 1234 }) : name.endsWith('control-token') ? 'private-token' : JSON.stringify({ provider: 'llamacpp-upstream', model: 'AtomicChat/Test' }),
  };
  let finish;
  const finished = new Promise(resolve => { finish = resolve; });
  const context = {
    __dirname, process: { argv: [] }, AbortSignal, encodeURIComponent,
    console: { log: () => finish(), error: text => finish(new Error(text)) },
    require: name => name === 'node:fs/promises' ? fakeFs : require(name),
    fetch: async (url, options) => {
      assert.equal(options.headers.Authorization, 'Bearer private-token');
      assert.equal(options.redirect, 'error');
      calls.push({ url, options });
      const response = url.endsWith('/sessions') ? { sessions: loaded ? [{ provider: 'llamacpp-upstream', model_id: 'AtomicChat/Test' }] : [] } : url.endsWith('/server') ? { running: loaded } : {};
      return { ok: true, json: async () => response };
    },
  };
  vm.runInNewContext(source, context);
  const error = await finished;
  if (error) throw error;
  const posts = calls.filter(c => c.options.method === 'POST');
  assert.equal(posts.length, loaded ? 0 : 2);
  if (!loaded) {
    assert.ok(posts[0].url.endsWith('/server/start'));
    assert.ok(posts[1].url.endsWith('/models/llamacpp-upstream/AtomicChat/Test/load'));
    assert.equal(JSON.parse(posts[0].options.body).host, '127.0.0.1');
  }
}
(async () => {
  await check(true);
  await check(false);
  console.log('Startup: preserva sessao ativa e retoma API/modelo ausentes.');
})().catch(err => { console.error(err); process.exitCode = 1; });
