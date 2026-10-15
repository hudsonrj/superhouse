'use strict';
const { spawn } = require('node:child_process');
const path = require('node:path');
const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;
const child = spawn('C:/repositorio/nino/node_modules/electron/dist/electron.exe',
  [path.join(__dirname, 'test-ui.js')], { env, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
child.stdout.pipe(process.stdout); child.stderr.pipe(process.stderr);
const timer = setTimeout(() => { console.error('Tempo esgotado no teste da interface.'); child.kill(); process.exitCode = 1; }, 180000);
child.on('error', error => { clearTimeout(timer); console.error(error.message); process.exitCode = 1; });
child.on('exit', code => { clearTimeout(timer); process.exitCode = code === 0 ? (process.exitCode || 0) : 1; });
