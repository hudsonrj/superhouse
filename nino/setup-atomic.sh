#!/usr/bin/env bash
#
# Setup otimizado do Nino para usar Atomic Chat local
# - Piper (voz neural PT-BR)
# - Whisper (transcrição)
# - Node.js dependencies (já instaladas)
#
# SEM Ollama (usa Atomic Chat em http://127.0.0.1:1337/v1)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }
success() { printf '\033[1;32m✓ %s\033[0m\n' "$1"; }

# ================================================================== #
step "1/3  Piper (voz neural PT-BR)"
# ================================================================== #

mkdir -p vendor/voices

if [ ! -x vendor/piper/piper ]; then
  echo "Baixando Piper..."

  # Detecta sistema operacional
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PIPER_URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz"
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    PIPER_URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_macos_x86_64.tar.gz"
  else
    echo "❌ Sistema operacional não suportado para Piper"
    exit 1
  fi

  tmp="$(mktemp -d)"
  curl -fsSL -o "$tmp/piper.tar.gz" "$PIPER_URL"
  tar xzf "$tmp/piper.tar.gz" -C vendor
  rm -rf "$tmp"
  success "Piper instalado"
else
  success "Piper já presente: $(vendor/piper/piper --version 2>/dev/null || echo '?')"
fi

# Vozes PT-BR
VOICES=("pt_BR-faber-medium" "pt_BR-edresson-low")
for voice in "${VOICES[@]}"; do
  if [ ! -f "vendor/voices/${voice}.onnx" ]; then
    echo "Baixando voz: $voice..."
    curl -fsSL -o "vendor/voices/${voice}.onnx" \
      "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/${voice}.onnx"
    curl -fsSL -o "vendor/voices/${voice}.onnx.json" \
      "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/${voice}.onnx.json"
  fi
done
success "Vozes PT-BR prontas"

# ================================================================== #
step "2/3  Whisper (transcrição de voz)"
# ================================================================== #

if [ ! -d "vendor/sttenv" ]; then
  echo "Criando ambiente Python..."
  python3 -m venv vendor/sttenv
  source vendor/sttenv/bin/activate

  echo "Instalando faster-whisper..."
  pip install -q --upgrade pip
  pip install -q faster-whisper
  deactivate
  success "Whisper pronto"
else
  success "Ambiente Whisper já existe"
fi

# ================================================================== #
step "3/3  Ícones (opcional)"
# ================================================================== #

if [ -f "scripts/make-icons.js" ]; then
  echo "Gerando ícones..."
  node scripts/make-icons.js 2>/dev/null || true
  success "Ícones prontos"
else
  echo "⚠️  Script de ícones não encontrado"
fi

# ================================================================== #
success "Setup completo! 🎉"
echo ""
echo "Próximos passos:"
echo "1. Certifique-se que Atomic Chat está rodando em http://127.0.0.1:1337/v1"
echo "2. No Atomic Chat, crie um projeto e adicione seus documentos (base de conhecimento)"
echo "3. Abra em navegador:"
echo ""
echo "   npm run web"
echo "   # ou"
echo "   ./run-atomic.bat  (Windows)"
echo "   ./run-atomic.sh   (Linux/Mac)"
echo ""
echo "4. Acesse http://127.0.0.1:3081 no Chrome/Edge"
echo "5. Clique em 🪟 para modo flutuante"
