'use strict';
const http = require('http');
const crypto = require('crypto');

function createPresenceServer({ token, onVoice = () => {} }) {
  const expected = Buffer.from(`Bearer ${token}`);
  return http.createServer(async (req, res) => {
    const auth = Buffer.from(req.headers.authorization || '');
    if (auth.length !== expected.length || !crypto.timingSafeEqual(auth, expected)) {
      req.resume();
      res.writeHead(401).end(); return;
    }
    if (req.method === 'POST' && req.url === '/voice-event') {
      try {
        const chunks = [];
        let size = 0;
        for await (const chunk of req) {
          size += chunk.length;
          if (size > 16384) throw new Error('Evento grande demais.');
          chunks.push(chunk);
        }
        const event = JSON.parse(Buffer.concat(chunks).toString('utf8'));
        if (!['transcript', 'answer', 'error'].includes(event.type) || typeof event.text !== 'string') throw new Error('Evento invalido.');
        onVoice(event);
        res.writeHead(204).end();
      } catch { res.writeHead(400).end(); }
      return;
    }
    req.resume();
    if (req.method !== 'POST' || req.url !== '/presence') { res.writeHead(404).end(); return; }
    // Presenca suspensa: confirma ao Atom sem abrir a interface do Nino.
    res.writeHead(204).end();
  });
}

function notifyPresence(token, event) {
  const body = event ? Buffer.from(JSON.stringify(event)) : Buffer.alloc(0);
  return new Promise((resolve, reject) => {
    const req = http.request({ hostname: '127.0.0.1', port: 3083, path: event ? '/voice-event' : '/presence', method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', 'Content-Length': body.length }, timeout: 2000 }, (res) => {
      res.resume();
      res.on('end', () => res.statusCode === 204 ? resolve() : reject(new Error('Nino nao recebeu presenca.')));
    });
    req.on('timeout', () => req.destroy(new Error('Nino nao respondeu.')));
    req.on('error', reject);
    req.end(body);
  });
}
module.exports = { createPresenceServer, notifyPresence };
