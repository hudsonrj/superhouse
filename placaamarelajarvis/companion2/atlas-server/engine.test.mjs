import { test } from "node:test";
import assert from "node:assert/strict";
import {
  emptyState,
  startSession,
  presentSession,
  answerSession,
  buildDiscovery,
  buildAction,
  detectCrisisText,
  localJourney,
  encodeForDevice,
  applyCheckin,
  checkinInsight,
  weekPattern,
  rolloverDay,
  recordDiscovery,
  mergeState,
  PATHS,
} from "./engine.mjs";

test("empty state has the life-system contract", () => {
  const s = emptyState();
  assert.equal(s.hoje.type, null);
  assert.ok(Array.isArray(s.placa.descobertas));
  assert.equal(s.consents.cloud, false);
  assert.equal(s.consents.learn, false);
  assert.equal(s.consents.alerts, false);
  assert.equal(s.consents.sync, false);
});

test("unsafe answer short-circuits to crisis", () => {
  let session = startSession("sentir");
  let result = answerSession(session, 1);
  assert.equal(result.tipo, "crise");
  assert.equal(result.seguranca, "crise");
  assert.match(result.texto, /CVV 188/);
  assert.match(result.texto, /192/);
});

test("safe journey reaches an insight with a small action", () => {
  let result = presentSession(startSession("organizar"));
  const clicks = [0, 1, 0, 0, 0, 0];
  for (const idx of clicks) {
    result = answerSession(result.session, idx);
  }
  assert.equal(result.tipo, "insight");
  assert.ok(result.descoberta.length > 10);
  assert.ok(result.acao.length > 10);
  assert.equal(result.ferramenta, "passo");
});

test("impulse path suggests delay when the act is hard to undo", () => {
  let result = presentSession(startSession("decisao"));
  result = answerSession(result.session, 0);
  result = answerSession(result.session, 2);
  result = answerSession(result.session, 1);
  result = answerSession(result.session, 1);
  result = answerSession(result.session, 0);
  result = answerSession(result.session, 0);
  assert.equal(result.tipo, "insight");
  assert.match(result.descoberta, /desfazer|dist[aâ]ncia/i);
  assert.equal(result.ferramenta, "adiar");
});

test("crisis text is detected without flagging ordinary sadness", () => {
  assert.equal(detectCrisisText("estou cansado e triste"), false);
  assert.equal(detectCrisisText("quero morrer"), true);
});

test("device protocol encodes atlas lines", () => {
  const body = encodeForDevice({
    tipo: "pergunta",
    titulo: "COMO ESTOU",
    texto: "Você está fisicamente seguro agora?",
    progresso: 12,
    descoberta: "",
    acao: "",
    opcoes: [
      { rotulo: "SIM", valor: "sim" },
      { rotulo: "NÃO", valor: "nao" },
    ],
  });
  assert.match(body, /^ATLAS\/1\n/);
  assert.match(body, /TYPE=pergunta/);
  assert.match(body, /OPT1=SIM/);
});

test("localJourney starts a path from device language", () => {
  const first = localJourney({ caminho: "REGULAR", escolha: "iniciar jornada" });
  assert.equal(first.tipo, "pergunta");
  assert.equal(first.eyebrow, "SEGURANÇA");
});

test("check-in insight lowers the bar on a crisis day", () => {
  let state = applyCheckin(emptyState(), { type: "crise", mood: 1, energy: 1, sleep: 1 });
  const insight = checkinInsight(state);
  assert.equal(insight.seguranca, "atencao");
  assert.match(insight.descoberta, /crise/i);
});

test("week pattern alerts after three crisis days", () => {
  const state = emptyState();
  state.hoje = { date: "2026-08-21", type: "crise", mood: 1, energy: 1, sleep: 1 };
  state.ultimos_dias = [
    { data: "2026-08-20", type: "crise", mood: 2, energy: 2, sleep: 2 },
    { data: "2026-08-19", type: "crise", mood: 1, energy: 1, sleep: 2 },
  ];
  const pattern = weekPattern(state);
  assert.equal(pattern.criseCount, 3);
  assert.ok(pattern.alert);
});

test("rollover archives yesterday and starts a blank today", () => {
  const state = emptyState();
  state.hoje = { date: "2020-01-01", type: "crise", mood: 2, energy: 2, sleep: 2, gratitude: "", kidExample: "" };
  const next = rolloverDay(state, new Date("2026-08-21T12:00:00"));
  assert.equal(next.hoje.date, "2026-08-21");
  assert.equal(next.hoje.type, null);
  assert.equal(next.ultimos_dias[0].data, "2020-01-01");
  assert.equal(next.restarts, 1);
});

test("discoveries never diagnose", () => {
  const session = startSession("sentir");
  session.answers = { safety: "sim", intensity: "2", capacity: "pensar", sinal: "ansiedade" };
  const text = buildDiscovery(session) + buildAction(session);
  assert.equal(/\b(TDAH|TOC|depress[aã]o|transtorno|diagn[oó]stico|laudo)\b/i.test(text), false);
});

test("merge keeps cloud consent off unless set", () => {
  const merged = mergeState(emptyState(), { config: { name: "Hudson" } });
  assert.equal(merged.config.name, "Hudson");
  assert.equal(merged.consents.cloud, false);
});

test("all six device paths exist", () => {
  assert.equal(PATHS.length, 6);
  assert.deepEqual(
    PATHS.map((p) => p.device),
    ["COMO ESTOU", "ENTENDER", "REGULAR", "ORGANIZAR", "DECISAO", "COMPANHIA"],
  );
});

test("recordDiscovery prepends and caps", () => {
  let state = emptyState();
  for (let i = 0; i < 5; i++) {
    state = recordDiscovery(state, { texto: `d${i}`, estacao: "sentir" });
  }
  assert.equal(state.placa.descobertas[0].texto, "d4");
  assert.equal(state.placa.descobertas.length, 5);
});
