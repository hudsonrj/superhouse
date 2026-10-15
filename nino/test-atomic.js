#!/usr/bin/env node
'use strict';

/**
 * Teste rápido da conexão com Atomic Chat
 */

const http = require('http');

const ATOMIC_URL = 'http://127.0.0.1:1337/v1';

function testConnection() {
  return new Promise((resolve, reject) => {
    const req = http.get(ATOMIC_URL + '/models', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve(json);
        } catch (err) {
          reject(new Error('Resposta inválida: ' + data.slice(0, 200)));
        }
      });
    });

    req.on('error', reject);
    req.setTimeout(5000);
  });
}

async function main() {
  console.log('🔍 Testando conexão com Atomic Chat em', ATOMIC_URL);

  try {
    const models = await testConnection();
    console.log('✅ Conexão bem-sucedida!');
    console.log('\n📦 Modelos disponíveis:');
    if (models.data && models.data.length > 0) {
      models.data.forEach(m => {
        console.log(`  • ${m.id}`);
      });
    } else {
      console.log('  (Nenhum modelo listado)');
    }

    // Testa request de chat
    console.log('\n🗣️ Testando chat com Atomic...');
    const chatReq = http.request(ATOMIC_URL + '/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }, (res) => {
      let isOk = res.statusCode === 200;
      console.log(`  Status: ${res.statusCode}`);
      if (isOk) {
        console.log('✅ Chat endpoint respondendo (pronto para usar!)');
      } else {
        console.log('⚠️  Endpoint respondendo, mas com status ' + res.statusCode);
      }
      res.on('data', () => {}); // drain
    });

    chatReq.write(JSON.stringify({
      model: models.data?.[0]?.id || 'default',
      messages: [{ role: 'user', content: 'test' }],
      stream: true,
    }));
    chatReq.end();
    chatReq.on('error', () => {
      console.log('⚠️  Chat endpoint não respondeu (pode não estar pronto)');
    });

  } catch (err) {
    console.error('❌ Erro:', err.message);
    console.error('\nVerifique:');
    console.error('1. Atomic Chat está rodando em http://127.0.0.1:1337?');
    console.error('2. Comando na prompt: curl http://127.0.0.1:1337/v1/models');
    process.exit(1);
  }
}

main();
