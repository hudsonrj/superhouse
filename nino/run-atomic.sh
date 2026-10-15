#!/bin/bash
#
# Inicia Nino com Atomic Chat local
#
# Uso:
#   ./run-atomic.sh
#
# Abrirá servidor em http://127.0.0.1:3081

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export OLLAMA_HOST="http://127.0.0.1:1337/v1"
export OPENAI_COMPATIBLE="true"
export NODE_OPTIONS="--max-old-space-size=4096"

echo "🚀 Iniciando Nino com Atomic Chat..."
echo ""
echo "📡 Servidor:  http://127.0.0.1:3081"
echo "🌐 Navegador: Abra no Chrome/Edge"
echo "🪟 Modo:     Clique em 🪟 para janela flutuante"
echo ""
echo "⏹️  Pressione Ctrl+C para parar"
echo ""

# Verifica se Atomic Chat está rodando
echo "🔍 Verificando Atomic Chat em http://127.0.0.1:1337/v1/models..."
if curl -s http://127.0.0.1:1337/v1/models | grep -q "data"; then
  echo "✅ Atomic Chat encontrado!"
  echo ""
else
  echo "⚠️  Atomic Chat não respondeu."
  echo "   Certifique-se que está rodando em http://127.0.0.1:1337"
  echo ""
  read -p "Continuar mesmo assim? (s/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    exit 1
  fi
fi

# Inicia servidor
npm run web
