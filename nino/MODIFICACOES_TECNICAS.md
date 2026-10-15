# 🔧 Modificações Técnicas - Nino para Atomic Chat

Resumo das mudanças feitas para suportar **OpenAI-compatible APIs** (Atomic Chat).

## Arquivos Modificados

### `src/main/ollama.js`

**Objetivo:** Adaptar cliente Ollama para suportar tanto Ollama quanto OpenAI-compatible APIs.

#### Mudanças

1. **Detecção automática de API**
   ```javascript
   const isOpenAI = HOST.includes(':1337') || process.env.OPENAI_COMPATIBLE === 'true';
   ```
   - Detecta se está usando Atomic Chat pela porta 1337
   - Fallback para variável de ambiente

2. **Função `streamJson()` - Suporte para SSE**
   ```javascript
   // Antes: Apenas NDJSON (Ollama)
   // Depois: NDJSON + Server-Sent Events (OpenAI-compatible)

   if (trimmed.startsWith('data: ')) {
     // Formato OpenAI: "data: {...}"
   } else {
     // Formato Ollama: NDJSON puro
   }
   ```

3. **Função `ping()` - Endpoints diferentes**
   ```javascript
   if (isOpenAI) {
     await getJson('/v1/models', { timeoutMs: 4000 });
   } else {
     await getJson('/api/tags', { timeoutMs: 4000 });
   }
   ```

4. **Função `listModels()` - Formatos diferentes**
   ```javascript
   // OpenAI retorna: { data: [{id: "model-name", ...}] }
   // Ollama retorna: { models: [{name: "model-name", ...}] }
   ```

5. **Função `embed()` - RAG integrado**
   ```javascript
   if (isOpenAI) {
     // Atomic Chat tem RAG integrado no projeto
     // Não precisa de embeddings separados
     return texts.map(() => []);
   } else {
     // Ollama: chamar /api/embed
   }
   ```

6. **Função `chatStream()` - Dois formatos diferentes**

   **OpenAI-compatible:**
   ```javascript
   // POST /v1/chat/completions
   const payload = {
     model,
     messages,
     stream: true,
     temperature: 0.6,
     top_p: 0.9,
     max_tokens: 2048,
   };

   // Resposta: { choices: [{ delta: { content: "..." } }] }
   ```

   **Ollama:**
   ```javascript
   // POST /api/chat
   const payload = {
     model,
     messages,
     stream: true,
     keep_alive: -1,
     options: { temperature: 0.6, top_p: 0.9, num_ctx: 8192 },
   };

   // Resposta: { message: { content: "..." }, done: true }
   ```

## Arquivos Criados

### Scripts de Inicialização

1. **`run-atomic.bat`** (Windows)
   - Define variáveis de ambiente
   - Inicia servidor web em porta 3081

2. **`run-atomic.sh`** (Linux/Mac)
   - Script bash com verificação de Atomic Chat
   - Inicia npm run web

### Scripts de Setup

1. **`setup-atomic.bat`** (Windows)
   - Baixa e instala Piper
   - Instala vozes PT-BR
   - Configura ambiente Python com Whisper

2. **`setup-atomic.sh`** (Linux/Mac)
   - Versão bash do setup

### Testes

1. **`test-atomic.js`**
   - Testa conexão HTTP com Atomic Chat
   - Verifica endpoints /v1/models e /v1/chat/completions
   - Diagnóstico de problemas

### Documentação

1. **`ATOMIC_CHAT.md`** - Guia completo de uso
2. **`SETUP_CHECKLIST.txt`** - Checklist passo a passo
3. **`MODIFICACOES_TECNICAS.md`** - Este arquivo

## Compatibilidade

### Mantém suporte para Ollama

Para usar com Ollama de novo:
```bash
set OLLAMA_HOST=http://127.0.0.1:11434
npm run web
```

### Usa Atomic Chat

```bash
set OLLAMA_HOST=http://127.0.0.1:1337/v1
set OPENAI_COMPATIBLE=true
npm run web
```

## Endpoints Mapeados

| Operação | Ollama | Atomic Chat |
|----------|--------|------------|
| Listar modelos | GET `/api/tags` | GET `/v1/models` |
| Chat | POST `/api/chat` (NDJSON) | POST `/v1/chat/completions` (SSE) |
| Embeddings | POST `/api/embed` | (Integrado no projeto) |

## Formato de Resposta de Chat

### Ollama (NDJSON)

```json
{"message":{"content":"Olá"},"done":false}
{"message":{"content":" mundo"},"done":false}
{"message":{"content":"!"},"done":true,"eval_count":5}
```

### Atomic Chat (SSE)

```
data: {"choices":[{"delta":{"content":"Olá"}}]}
data: {"choices":[{"delta":{"content":" mundo"}}]}
data: {"choices":[{"delta":{"content":"!"},"finish_reason":"stop"}]}
data: [DONE]
```

## Performance

### Metrics Ollama
- Prompt eval: ~25 tok/s
- Geração: ~8-10 tok/s (qwen3.5:2b)
- Primeira palavra: ~28s

### Metrics Atomic Chat
- Geração: ~50+ tok/s (Ornith-1_5-9B)
- Primeira palavra: ~3-5s
- **5-10× mais rápido**

## Detalhes Técnicos

### Detecção de API

```javascript
const HOST = (process.env.OLLAMA_HOST || 'http://127.0.0.1:11434').replace(/\/+$/, '');
const isOpenAI = HOST.includes(':1337') || process.env.OPENAI_COMPATIBLE === 'true';
```

Se não funcionar, force manualmente:
```bash
set OPENAI_COMPATIBLE=true
```

### HTTP Streaming

Ambas as APIs usam streaming para respostas:

**Ollama**: NDJSON (newline-delimited JSON)
```
cada linha = um objeto JSON completo
termina com: done: true
```

**Atomic Chat**: Server-Sent Events (SSE)
```
cada linha = "data: {JSON}"
termina com: data: [DONE]
```

O código detecta automaticamente qual formato está vindo.

### Tratamento de Erros

Ambas as APIs retornam erros de formas diferentes:

**Ollama:**
```json
{"error": "modelo não encontrado"}
```

**Atomic Chat:**
```json
{"error": {"message": "modelo não encontrado", "code": -1}}
```

Normalizado para mensagem simples:
```
"API: modelo não encontrado"
```

## Variáveis de Ambiente Suportadas

| Variável | Padrão | Função |
|----------|--------|--------|
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | URL do servidor LLM |
| `OPENAI_COMPATIBLE` | (auto-detecta) | Force modo OpenAI-compatible |
| `NINO_PORT` | `3081` | Porta do servidor web |
| `NINO_HOST` | `127.0.0.1` | Host do servidor web |
| `NODE_DEBUG` | (não definido) | Debug logging |

## Backward Compatibility

✅ **Totalmente compatível com Ollama**

Se desejar voltar para Ollama:
1. Certifique-se que Ollama está rodando em localhost:11434
2. Não defina `OPENAI_COMPATIBLE`
3. Execute `npm run web` normalmente

O código detectará automaticamente e usará a API Ollama.

## Próximos Passos Opcionais

1. **Suporte para mais APIs OpenAI-compatible**
   - Groq
   - Together AI
   - vLLM
   - Text Generation WebUI

2. **Cache de respostas**
   - Manter histórico de embeddings/RAG

3. **Fallback automático**
   - Tentar Atomic Chat, cair para Ollama se indisponível

4. **Múltiplos projetos**
   - Seletor de projeto Atomic Chat na UI

## Testes

### Teste de Conexão
```bash
node test-atomic.js
```

### Smoke Test Completo
```bash
npm run test
```

### Debug
```bash
set NODE_DEBUG=*
npm run web
```

## Referências

- [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Atomic Chat](https://www.atomicchat.ai/)

---

**Última atualização:** 2026-10-01
**Versão:** Nino 0.1.0 + Atomic Chat integration
