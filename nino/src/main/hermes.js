'use strict';
const path = require('path');
const { spawn } = require('child_process');

function command(text) {
  const match = String(text).match(/^\s*(?:\/hermes\b|hermes\b)[\s,:-]*(.+)$/is);
  if (match) return match[1].trim();
  // shortcut: reconhece pedidos diretos de agentes/rotinas; outras acoes precisam do prefixo Hermes.
  return /^\s*(?:crie|criar|agende|agendar|programe|programar|execute|executar)\b.*\b(?:agente|agentes|rotina|rotinas)\b/is.test(text) ? String(text).trim() : null;
}

function ask(task, { signal, launch = spawn } = {}) {
  if (typeof task !== 'string' || !task.trim() || task.length > 8000) return Promise.reject(new Error('Tarefa deve ter 1 a 8000 caracteres.'));
  if (signal?.aborted) return Promise.reject(new Error('Tarefa cancelada.'));
  const python = path.join(process.env.LOCALAPPDATA, 'hermes', 'hermes-agent', 'venv', 'Scripts', 'python.exe');
  const script = path.resolve(__dirname, '../../scripts/hermes_mcp.py');
  return new Promise((resolve, reject) => {
    const child = launch(python, [script, '--task'], { cwd: path.resolve(__dirname, '../..'), windowsHide: true, stdio: ['pipe', 'pipe', 'ignore'], env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
    let output = '';
    // O executor Python encerra a arvore apos 240s. Nao mate apenas seu pai durante uma acao.
    child.stdout.on('data', data => { output += data.toString('utf8'); });
    child.on('error', reject);
    child.stdin.on('error', reject);
    child.on('close', code => {
      if (signal?.aborted) return reject(new Error('Espera cancelada; confira o historico do Hermes antes de repetir a tarefa.'));
      try {
        const result = JSON.parse(output);
        if (code !== 0 || !result.ok) throw new Error(result.text || 'Hermes falhou. Confira o historico antes de repetir.');
        resolve({ ...result, stats: { provider: 'hermes-local' } });
      } catch (error) { reject(error instanceof SyntaxError ? new Error('Hermes nao devolveu resultado valido.') : error); }
    });
    child.stdin.end(task.trim());
  });
}
module.exports = { command, ask };
