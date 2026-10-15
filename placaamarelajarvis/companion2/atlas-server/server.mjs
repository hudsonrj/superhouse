import http from "node:http";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { existsSync, createReadStream, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import {
  emptyState,
  mergeState,
  localJourney,
  encodeForDevice,
  detectCrisisText,
} from "./engine.mjs";
import { sanitizeFleet } from "./fleet.mjs";

const host = process.env.ATLAS_HOST || "127.0.0.1";
const port = Number(process.env.ATLAS_PORT || 8787);
const apiKey = process.env.DEEPSEEK_API_KEY || "";
const apiUrl = "https://api.deepseek.com/chat/completions";
const model = process.env.DEEPSEEK_MODEL || "deepseek-v4-flash";
const fleetUrl = (process.env.ATLAS_FLEET_URL || "").replace(/\/$/, "");
const here = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(here, "public");
const dataDir = path.join(here, "data");
const stateFile = path.join(dataDir, "sistema.json");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".webmanifest": "application/manifest+json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

let memoryState = emptyState();

async function loadState() {
  try {
    const raw = await readFile(stateFile, "utf8");
    memoryState = mergeState(emptyState(), JSON.parse(raw));
  } catch {
    memoryState = emptyState();
  }
  return memoryState;
}

async function saveState(next) {
  memoryState = mergeState(memoryState, next);
  await mkdir(dataDir, { recursive: true });
  await writeFile(stateFile, JSON.stringify(memoryState, null, 2), "utf8");
  return memoryState;
}

const basePrompt = await readFile(path.join(here, "..", "prompts", "placa_amarela.system.md"), "utf8").catch(
  () => "Voce e o motor da Placa Amarela. Uma pergunta por vez. Nunca diagnostique nem altere medicamento.",
);

const atlasContract = `
Voce esta atendendo o dispositivo Atlas com tela 320x240. Responda APENAS JSON valido.
Cada clique deve aprofundar a jornada sem repetir perguntas. Use o historico recebido.
Gere no maximo tres opcoes curtas, distintas e acionaveis, com ate 20 caracteres cada.
O texto principal deve ter no maximo 150 caracteres e uma ideia por vez.

Formato obrigatorio:
{
  "tipo":"pergunta|insight|crise",
  "titulo":"ate 20 caracteres",
  "texto":"ate 150 caracteres",
  "opcoes":[{"rotulo":"ate 20 caracteres","valor":"identificador"}],
  "descoberta":"ate 120 caracteres ou vazio",
  "acao":"ate 120 caracteres ou vazio",
  "progresso":0
}

Se houver risco imediato, use tipo "crise", sem investigacao adicional, e direcione para apoio humano, CVV 188 e SAMU 192.
Nao diagnostique, nao altere medicacao e nao invente fatos. Uma pergunta por resposta.
`;

async function readJson(req, limit = 200_000) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > limit) throw new Error("payload_too_large");
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? JSON.parse(raw) : {};
}

async function cloudJourney(input) {
  if (!apiKey) throw new Error("no_key");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25_000);
  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: `${basePrompt}\n\n${atlasContract}` },
          { role: "user", content: `ENTRADA JSON:\n${JSON.stringify(input)}` },
        ],
        response_format: { type: "json_object" },
        thinking: { type: "disabled" },
        temperature: 0.35,
        max_tokens: 500,
      }),
      signal: controller.signal,
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body?.error?.message || `deepseek_${response.status}`);
    const content = body?.choices?.[0]?.message?.content;
    if (!content) throw new Error("deepseek_empty");
    return JSON.parse(content);
  } finally {
    clearTimeout(timeout);
  }
}

async function loadFleet() {
  if (!fleetUrl) return { available: false, reason: "not_configured", agents_list: [] };
  const response = await fetch(`${fleetUrl}/cyd/json`, { signal: AbortSignal.timeout(3000) });
  if (!response.ok) throw new Error(`fleet_${response.status}`);
  return sanitizeFleet(await response.json());
}

function send(res, status, body, type = "application/json; charset=utf-8") {
  res.writeHead(status, {
    "Content-Type": type,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
  });
  res.end(typeof body === "string" ? body : JSON.stringify(body));
}

function safePath(urlPath) {
  const clean = decodeURIComponent(urlPath.split("?")[0]);
  const relative = clean === "/" ? "/index.html" : clean;
  const resolved = path.normalize(path.join(publicDir, relative));
  if (!resolved.startsWith(publicDir)) return null;
  return resolved;
}

function serveFile(res, filePath) {
  const ext = path.extname(filePath);
  const type = MIME[ext] || "application/octet-stream";
  const stream = createReadStream(filePath);
  res.writeHead(200, {
    "Content-Type": type,
    "Cache-Control": ext === ".html" ? "no-store" : "public, max-age=3600",
  });
  stream.pipe(res);
}

await loadState();

const sessions = new Map();

function sessionOf(input) {
  const id = String(input.session_id || input.device || "atlas");
  if (!sessions.has(id) || input.reset) sessions.set(id, null);
  return { id, session: sessions.get(id) };
}

const server = http.createServer(async (req, res) => {
  const url = req.url || "/";
  const method = req.method || "GET";

  if (method === "OPTIONS") {
    send(res, 204, "");
    return;
  }

  try {
    if (method === "GET" && url === "/health") {
      send(res, 200, {
        ok: true,
        model: apiKey ? model : "local",
        cloud: Boolean(apiKey),
        name: "placa-amarela",
      });
      return;
    }

    if (method === "GET" && url.startsWith("/api/state")) {
      send(res, 200, memoryState);
      return;
    }

    if (method === "GET" && url === "/api/fleet") {
      try {
        send(res, 200, await loadFleet());
      } catch (error) {
        console.error(new Date().toISOString(), "fleet_unavailable", error.message);
        send(res, 503, { available: false, reason: "unavailable", agents_list: [] });
      }
      return;
    }

    if (method === "PUT" && url.startsWith("/api/state")) {
      const incoming = await readJson(req);
      const saved = await saveState(incoming);
      send(res, 200, saved);
      return;
    }

    if (method === "POST" && (url.startsWith("/api/journey") || url === "/journey")) {
      const input = await readJson(req);
      const { id, session } = sessionOf(input);
      const packed = { ...input, session };
      if (detectCrisisText(JSON.stringify(input))) packed.escolha = "nao";

      const wantCloud = Boolean(apiKey) && (url === "/journey" || memoryState.consents?.cloud);
      let output;
      let source = "local";
      if (wantCloud) {
        try {
          output = await cloudJourney({ ...packed, estado: memoryState });
          source = "deepseek";
        } catch (error) {
          console.error(new Date().toISOString(), "cloud_fallback", error.message);
          output = localJourney(packed, memoryState);
        }
      } else {
        output = localJourney(packed, memoryState);
      }
      if (output.session) sessions.set(id, output.session);

      if (url === "/journey") {
        send(res, 200, encodeForDevice(output), "text/plain; charset=utf-8");
        return;
      }
      send(res, 200, { ...output, source });
      return;
    }

    if (method === "GET" && url === "/engine.mjs") {
      serveFile(res, path.join(here, "engine.mjs"));
      return;
    }

    if (method === "GET") {
      let filePath = safePath(url);
      if (filePath && existsSync(filePath) && statSync(filePath).isDirectory()) {
        filePath = path.join(filePath, "index.html");
      }
      if (filePath && existsSync(filePath) && statSync(filePath).isFile()) {
        serveFile(res, filePath);
        return;
      }
      send(res, 404, "not_found", "text/plain; charset=utf-8");
      return;
    }

    send(res, 404, { error: "not_found" });
  } catch (error) {
    console.error(new Date().toISOString(), error.message);
    if (url === "/journey") {
      send(
        res,
        502,
        "ATLAS/1\nTYPE=error\nTITLE=SEM CONEXAO\nTEXT=Continue no modo local. A IA nao respondeu agora.\n",
        "text/plain; charset=utf-8",
      );
      return;
    }
    send(res, 500, { error: "server_error" });
  }
});

server.listen(port, host, () => {
  console.log(`Placa Amarela em http://localhost:${port}`);
  console.log(apiKey ? `IA opcional: ${model}` : "Motor local ativo (sem chave de IA).");
  console.log("Abra no telefone da mesma rede para instalar o app.");
});
