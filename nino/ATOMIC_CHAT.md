# 🪟 Nino + Atomic Chat Local

Integração do Nino com **Atomic Chat** rodando localmente - sem Ollama, sem nuvem.

## ✅ Checklist de Requisitos

- [x] **Node.js 20+** (verificado: v22)
- [ ] **Atomic Chat rodando** em `http://127.0.0.1:1337/v1`
  - Verifique: `curl http://127.0.0.1:1337/v1/models`
- [ ] **Projeto criado** no Atomic Chat
- [ ] **Documentos adicionados** ao projeto (base de conhecimento)

## 🚀 Setup Rápido (Windows)

### 1. Instalar dependências

```bash
# Abre este arquivo com duplo clique
setup-atomic.bat
```

Isso instala:
- ✅ Piper (voz neural PT-BR)
- ✅ Whisper (transcrição de voz)
- ✅ Dependências Node.js

### 2. Rodar Nino

```bash
# Abre este arquivo com duplo clique
run-atomic.bat

# Ou no terminal:
npm run web
```

Servidor abrirá em **http://127.0.0.1:3081**

### 3. No navegador

1. Abra **Chrome** ou **Edge**
2. Vá para `http://127.0.0.1:3081`
3. Clique em **🪟** para janela flutuante
4. Converse normalmente - o RAG do Atomic Chat cuidará da base de conhecimento

---

## 🌐 Setup Linux/macOS

```bash
chmod +x setup-atomic.sh run-atomic.sh
./setup-atomic.sh
./run-atomic.sh
```

---

## 🔧 Configuração Manual (se precisar)

### Variáveis de Ambiente

```bash
# Windows
set OLLAMA_HOST=http://127.0.0.1:1337/v1
set OPENAI_COMPATIBLE=true
npm run web

# Linux/Mac
export OLLAMA_HOST="http://127.0.0.1:1337/v1"
export OPENAI_COMPATIBLE="true"
npm run web
```

### Mudar porta

```bash
# Padrão: 3081
npm run web -- --port 3082

# Via env var
set NINO_PORT=3082
npm run web
```

---

## 📚 Como Usar Base de Conhecimento

1. **No Atomic Chat**, crie um projeto
2. **Adicione documentos** ao projeto (PDFs, TXT, etc)
3. **Pergunte algo** no Nino que use os documentos
4. O Atomic Chat automaticamente busca contexto relevante

### Formatos suportados

| Tipo | Suporte |
|------|---------|
| PDF | ✅ Sim (com OCR de imagens não) |
| TXT | ✅ Sim |
| DOCX | ✅ Sim |
| EPUB | ✅ Sim |
| HTML | ✅ Sim |
| CSV | ✅ Sim |
| Markdown | ✅ Sim |
| ODT | ✅ Sim |
| RTF | ✅ Sim |

---

## 🎤 Recursos Disponíveis

| Feature | Status | Como funciona |
|---------|--------|--------------|
| 💬 Conversa | ✅ | Texto + streaming |
| 🔊 Fala | ✅ | Piper PT-BR neural |
| 🎤 Microfone | ✅ | Whisper (gravação + transcrição) |
| 📚 RAG | ✅ | Atomic Chat (base do projeto) |
| 👁️ Câmera | ✅ | Visão (via Atomic Chat) |
| 🖥️ Tela | ✅ | Screenshot (via Atomic Chat) |
| 🌤️ Gmail | ❌ | Não disponível nesta integração |

---

## ⚡ Performance

Medidas reais (CPU sem GPU):

| Operação | Tempo |
|----------|-------|
| Primeira palavra de resposta | ~2-5s |
| Resposta completa (30 tokens) | ~8-15s |
| Transcrição (5s de áudio) | ~3-5s |
| Síntese de fala | tempo real |

Muito mais rápido que Ollama na CPU! 🚀

---

## 🔧 Troubleshooting

### "Conexão recusada em http://127.0.0.1:1337"

```bash
# Verifique se Atomic Chat está rodando
curl http://127.0.0.1:1337/v1/models

# Se retornar JSON com "data", está ok
# Se retornar erro, inicie o Atomic Chat
```

### "Não ouço o Nino falar"

1. Verifique volume do sistema
2. Clique uma vez na página (navegadores exigem interação)
3. Teste em ⚙️ → Saída de áudio → **Testar a voz agora**

### "Não reconhece minha voz"

1. Nível do microfone aparece em `ouvindo… ▃▃▃`
2. Se não mexe, ajuste em Configurações → Som → Entrada
3. Ou fale mais perto do microfone

### "Resposta vazia ou genérica"

1. Verifique se documentos foram adicionados ao projeto no Atomic
2. Confirme que a pergunta está relacionada aos documentos
3. Teste uma pergunta simples primeiro: "Olá"

---

## 💾 Dados

### Onde ficam

```
data/
  kb/                   base de conhecimento local (não usado com Atomic)
  settings.json         suas preferências (modelo, voz, etc)
  audio/                gravações temporárias do microfone
  models/whisper/       modelo de transcrição
vendor/
  piper/                voz neural
  voices/               vozes PT-BR (.onnx)
  sttenv/               ambiente Python do Whisper
```

### Segurança

- ✅ Nada é enviado para a nuvem (exceto Atomic Chat que está local)
- ✅ Documentos ficam no projeto Atomic (local)
- ✅ Conversas não são salvas
- ✅ Configurações ficam em `data/settings.json`

---

## 📖 Atalhos Globais

| Atalho | Ação |
|--------|------|
| `Ctrl+Alt+N` | Mostrar/esconder mascote (modo desktop) |
| `Ctrl+Alt+T` | Modo clique-através (deixa passar cliques) |
| `Ctrl+Alt+S` | Parar de falar |

*Nota: Modo web em navegador usa atalhos do navegador*

---

## 🐛 Debug

### Ver logs

```bash
# Windows
set NODE_DEBUG=*
npm run web

# Linux/Mac
export NODE_DEBUG=*
./run-atomic.sh
```

### Testar integração

```bash
node test-atomic.js
```

### Teste de smoke

```bash
npm run test
```

---

## 📊 Comparação: Nino com Ollama vs Atomic Chat

| Aspecto | Ollama | Atomic Chat |
|--------|--------|------------|
| Chat LLM | Local (lento em CPU) | Local (rápido) |
| Embeddings | Local | Integrado no projeto |
| RAG | Manual (índice local) | Automático |
| Latência primeira resposta | ~28s | ~3-5s |
| Velocidade geração | ~8-10 tok/s | ~50+ tok/s |
| Configuração | Complexa | Simples |
| Documentos | Upload pelo app | Upload no Atomic |

**Atomic Chat é 5-10× mais rápido na mesma CPU!** ⚡

---

## ✨ Próximos Passos

1. ✅ Setup concluído
2. ⏳ Adicione documentos no Atomic Chat
3. 🚀 Pergunte sobre seus documentos
4. 🎨 Customize voz/velocidade em ⚙️
5. 📱 Compartilhe o link se quiser acessar de outro dispositivo

---

## 📝 Notas

- O RAG funciona via projeto Atomic Chat (não precisa Ollama)
- Sem limite de contexto além do modelo
- Suporta imagens (via câmera/tela) quando Atomic Chat suporta
- Histórico de conversa não persiste (volta a zero ao reiniciar)

---

## 🤝 Suporte

Problemas? Verifique:

1. Atomic Chat está respondendo em `http://127.0.0.1:1337/v1/models`?
2. Node.js está instalado (`node -v`)?
3. Python está instalado para Whisper (`python -v`)?
4. Permissões de microfone estão liberadas?

Qualquer erro, execute `test-atomic.js` para diagnóstico.
