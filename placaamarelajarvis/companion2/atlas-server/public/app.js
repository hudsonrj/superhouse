import {
  PATHS,
  TOOLS,
  emptyState,
  rolloverDay,
  homeCopy,
  weekPattern,
  startSession,
  presentSession,
  answerSession,
  checkinQuestions,
  applyCheckin,
  checkinInsight,
  recordDiscovery,
  recordTrigger,
  recordCycle,
  mergeState,
  detectCrisisText,
  todayISO,
} from "/engine.mjs";

const KEY = "sistema_de_vida_v1";
const root = document.getElementById("root");
const clock = document.getElementById("clock");

const ui = {
  data: load(),
  session: null,
  checkin: { step: 0, answers: {} },
  tool: null,
  delayUntil: 0,
  breathLabel: "INSPIRE",
  senseStep: 0,
  draft: {},
  notice: "",
  lastInsight: null,
  fleet: null,
  fleetLoading: false,
};

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return emptyState();
    return rolloverDay(mergeState(emptyState(), JSON.parse(raw)));
  } catch {
    return emptyState();
  }
}

function save(next = ui.data) {
  ui.data = rolloverDay({ ...next, updatedAt: Date.now() });
  localStorage.setItem(KEY, JSON.stringify(ui.data));
  syncUp();
  return ui.data;
}

async function syncDown() {
  if (!ui.data.consents?.sync) return;
  try {
    const res = await fetch("/api/state", { cache: "no-store" });
    if (!res.ok) return;
    const remote = await res.json();
    if (Number(remote.updatedAt || 0) > Number(ui.data.updatedAt || 0)) {
      save(mergeState(ui.data, remote));
      render();
    }
  } catch {
    /* offline is the default */
  }
}

let syncTimer = 0;
function syncUp() {
  if (!ui.data.consents?.sync) return;
  clearTimeout(syncTimer);
  syncTimer = setTimeout(async () => {
    try {
      await fetch("/api/state", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(ui.data),
      });
    } catch {
      /* keep local */
    }
  }, 400);
}

function route() {
  const hash = (location.hash || "#/").replace(/^#/, "") || "/";
  const parts = hash.split("/").filter(Boolean);
  return { path: parts[0] || "home", arg: parts[1] || "", rest: parts.slice(2) };
}

function go(to) {
  if (location.hash !== `#${to}`) location.hash = to;
  else render();
}

function tap() {
  if (navigator.vibrate) navigator.vibrate(12);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function plate(inner, extraClass = "") {
  return `
    <section class="plate ${extraClass}">
      <span class="rivet tl" aria-hidden="true"></span>
      <span class="rivet tr" aria-hidden="true"></span>
      <span class="rivet bl" aria-hidden="true"></span>
      <span class="rivet br" aria-hidden="true"></span>
      ${inner}
    </section>
  `;
}

function header(title = "PLACA AMARELA") {
  return `
    <div class="plate-head">
      <div class="brand">
        <span class="serial">MSV-01 · LOCAL</span>
        <h1 tabindex="-1">${escapeHtml(title)}</h1>
      </div>
      <button class="sos" type="button" data-go="/sos" aria-label="SOS, abrir apoio humano">SOS</button>
    </div>
  `;
}

function nav(active) {
  const items = [
    ["/", "Placa"],
    ["/hoje", "Hoje"],
    ["/mapa", "Mapa"],
    ["/perfil", "Perfil"],
  ];
  return `
    <nav class="nav-row" aria-label="Principal">
      ${items
        .map(
          ([href, label]) =>
            `<button type="button" data-go="${href}" ${active === href ? 'aria-current="page"' : ""}>${label}</button>`,
        )
        .join("")}
    </nav>
  `;
}

function weekStrip(state) {
  const labels = ["D", "S", "T", "Q", "Q", "S", "S"];
  const today = new Date();
  const stamps = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const iso = todayISO(d);
    const hit =
      (state.hoje?.date === iso && state.hoje) ||
      (state.ultimos_dias || []).find((x) => x.data === iso);
    const type = hit?.type || "empty";
    stamps.push(
      `<div class="day-stamp ${type}" aria-label="${iso}: ${type === "empty" ? "sem registro" : type}">${labels[d.getDay()]}</div>`,
    );
  }
  return `<div class="week" aria-label="Últimos sete dias">${stamps.join("")}</div>`;
}

function renderHome() {
  const copy = homeCopy(ui.data);
  const doneToday = Boolean(ui.data.hoje?.type);
  return (
    plate(
      `
      ${header()}
      <p class="eyebrow">${escapeHtml(copy.eyebrow)}</p>
      <p class="lead">${escapeHtml(copy.title)}</p>
      <p class="support">${escapeHtml(copy.body)}</p>
      ${copy.alert ? `<p class="alert-strip">${escapeHtml(copy.alert)}</p>` : ""}
      ${weekStrip(ui.data)}
      <div class="grid-2">
        <button class="stamp-btn wide" type="button" data-go="${doneToday ? "/caminho/regular" : "/hoje"}">
          <span class="k">${doneToday ? "PRECISO REGULAR" : "CHECK-IN DE HOJE"}</span>
          <span class="s">${doneToday ? "Uma ferramenta curta, agora" : "Nomear o dia em quatro toques"}</span>
        </button>
        ${PATHS.map(
          (p) => `
            <button class="stamp-btn" type="button" data-go="/caminho/${p.id}">
              <span class="k">${p.stamp}</span>
              <span class="s">${p.hint}</span>
            </button>
          `,
        ).join("")}
      </div>
    `,
      copy.mode === "crise" ? "crise" : "",
    ) +
    `
    <aside class="tray">
      <header>FERRAMENTAS</header>
      <div class="body">
        <div class="row-btns">
          ${TOOLS.map((t) => `<button class="ghost" type="button" data-go="/ferramenta/${t.id}">${t.label}</button>`).join("")}
          <button class="ghost" type="button" data-go="/frota">Ver frota de agentes</button>
        </div>
        <p class="note" style="margin-top:12px">A placa não diagnostica, não muda medicamento e não substitui CVV, SAMU, médico ou alguém de confiança.</p>
      </div>
    </aside>
    ${nav("/")}
  `
  );
}

function renderQuestion(block) {
  const options = (block.options || []).map(
    (opt, i) =>
      `<button class="choice ${i === 0 ? "primary" : ""}" type="button" data-answer="${i}">${escapeHtml(opt.rotulo)}</button>`,
  );
  return plate(`
    ${header(block.title || "PLACA")}
    <p class="eyebrow">${escapeHtml(block.eyebrow || "")}</p>
    <p class="lead">${escapeHtml(block.prompt)}</p>
    ${block.body ? `<p class="support">${escapeHtml(block.body)}</p>` : ""}
    <div class="progress" role="progressbar" aria-label="Progresso desta etapa" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(block.progress || 0)}"><span style="width:${block.progress || 0}%"></span></div>
    ${options.join("")}
    <div class="row-btns" style="margin-top:12px">
      <button class="ghost" type="button" data-go="/">Voltar</button>
      <button class="ghost" type="button" data-go="/ferramenta/silencio">Silêncio</button>
      <button class="ghost danger" type="button" data-go="/sos">SOS</button>
    </div>
  `);
}

function renderCheckin() {
  const r = route();
  if (r.arg === "feito" && (ui.lastInsight || ui.data.hoje?.type)) {
    const insight = ui.lastInsight || checkinInsight(ui.data);
    return plate(`
      ${header("HOJE")}
      <p class="eyebrow">DESCOBERTA</p>
      <div class="discovery"><small>O DIA FOI NOMEADO</small>${escapeHtml(insight.descoberta)}</div>
      <p class="lead">${escapeHtml(insight.acao)}</p>
      <button class="choice primary" type="button" data-go="/ferramenta/${insight.ferramenta}">Fazer agora</button>
      <button class="choice" type="button" data-go="/">Voltar à placa</button>
    `);
  }
  const steps = checkinQuestions(ui.data);
  if (ui.checkin.step >= steps.length) {
    const next = applyCheckin(ui.data, ui.checkin.answers);
    const insight = checkinInsight(next);
    ui.lastInsight = insight;
    save(
      recordDiscovery(next, {
        texto: insight.descoberta,
        estacao: "hoje",
        acao: insight.acao,
      }),
    );
    ui.checkin = { step: 0, answers: {} };
    queueMicrotask(() => go("/hoje/feito"));
    return plate(`
      ${header("HOJE")}
      <p class="eyebrow">DESCOBERTA</p>
      <div class="discovery"><small>O DIA FOI NOMEADO</small>${escapeHtml(insight.descoberta)}</div>
      <p class="lead">${escapeHtml(insight.acao)}</p>
    `);
  }
  const q = steps[ui.checkin.step];
  return renderQuestion({
    title: "HOJE",
    eyebrow: q.eyebrow,
    prompt: q.prompt,
    options: q.options,
    progress: ((ui.checkin.step + 1) / steps.length) * 100,
  });
}

function renderJourney() {
  const path = route().arg || "sentir";
  if (!ui.session || ui.session.path !== path) ui.session = startSession(path);
  const result = presentSession(ui.session, ui.data);
  if (result.tipo === "crise") {
    go("/sos");
    return renderSos();
  }
  if (result.tipo === "insight") {
    return plate(`
      ${header("PRÓXIMO PASSO")}
      <p class="eyebrow">DESCOBERTA</p>
      <div class="discovery"><small>${escapeHtml(result.eyebrow)}</small>${escapeHtml(result.descoberta)}</div>
      <p class="lead">${escapeHtml(result.acao)}</p>
      ${(result.opcoes || [])
        .map(
          (opt, i) =>
            `<button class="choice ${i === 0 ? "primary" : ""}" type="button" data-insight="${escapeHtml(opt.valor)}">${escapeHtml(opt.rotulo)}</button>`,
        )
        .join("")}
    `);
  }
  return renderQuestion({
    title: result.titulo,
    eyebrow: result.eyebrow,
    prompt: result.texto,
    options: result.opcoes,
    progress: result.progresso,
  });
}

function renderFleet() {
  if (!ui.fleet && !ui.fleetLoading) {
    ui.fleetLoading = true;
    fetch("/api/fleet", { cache: "no-store" })
      .then(async (response) => ({ ok: response.ok, data: await response.json() }))
      .then(({ ok, data }) => {
        ui.fleet = ok ? data : { ...data, available: false };
      })
      .catch(() => {
        ui.fleet = { available: false, reason: "unavailable", agents_list: [] };
      })
      .finally(() => {
        ui.fleetLoading = false;
        if (route().path === "frota") render();
      });
  }
  const fleet = ui.fleet;
  const agents = fleet?.agents_list || [];
  const teams = Object.groupBy ? Object.groupBy(agents, (agent) => agent.team) : agents.reduce((groups, agent) => {
    (groups[agent.team] ||= []).push(agent);
    return groups;
  }, {});
  return `
    ${plate(`
      ${header("FROTA")}
      <p class="eyebrow">CONTROL · FLUXO OPERACIONAL</p>
      <p class="lead">${fleet?.available ? `${fleet.working} trabalhando · ${fleet.tasks} tarefas` : ui.fleetLoading ? "Carregando a frota…" : "Frota não conectada"}</p>
      <p class="support">${fleet?.available ? escapeHtml(fleet.brief || fleet.health || "Estado recebido do CONTROL.") : "Configure ATLAS_FLEET_URL para visualizar os agentes reais, sem copiar o orquestrador para este app."}</p>
      <ol class="flow-list" aria-label="Fluxo da frota">
        <li>Entrada e alertas <strong>${fleet?.alerts ?? "—"}</strong></li>
        <li>Agentes em execução <strong>${fleet?.working ?? "—"}</strong></li>
        <li>Fila de entregas <strong>${fleet?.tasks ?? "—"}</strong></li>
      </ol>
    `)}
    ${Object.entries(teams).map(([team, members]) => `
      <aside class="tray">
        <header>${escapeHtml(team)} · ${members.filter((agent) => agent.st === "RUN").length} RUN</header>
        <div class="body agent-list">
          ${members.map((agent) => `
            <article class="agent-card">
              <strong>${escapeHtml(agent.short || agent.n)} · ${escapeHtml(agent.n)}</strong>
              <span class="agent-status ${agent.st.toLowerCase()}">${escapeHtml(agent.st)} · ${agent.nwork} itens</span>
              <span>${escapeHtml(agent.act || agent.head || agent.role)}</span>
              ${agent.act && agent.head ? `<small>${escapeHtml(agent.head)}</small>` : ""}
            </article>
          `).join("")}
        </div>
      </aside>
    `).join("")}
    ${nav("")}
  `;
}

const SENSES = [
  { n: "5", sense: "VEJA", prompt: "Cinco coisas que seus olhos encontram agora. Sem interpretar." },
  { n: "4", sense: "TOQUE", prompt: "Quatro contatos: pés no chão, tecido, temperatura, peso." },
  { n: "3", sense: "OUÇA", prompt: "Três sons. Longe, perto, dentro da sala." },
  { n: "2", sense: "CHEIRO", prompt: "Dois cheiros, mesmo fracos. Se não houver, nomeie o ar." },
  { n: "1", sense: "SABOR", prompt: "Um gosto: água, dente, nada. Isso já é corpo presente." },
];

function renderTool(id) {
  if (id === "respirar") {
    return plate(`
      ${header("RESPIRAR")}
      <p class="eyebrow">4 ENTRA · 6 SAI</p>
      <p class="lead">Não force o ritmo. Acompanhe o disco.</p>
      <div class="tool-stage"><div class="breath" id="breath">${ui.breathLabel}</div></div>
      <button class="choice" type="button" data-go="/">Encerrei</button>
    `);
  }
  if (id === "aterrar") {
    const s = SENSES[ui.senseStep] || SENSES[0];
    return plate(`
      ${header("ATERRAR")}
      <p class="eyebrow">${s.n} · ${s.sense}</p>
      <p class="lead sense">${escapeHtml(s.prompt)}</p>
      <button class="choice primary" type="button" data-sense="next">${ui.senseStep >= 4 ? "Encerrar" : "Próximo sentido"}</button>
      <button class="choice" type="button" data-go="/">Parar</button>
    `);
  }
  if (id === "adiar") {
    const left = Math.max(0, ui.delayUntil - Date.now());
    const m = String(Math.floor(left / 60000)).padStart(2, "0");
    const s = String(Math.floor((left % 60000) / 1000)).padStart(2, "0");
    return plate(`
      ${header("ADIAR")}
      <p class="eyebrow">DISTÂNCIA ANTES DA AÇÃO</p>
      <p class="lead">Você não precisa decidir agora. Só atravessar estes minutos.</p>
      <div class="tool-stage"><div class="timer" id="delay">${m}:${s}</div></div>
      <p class="support">Se a ação puder ser desfeita, ela pode esperar. Se não puder, fale com alguém seguro.</p>
      <button class="choice" type="button" data-go="/">Chega por agora</button>
    `);
  }
  if (id === "passo") {
    return plate(`
      ${header("UM PASSO")}
      <p class="eyebrow">CABE EM CINCO MINUTOS</p>
      <p class="lead">Uma tarefa. Sem lista. Sem o resto do dia.</p>
      <label class="field" style="margin:12px 8px">O passo
        <input id="one-step" maxlength="80" placeholder="Ex.: encher o copo d'água" />
      </label>
      <button class="choice primary" type="button" data-save-step="1">Guardar este passo</button>
      <button class="choice" type="button" data-go="/">Agora não</button>
    `);
  }
  if (id === "reuniao") {
    return plate(`
      ${header("REUNIÃO")}
      <p class="eyebrow">ESCUDO CURTO</p>
      <p class="lead">Você não precisa responder imediatamente.</p>
      <div class="discovery"><small>1</small>Anote. Decida depois.</div>
      <div class="discovery"><small>2</small>Continue cinco minutos — ou peça uma pausa.</div>
      <div class="discovery"><small>3</small>Se sobrecarregar, saia da fala. Presença já é trabalho.</div>
      <button class="choice" type="button" data-go="/">Voltar</button>
    `);
  }
  if (id === "silencio") {
    return `
      ${plate(`
        ${header("SILÊNCIO")}
        <p class="eyebrow">NENHUMA RESPOSTA É EXIGIDA</p>
        <p class="lead">Estou aqui.</p>
        <div class="tool-stage"><div class="breath" style="animation-duration:16s">·</div></div>
        <button class="choice" type="button" data-go="/">Toque quando quiser</button>
      `)}
    `;
  }
  if (id === "sos") return renderSos();
  go("/");
  return renderHome();
}

function renderSos() {
  const name = ui.data.config.trustedName;
  const phone = ui.data.config.trustedPhone;
  return plate(
    `
    ${header("APOIO HUMANO")}
    <p class="eyebrow">VOCÊ NÃO PRECISA PASSAR POR ISSO SOZINHO</p>
    <p class="lead">Risco imediato: SAMU 192. Apoio emocional: CVV 188, gratuito, 24 horas.</p>
    <a class="choice primary" href="tel:192">Ligar 192</a>
    <a class="choice" href="tel:188">Ligar 188 · CVV</a>
    ${phone ? `<a class="choice" href="tel:${escapeHtml(phone)}">Ligar para ${escapeHtml(name || "contato de confiança")}</a>` : `<button class="choice" type="button" data-go="/perfil">Cadastrar alguém de confiança</button>`}
    <button class="choice" type="button" data-go="/ferramenta/silencio">Ficar em silêncio</button>
    <button class="choice" type="button" data-go="/">Voltar à placa</button>
    <p class="support">A placa não confirma se você está seguro. Se houver dúvida, trate como risco e peça presença humana.</p>
  `,
    "crise",
  );
}

function renderMap() {
  const descobertas = ui.data.placa.descobertas || [];
  const gatilhos = ui.data.placa.gatilhos || [];
  const pattern = weekPattern(ui.data);
  return `
    ${plate(`
      ${header("MAPA")}
      <p class="eyebrow">${descobertas.length} DESCOBERTAS · ${gatilhos.length} GATILHOS</p>
      <p class="lead">${pattern.alert || "O mapa cresce no que você guarda, não no que você aguenta."}</p>
      ${weekStrip(ui.data)}
    `)}
    <aside class="tray">
      <header>ÚLTIMAS DESCOBERTAS</header>
      <div class="body">
        ${
          descobertas.length
            ? `<ul class="list">${descobertas
                .slice(0, 8)
                .map(
                  (d) =>
                    `<li><strong>${escapeHtml(d.texto)}</strong>${d.acao ? `<span>${escapeHtml(d.acao)}</span>` : ""}<time datetime="${escapeHtml(d.em)}">${escapeHtml((d.em || "").slice(0, 16).replace("T", " "))}</time></li>`,
                )
                .join("")}</ul>`
            : `<p class="note">Ainda estamos começando o mapa. Cada ciclo guarda uma peça.</p>`
        }
      </div>
    </aside>
    <aside class="tray" style="margin-top:14px">
      <header>GATILHOS CONHECIDOS</header>
      <div class="body">
        ${
          gatilhos.length
            ? `<ul class="list">${gatilhos
                .map(
                  (g) =>
                    `<li><strong>${escapeHtml(g.nome)}</strong>Dispara: ${escapeHtml(g.dispara || "—")}<br>Custo: ${escapeHtml(g.custo || "—")}<br>Resposta: ${escapeHtml(g.resposta || "—")}</li>`,
                )
                .join("")}</ul>`
            : `<p class="note">Nenhum gatilho salvo. Depois de um ciclo, você pode registrar o que dispara e a resposta planejada.</p>`
        }
        <form id="trigger-form" class="field" style="margin-top:16px">
          <label class="field">Nome <input name="nome" required maxlength="40" /></label>
          <label class="field">O que dispara <input name="dispara" maxlength="80" /></label>
          <label class="field">Custo <input name="custo" maxlength="80" /></label>
          <label class="field">Resposta planejada <input name="resposta" maxlength="80" /></label>
          <button class="choice primary" type="submit">Guardar gatilho</button>
        </form>
      </div>
    </aside>
    ${nav("/mapa")}
  `;
}

function renderProfile() {
  const c = ui.data.config;
  const kids = c.kids || [];
  return `
    ${plate(`
      ${header("PERFIL")}
      <p class="eyebrow">FICA NESTE APARELHO</p>
      <p class="lead">${c.name ? escapeHtml(c.name) : "Como você quer ser chamado?"}</p>
      <p class="support">O perfil calibra o tom. Não vira laudo. Medicamento aqui é contexto, nunca orientação de dose.</p>
    `)}
    <form id="profile-form" class="tray">
      <header>COMO ACOMPANHAR VOCÊ</header>
      <div class="body">
        <label class="field">Nome ou forma de tratamento <input name="name" value="${escapeHtml(c.name)}" maxlength="40" /></label>
        <label class="field">Início do expediente <input name="workStart" type="time" value="${escapeHtml(c.workStart)}" /></label>
        <label class="field">Fim do expediente <input name="workEnd" type="time" value="${escapeHtml(c.workEnd)}" /></label>
        <label class="field">Neurodivergências informadas <textarea name="neuro">${escapeHtml(c.neuro)}</textarea></label>
        <label class="field">Frase que acalma <input name="calmingPhrase" value="${escapeHtml(c.calmingPhrase)}" maxlength="80" /></label>
        <label class="field">Frases a evitar <input name="phrasesToAvoid" value="${escapeHtml(c.phrasesToAvoid)}" maxlength="80" /></label>
        <label class="field">O que costuma ajudar <textarea name="helps">${escapeHtml(c.helps)}</textarea></label>
        <label class="field">O que piora <textarea name="harms">${escapeHtml(c.harms)}</textarea></label>
        <label class="field">Pessoa de confiança <input name="trustedName" value="${escapeHtml(c.trustedName)}" maxlength="40" /></label>
        <label class="field">Telefone <input name="trustedPhone" value="${escapeHtml(c.trustedPhone)}" inputmode="tel" maxlength="20" /></label>
        <label class="field">Objetivos <textarea name="goals">${escapeHtml(c.goals)}</textarea></label>
        <label class="field">Limites que devem ser respeitados <textarea name="limits">${escapeHtml(c.limits)}</textarea></label>
        <p class="note">Filhos — presença, não desempenho.</p>
        <div id="kids">
          ${kids
            .map(
              (k, i) =>
                `<label class="field">Nome da criança ${i + 1} <input name="kid${i}" value="${escapeHtml(k.name || "")}" maxlength="30" /></label>`,
            )
            .join("")}
          <label class="field">Outra criança <input name="kidNew" maxlength="30" placeholder="Opcional" /></label>
        </div>
        <label class="field check">
          <input type="checkbox" name="learn" ${ui.data.consents.learn ? "checked" : ""} />
          <span>Registrar ciclos para adaptar o acompanhamento</span>
        </label>
        <label class="field check">
          <input type="checkbox" name="alerts" ${ui.data.consents.alerts ? "checked" : ""} />
          <span>Mostrar alertas de padrão nos últimos dias</span>
        </label>
        <label class="field check">
          <input type="checkbox" name="sync" ${ui.data.consents.sync ? "checked" : ""} />
          <span>Sincronizar este perfil com o servidor local</span>
        </label>
        <button class="choice primary" type="submit">Salvar perfil</button>
        <button class="choice danger" type="button" id="erase">Apagar todos os dados</button>
      </div>
    </form>
    ${nav("/perfil")}
  `;
}

function render() {
  ui.data = rolloverDay(ui.data);
  const r = route();
  let html = "";
  if (r.path === "hoje") html = renderCheckin();
  else if (r.path === "caminho") html = renderJourney();
  else if (r.path === "ferramenta") html = renderTool(r.arg);
  else if (r.path === "sos") html = renderSos();
  else if (r.path === "mapa") html = renderMap();
  else if (r.path === "perfil") html = renderProfile();
  else if (r.path === "frota") html = renderFleet();
  else html = renderHome();
  root.innerHTML = html;
  bind();
  tickClock();
  document.title = `${root.querySelector("h1")?.textContent || "Placa Amarela"} — Meu Sistema de Vida`;
  requestAnimationFrame(() => root.querySelector("h1")?.focus({ preventScroll: true }));
}

function bind() {
  root.querySelectorAll("[data-go]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      tap();
      const to = el.getAttribute("data-go");
      if (to.startsWith("/caminho/")) ui.session = startSession(to.split("/")[2]);
      if (to.startsWith("/ferramenta/adiar")) ui.delayUntil = Date.now() + 15 * 60 * 1000;
      if (to.startsWith("/ferramenta/aterrar")) ui.senseStep = 0;
      if (to === "/") ui.session = null;
      go(to);
    });
  });

  root.querySelectorAll("[data-answer]").forEach((el) => {
    el.addEventListener("click", () => {
      tap();
      const idx = Number(el.getAttribute("data-answer"));
      const r = route();
      if (r.path === "hoje") {
        const steps = checkinQuestions(ui.data);
        const q = steps[ui.checkin.step];
        const opt = q.options[idx];
        ui.checkin.answers[q.id] = opt.valor;
        if (q.id === "kid" && opt.valor === "sim") {
          const name = ui.data.config.kids?.[0]?.name || "";
          ui.checkin.answers.kidExample = `Momento com ${name}`;
        }
        if (detectCrisisText(JSON.stringify(ui.checkin.answers))) {
          go("/sos");
          return;
        }
        ui.checkin.step += 1;
        render();
        return;
      }
      if (r.path === "caminho" && ui.session) {
        const result = answerSession(ui.session, idx, ui.data);
        ui.session = result.session;
        if (result.tipo === "crise") {
          go("/sos");
          return;
        }
        render();
      }
    });
  });

  root.querySelectorAll("[data-insight]").forEach((el) => {
    el.addEventListener("click", () => {
      tap();
      const valor = el.getAttribute("data-insight");
      const result = presentSession(ui.session, ui.data);
      if (valor === "guardar" || valor.startsWith("tool:")) {
        save(recordCycle(ui.data, ui.session, result));
      }
      if (valor.startsWith("tool:")) {
        const tool = valor.slice(5);
        if (tool === "adiar") ui.delayUntil = Date.now() + 15 * 60 * 1000;
        if (tool === "sos") go("/sos");
        else go(`/ferramenta/${tool}`);
        return;
      }
      ui.session = null;
      go("/");
    });
  });

  root.querySelectorAll("[data-sense]").forEach((el) => {
    el.addEventListener("click", () => {
      tap();
      if (ui.senseStep >= 4) {
        save(
          recordDiscovery(ui.data, {
            texto: "Você atravessou os cinco sentidos sem precisar resolver o resto.",
            estacao: "regular",
            acao: "Corpo presente. Próximo passo só se couber.",
          }),
        );
        go("/");
        return;
      }
      ui.senseStep += 1;
      render();
    });
  });

  root.querySelectorAll("[data-save-step]").forEach((el) => {
    el.addEventListener("click", () => {
      const input = document.getElementById("one-step");
      const texto = (input?.value || "").trim();
      if (!texto) {
        input?.focus();
        return;
      }
      save(
        recordDiscovery(ui.data, {
          texto: `Próximo passo reduzido: ${texto}`,
          estacao: "organizar",
          acao: texto,
        }),
      );
      go("/");
    });
  });

  const triggerForm = document.getElementById("trigger-form");
  triggerForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(triggerForm);
    save(
      recordTrigger(ui.data, {
        nome: fd.get("nome"),
        dispara: fd.get("dispara"),
        custo: fd.get("custo"),
        resposta: fd.get("resposta"),
      }),
    );
    render();
  });

  const profileForm = document.getElementById("profile-form");
  profileForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(profileForm);
    const kids = [];
    for (const [key, value] of fd.entries()) {
      if (key.startsWith("kid") && String(value).trim()) kids.push({ name: String(value).trim(), age: "" });
    }
    const next = structuredClone(ui.data);
    next.config = {
      ...next.config,
      name: String(fd.get("name") || ""),
      workStart: String(fd.get("workStart") || "09:00"),
      workEnd: String(fd.get("workEnd") || "18:00"),
      neuro: String(fd.get("neuro") || ""),
      calmingPhrase: String(fd.get("calmingPhrase") || ""),
      phrasesToAvoid: String(fd.get("phrasesToAvoid") || ""),
      helps: String(fd.get("helps") || ""),
      harms: String(fd.get("harms") || ""),
      trustedName: String(fd.get("trustedName") || ""),
      trustedPhone: String(fd.get("trustedPhone") || ""),
      goals: String(fd.get("goals") || ""),
      limits: String(fd.get("limits") || ""),
      kids,
    };
    next.consents.learn = fd.get("learn") === "on";
    next.consents.alerts = fd.get("alerts") === "on";
    next.consents.sync = fd.get("sync") === "on";
    save(next);
    go("/");
  });

  document.getElementById("erase")?.addEventListener("click", () => {
    if (!confirm("Apagar perfil, mapa e ciclos deste aparelho?")) return;
    localStorage.removeItem(KEY);
    ui.data = emptyState();
    ui.session = null;
    save(ui.data);
    go("/");
  });
}

function tickClock() {
  const now = new Date();
  clock.textContent = now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const breath = document.getElementById("breath");
  if (breath) {
    const cycle = 10400;
    const t = Date.now() % cycle;
    breath.textContent = t < 4400 ? "INSPIRE" : t < 5000 ? "SEGURE" : "SOLTE";
  }
  const delay = document.getElementById("delay");
  if (delay) {
    const left = Math.max(0, ui.delayUntil - Date.now());
    const m = String(Math.floor(left / 60000)).padStart(2, "0");
    const s = String(Math.floor((left % 60000) / 1000)).padStart(2, "0");
    delay.textContent = `${m}:${s}`;
    if (left === 0) delay.dataset.done = "1";
  }
}

setInterval(tickClock, 250);
window.addEventListener("hashchange", render);

async function boot() {
  await syncDown();
  render();
  if ("serviceWorker" in navigator) {
    try {
      await navigator.serviceWorker.register("/sw.js");
    } catch {
      /* optional */
    }
  }
}

if (document.readyState === "loading") {
  window.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
