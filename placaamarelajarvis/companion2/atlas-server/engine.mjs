/**
 * Motor local da Placa Amarela / Meu Sistema de Vida.
 * Uma pergunta por vez. Nunca diagnostica. Nunca altera medicamento.
 * Funciona sem internet; a IA externa, se existir, é um luxo.
 */

export const PATHS = [
  {
    id: "sentir",
    stamp: "COMO ESTOU",
    label: "Como estou",
    hint: "Nomear o sinal",
    device: "COMO ESTOU",
  },
  {
    id: "entender",
    stamp: "ENTENDER",
    label: "Entender",
    hint: "O que veio antes",
    device: "ENTENDER",
  },
  {
    id: "regular",
    stamp: "REGULAR",
    label: "Regular",
    hint: "Aqui e agora",
    device: "REGULAR",
  },
  {
    id: "organizar",
    stamp: "ORGANIZAR",
    label: "Organizar",
    hint: "Um passo só",
    device: "ORGANIZAR",
  },
  {
    id: "decisao",
    stamp: "DECISAO",
    label: "Decisão",
    hint: "Criar distância",
    device: "DECISAO",
  },
  {
    id: "companhia",
    stamp: "COMPANHIA",
    label: "Companhia",
    hint: "Não ficar só",
    device: "COMPANHIA",
  },
];

export const TOOLS = [
  { id: "respirar", stamp: "RESPIRAR", label: "Respirar", seconds: "1 min" },
  { id: "aterrar", stamp: "ATERRAR", label: "Aterrar", seconds: "2 min" },
  { id: "adiar", stamp: "ADIAR", label: "Adiar impulso", seconds: "15 min" },
  { id: "passo", stamp: "UM PASSO", label: "Um passo", seconds: "5 min" },
  { id: "reuniao", stamp: "REUNIAO", label: "Reunião", seconds: "agora" },
  { id: "silencio", stamp: "SILENCIO", label: "Silêncio", seconds: "livre" },
];

const CRISIS_RE =
  /\b(suicid|me matar|quero morrer|nao quero mais viver|n[aã]o quero mais viver|acabar comigo|autoles|me cortar|tirar minha vida)\b/i;

export function todayISO(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function emptyState() {
  return {
    version: 1,
    updatedAt: Date.now(),
    config: {
      name: "",
      kids: [],
      workStart: "09:00",
      workEnd: "18:00",
      faith: false,
      trustedName: "",
      trustedPhone: "",
      calmingPhrase: "",
      phrasesToAvoid: "",
      helps: "",
      harms: "",
      communication: "toques e texto curto",
      neuro: "",
      goals: "",
      limits: "",
    },
    hoje: {
      date: "",
      type: null,
      mood: 0,
      energy: 0,
      sleep: 0,
      gratitude: "",
      kidExample: "",
    },
    ultimos_dias: [],
    restarts: 0,
    placa: {
      perfil: {},
      descobertas: [],
      gatilhos: [],
      insights: [],
      historico_estacoes: [],
      ciclos: [],
    },
    consents: {
      learn: false,
      alerts: false,
      cloud: false,
      sync: false,
    },
  };
}

export function rolloverDay(state, now = new Date()) {
  const next = structuredClone(state);
  const today = todayISO(now);
  if (next.hoje?.date && next.hoje.date !== today) {
    next.ultimos_dias = [
      {
        data: next.hoje.date,
        type: next.hoje.type,
        mood: next.hoje.mood,
        energy: next.hoje.energy,
        sleep: next.hoje.sleep,
      },
      ...(next.ultimos_dias || []),
    ].slice(0, 42);
    if (next.hoje.type === "crise") next.restarts = (next.restarts || 0) + 1;
    next.hoje = {
      date: today,
      type: null,
      mood: 0,
      energy: 0,
      sleep: 0,
      gratitude: "",
      kidExample: "",
    };
  } else if (!next.hoje?.date) {
    next.hoje = { ...(next.hoje || {}), date: today };
  }
  return next;
}

export function detectCrisisText(text) {
  return CRISIS_RE.test(String(text || "").normalize("NFD").replace(/[\u0300-\u036f]/g, ""));
}

export function weekPattern(state) {
  const days = [
    ...(state.hoje?.type ? [{ data: state.hoje.date, type: state.hoje.type, mood: state.hoje.mood, energy: state.hoje.energy, sleep: state.hoje.sleep }] : []),
    ...(state.ultimos_dias || []),
  ].slice(0, 7);

  const criseCount = days.filter((d) => d.type === "crise").length;
  const lowEnergy = days.filter((d) => Number(d.energy) > 0 && Number(d.energy) <= 2).length;
  const lowSleep = days.filter((d) => Number(d.sleep) > 0 && Number(d.sleep) <= 2).length;
  const lowMood = days.filter((d) => Number(d.mood) > 0 && Number(d.mood) <= 2).length;

  let alert = null;
  if (criseCount >= 3) {
    alert = "Os últimos dias pesaram. Isso não é falha. Vale reduzir a barra e avisar alguém de confiança.";
  } else if (lowSleep >= 3 && lowEnergy >= 3) {
    alert = "Sono e energia baixos se repetem. O corpo pede o básico antes de qualquer plano.";
  } else if (lowMood >= 4) {
    alert = "O humor baixo está se acumulando. Contato humano e uma ação mínima protegem mais do que se cobrar.";
  }

  return { days, criseCount, lowEnergy, lowSleep, lowMood, alert };
}

function greeting(state, now = new Date()) {
  const name = (state.config?.name || "").trim();
  const hour = now.getHours();
  const when = hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
  if (name) return `${when}, ${name}.`;
  return `${when}.`;
}

export function homeCopy(state, now = new Date()) {
  const rolled = rolloverDay(state, now);
  const pattern = weekPattern(rolled);
  const type = rolled.hoje?.type;
  const nameLine = greeting(rolled, now);
  if (type === "crise") {
    return {
      eyebrow: nameLine,
      title: "Hoje está em modo mínimo.",
      body: "Uma coisa só. Sem plano grande. Você já está fazendo a parte difícil: parar e pedir o próximo passo.",
      mode: "crise",
      alert: pattern.alert,
    };
  }
  if (type === "alta") {
    return {
      eyebrow: nameLine,
      title: "Há energia. Use com freio.",
      body: "Aproveite, e deixe uma âncora pequena para não gastar o dia inteiro de uma vez.",
      mode: "alta",
      alert: pattern.alert,
    };
  }
  if (!type) {
    return {
      eyebrow: nameLine,
      title: "O que você precisa agora?",
      body: "Um toque. Uma pergunta. O menor passo que aumenta clareza, estabilidade ou autonomia.",
      mode: "aberto",
      alert: pattern.alert,
    };
  }
  return {
    eyebrow: nameLine,
    title: "Siga o protocolo, sem drama.",
    body: "Nomeie, reduza o volume, escolha um passo que caiba nos próximos quinze minutos.",
    mode: "neutro",
    alert: pattern.alert,
  };
}

const QUESTIONS = {
  safety: {
    eyebrow: "SEGURANÇA",
    prompt: "Você está fisicamente seguro agora?",
    options: [
      { rotulo: "SIM", valor: "sim" },
      { rotulo: "NÃO", valor: "nao" },
      { rotulo: "NÃO SEI", valor: "nao_sei" },
    ],
  },
  intensity: {
    eyebrow: "INTENSIDADE",
    prompt: "Quanto isso está ocupando você agora?",
    options: [
      { rotulo: "BAIXO", valor: "1" },
      { rotulo: "MÉDIO", valor: "2" },
      { rotulo: "MUITO", valor: "3" },
    ],
  },
  capacity: {
    eyebrow: "CAPACIDADE",
    prompt: "O que ainda está disponível para você?",
    options: [
      { rotulo: "PENSAR", valor: "pensar" },
      { rotulo: "SÓ TOCAR", valor: "tocar" },
      { rotulo: "QUASE NADA", valor: "nada" },
    ],
  },
  context: {
    eyebrow: "CONTEXTO",
    prompt: "Onde você está neste momento?",
    options: [
      { rotulo: "EM CASA", valor: "casa" },
      { rotulo: "TRABALHO", valor: "trabalho" },
      { rotulo: "FORA", valor: "fora" },
    ],
  },
  need: {
    eyebrow: "NECESSIDADE",
    prompt: "Qual ganho mínimo faria diferença agora?",
    options: [
      { rotulo: "MENOS ESTÍMULO", valor: "estimulo" },
      { rotulo: "MAIS CLAREZA", valor: "clareza" },
      { rotulo: "APOIO HUMANO", valor: "humano" },
    ],
  },
};

const PATH_QUESTION = {
  sentir: {
    eyebrow: "SINAL",
    prompt: "Qual sinal parece mais próximo?",
    options: [
      { rotulo: "ANSIEDADE", valor: "ansiedade" },
      { rotulo: "TRISTEZA", valor: "tristeza" },
      { rotulo: "IRRITAÇÃO", valor: "irritacao" },
    ],
  },
  entender: {
    eyebrow: "ANTES",
    prompt: "O que veio imediatamente antes?",
    options: [
      { rotulo: "CONFLITO", valor: "conflito" },
      { rotulo: "COBRANÇA", valor: "cobranca" },
      { rotulo: "MUDANÇA", valor: "mudanca" },
    ],
  },
  regular: {
    eyebrow: "CORPO",
    prompt: "Onde a sobrecarga aparece mais?",
    options: [
      { rotulo: "PEITO", valor: "peito" },
      { rotulo: "CABEÇA", valor: "cabeca" },
      { rotulo: "CORPO TODO", valor: "corpo" },
    ],
  },
  organizar: {
    eyebrow: "PRESSÃO",
    prompt: "O que está travando o próximo passo?",
    options: [
      { rotulo: "MUITAS COISAS", valor: "volume" },
      { rotulo: "NÃO SEI COMO", valor: "como" },
      { rotulo: "SEM ENERGIA", valor: "energia" },
    ],
  },
  decisao: {
    eyebrow: "IMPULSO",
    prompt: "Essa ação pode ser desfeita depois?",
    options: [
      { rotulo: "SIM", valor: "reversivel" },
      { rotulo: "NÃO", valor: "irreversivel" },
      { rotulo: "NÃO SEI", valor: "nao_sei" },
    ],
  },
  companhia: {
    eyebrow: "PRESENÇA",
    prompt: "Que tipo de companhia ajuda agora?",
    options: [
      { rotulo: "SILÊNCIO", valor: "silencio" },
      { rotulo: "PERGUNTAS", valor: "perguntas" },
      { rotulo: "PASSO A PASSO", valor: "passo" },
    ],
  },
};

export function startSession(pathId) {
  const path = PATHS.find((p) => p.id === pathId) || PATHS[0];
  return {
    path: path.id,
    step: 0,
    answers: {},
    startedAt: Date.now(),
  };
}

function questionFor(session) {
  if (session.step === 0) return QUESTIONS.safety;
  if (session.step === 1) return QUESTIONS.intensity;
  if (session.step === 2) return QUESTIONS.capacity;
  if (session.step === 3) return PATH_QUESTION[session.path] || PATH_QUESTION.sentir;
  if (session.step === 4) return QUESTIONS.context;
  return QUESTIONS.need;
}

export function buildDiscovery(session, state = emptyState()) {
  const a = session.answers || {};
  if (a.safety && a.safety !== "sim") {
    return "Segurança precisa vir antes de qualquer descoberta.";
  }
  if (a.intensity === "3" && a.capacity === "nada") {
    return "Quando a intensidade sobe, reduzir escolhas protege a sua autonomia.";
  }
  if (session.path === "decisao") {
    return a.sinal === "irreversivel"
      ? "A decisão é difícil de desfazer; criar distância agora reduz dano."
      : "O impulso pode virar um teste reversível, sem decidir tudo agora.";
  }
  if (session.path === "organizar" && a.sinal === "volume") {
    return "O bloqueio parece vir do volume, não da falta de capacidade.";
  }
  if (session.path === "entender" && a.sinal === "cobranca") {
    return "Cobrança pode estar consumindo clareza antes mesmo da tarefa.";
  }
  if (session.path === "sentir" && a.sinal === "irritacao") {
    return "A irritação pode estar sinalizando limite ou estímulo demais.";
  }
  if (session.path === "sentir" && a.sinal === "ansiedade") {
    return "O alerta no corpo pede menos estímulo, não mais explicação.";
  }
  if (session.path === "sentir" && a.sinal === "tristeza") {
    return "Quando o peso aparece, contato humano e rotina mínima viram proteção.";
  }
  if (session.path === "regular" && a.sinal === "peito") {
    return "O peito apertado pede chão, ar e menos pergunta — não um plano.";
  }
  if (a.need === "humano") {
    return "Hoje, apoio humano parece mais útil do que insistir sozinho.";
  }
  const phrase = (state.config?.calmingPhrase || "").trim();
  if (phrase) return `Você já sabe o que ajuda: “${phrase}”. Vale usar agora, sem inventar outra estratégia.`;
  return "Você identificou um sinal antes de agir; isso abre uma escolha.";
}

export function buildAction(session, state = emptyState()) {
  const a = session.answers || {};
  if (a.safety && a.safety !== "sim") {
    return "Vá para perto de uma pessoa segura. Se houver risco imediato, ligue 192.";
  }
  if (a.need === "humano") {
    const who = (state.config?.trustedName || "").trim();
    return who
      ? `Envie agora para ${who}: “Preciso de companhia por alguns minutos. Não preciso explicar tudo.”`
      : "Envie agora: “Preciso de companhia por alguns minutos. Não preciso explicar tudo.”";
  }
  if (session.path === "decisao") return "Adie por 15 minutos. Escolha apenas uma ação que possa ser desfeita.";
  if (session.path === "organizar") return "Escreva uma única tarefa. Reduza até caber em cinco minutos.";
  if (session.path === "regular" || a.need === "estimulo") {
    return "Apoie os pés, solte os ombros e diminua luz ou som por dois minutos.";
  }
  if (session.path === "companhia") {
    return "Fique aqui. Nenhuma resposta é exigida. Toque quando quiser continuar.";
  }
  if (session.path === "sentir" && a.sinal === "ansiedade") {
    return "Apoie o corpo. Respire no ritmo que já existe. Não force o ar.";
  }
  if (session.path === "sentir" && a.sinal === "tristeza") {
    return "Reduza o objetivo deste momento. Água, alimento, descanso ou um contato.";
  }
  return "Não responda ainda. Nomeie o fato em uma frase e deixe o significado para depois.";
}

export function suggestedTool(session) {
  const a = session.answers || {};
  if (a.safety && a.safety !== "sim") return "sos";
  if (session.path === "decisao") return "adiar";
  if (session.path === "organizar") return "passo";
  if (session.path === "companhia" && a.sinal === "silencio") return "silencio";
  if (session.path === "regular" || a.need === "estimulo") return "respirar";
  if (a.sinal === "ansiedade") return "aterrar";
  if (session.path === "entender") return "passo";
  return "respirar";
}

function packQuestion(session, q) {
  const path = PATHS.find((p) => p.id === session.path);
  return {
    tipo: "pergunta",
    titulo: path?.stamp || "PLACA",
    texto: q.prompt,
    eyebrow: q.eyebrow,
    opcoes: q.options,
    progresso: Math.min(100, 12 + session.step * 14),
    descoberta: "",
    acao: "",
    ferramenta: null,
    seguranca: "ok",
    session,
  };
}

export function presentSession(session, state = emptyState()) {
  const a = session.answers || {};
  if (a.safety && a.safety !== "sim") {
    return {
      tipo: "crise",
      titulo: "APOIO HUMANO",
      texto: "Você não precisa passar por isso sozinho. Risco imediato: SAMU 192. Apoio emocional: CVV 188, 24h, gratuito.",
      eyebrow: "SEGURANÇA",
      opcoes: [
        { rotulo: "LIGAR 192", valor: "samu" },
        { rotulo: "CVV 188", valor: "cvv" },
        { rotulo: "VOLTAR", valor: "home" },
      ],
      progresso: 100,
      descoberta: buildDiscovery(session, state),
      acao: buildAction(session, state),
      ferramenta: "sos",
      seguranca: "crise",
      session,
    };
  }

  const collapsed = a.intensity === "3" && a.capacity === "nada" && session.step >= 2;
  if (session.step >= 6 || collapsed) {
    const tool = suggestedTool(session);
    return {
      tipo: "insight",
      titulo: "PRÓXIMO PASSO",
      texto: buildAction(session, state),
      eyebrow: "DESCOBERTA",
      opcoes: [
        { rotulo: "FAZER AGORA", valor: `tool:${tool}` },
        { rotulo: "GUARDAR", valor: "guardar" },
        { rotulo: "OUTRO CAMINHO", valor: "home" },
      ],
      progresso: 100,
      descoberta: buildDiscovery(session, state),
      acao: buildAction(session, state),
      ferramenta: tool,
      seguranca: a.intensity === "3" ? "atencao" : "ok",
      session,
    };
  }
  return packQuestion(session, questionFor(session));
}

export function answerSession(session, optionIndex, state = emptyState()) {
  const current = questionFor(session);
  const option = current.options[optionIndex];
  if (!option) return presentSession(session, state);

  const next = {
    ...session,
    answers: { ...session.answers },
    step: session.step,
  };

  if (session.step === 0) next.answers.safety = option.valor;
  else if (session.step === 1) next.answers.intensity = option.valor;
  else if (session.step === 2) next.answers.capacity = option.valor;
  else if (session.step === 3) next.answers.sinal = option.valor;
  else if (session.step === 4) next.answers.context = option.valor;
  else next.answers.need = option.valor;

  if (next.answers.safety && next.answers.safety !== "sim") {
    return presentSession(next, state);
  }

  next.step = session.step + 1;
  return presentSession(next, state);
}

export function checkinQuestions(state) {
  const rolled = rolloverDay(state);
  const kids = rolled.config?.kids?.filter((k) => k?.name) || [];
  const steps = [
    {
      id: "type",
      eyebrow: "HOJE",
      prompt: "Como está o dia até agora?",
      options: [
        { rotulo: "CRISE", valor: "crise" },
        { rotulo: "NEUTRO", valor: "neutro" },
        { rotulo: "ALTA", valor: "alta" },
      ],
    },
    {
      id: "mood",
      eyebrow: "HUMOR",
      prompt: "De 1 a 5, como está o humor?",
      options: [1, 2, 3, 4, 5].map((n) => ({ rotulo: String(n), valor: String(n) })),
    },
    {
      id: "energy",
      eyebrow: "ENERGIA",
      prompt: "De 1 a 5, quanta energia há agora?",
      options: [1, 2, 3, 4, 5].map((n) => ({ rotulo: String(n), valor: String(n) })),
    },
    {
      id: "sleep",
      eyebrow: "SONO",
      prompt: "De 1 a 5, como foi o sono?",
      options: [1, 2, 3, 4, 5].map((n) => ({ rotulo: String(n), valor: String(n) })),
    },
  ];
  if (kids.length) {
    steps.push({
      id: "kid",
      eyebrow: "PRESENÇA",
      prompt: `Um momento com ${kids[0].name} hoje — mesmo minúsculo?`,
      options: [
        { rotulo: "SIM, GUARDAR", valor: "sim" },
        { rotulo: "AINDA NÃO", valor: "nao" },
        { rotulo: "PULAR", valor: "pular" },
      ],
    });
  }
  return steps;
}

export function applyCheckin(state, answers) {
  const next = rolloverDay(state);
  const today = todayISO();
  next.hoje = {
    date: today,
    type: answers.type || next.hoje.type,
    mood: Number(answers.mood || next.hoje.mood || 0),
    energy: Number(answers.energy || next.hoje.energy || 0),
    sleep: Number(answers.sleep || next.hoje.sleep || 0),
    gratitude: answers.gratitude || next.hoje.gratitude || "",
    kidExample: answers.kidExample || next.hoje.kidExample || "",
  };
  next.updatedAt = Date.now();
  return next;
}

export function checkinInsight(state) {
  const type = state.hoje?.type;
  const mood = Number(state.hoje?.mood || 0);
  const energy = Number(state.hoje?.energy || 0);
  const sleep = Number(state.hoje?.sleep || 0);
  const pattern = weekPattern(state);

  if (type === "crise") {
    return {
      descoberta: "Em crise, a barra desce. Uma ação mínima e digna já conta.",
      acao: "Escolha regular, silêncio ou apoio humano. Nada além disso agora.",
      ferramenta: energy <= 2 ? "silencio" : "respirar",
      seguranca: "atencao",
    };
  }
  if (sleep <= 2 && energy <= 2) {
    return {
      descoberta: "O corpo está pedindo o básico. Plano grande hoje seria ruído.",
      acao: "Água, alimento, dez minutos deitado ou um único passo de cinco minutos.",
      ferramenta: "passo",
      seguranca: "ok",
    };
  }
  if (type === "alta" && mood >= 4) {
    return {
      descoberta: "Há folga. Use, e deixe um freio: uma âncora pequena, não cinco projetos.",
      acao: "Escolha uma coisa que importe e uma hora para parar.",
      ferramenta: "passo",
      seguranca: "ok",
    };
  }
  if (pattern.alert) {
    return {
      descoberta: pattern.alert,
      acao: "Hoje, o ganho é consistência baixa. Um passo visível e encerrar.",
      ferramenta: "passo",
      seguranca: "atencao",
    };
  }
  return {
    descoberta: "O dia foi nomeado. Isso já reduz a névoa.",
    acao: "Escolha o caminho que cabe agora: regular, organizar ou um passo.",
    ferramenta: mood <= 2 ? "aterrar" : "passo",
    seguranca: "ok",
  };
}

export function recordDiscovery(state, { texto, estacao, acao }) {
  const next = structuredClone(state);
  const item = {
    id: `d-${Date.now()}`,
    texto,
    estacao: estacao || "",
    acao: acao || "",
    em: new Date().toISOString(),
  };
  next.placa.descobertas = [item, ...(next.placa.descobertas || [])].slice(0, 80);
  next.placa.historico_estacoes = [
    { estacao: estacao || "", em: item.em },
    ...(next.placa.historico_estacoes || []),
  ].slice(0, 80);
  next.updatedAt = Date.now();
  return next;
}

export function recordTrigger(state, gatilho) {
  const next = structuredClone(state);
  next.placa.gatilhos = [
    {
      id: `g-${Date.now()}`,
      nome: gatilho.nome || "Gatilho",
      dispara: gatilho.dispara || "",
      custo: gatilho.custo || "",
      resposta: gatilho.resposta || "",
      em: new Date().toISOString(),
    },
    ...(next.placa.gatilhos || []),
  ].slice(0, 40);
  next.updatedAt = Date.now();
  return next;
}

export function recordCycle(state, session, result) {
  const next = recordDiscovery(state, {
    texto: result.descoberta,
    estacao: session.path,
    acao: result.acao,
  });
  next.placa.ciclos = [
    {
      path: session.path,
      answers: session.answers,
      em: new Date().toISOString(),
      seguranca: result.seguranca,
    },
    ...(next.placa.ciclos || []),
  ].slice(0, 40);
  return next;
}

const DEVICE_PATH = {
  "COMO ESTOU": "sentir",
  ENTENDER: "entender",
  REGULAR: "regular",
  ORGANIZAR: "organizar",
  DECISAO: "decisao",
  COMPANHIA: "companhia",
};

export function sanitize(value, max) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[\r\n=|]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, max);
}

export function encodeForDevice(data) {
  const options = Array.isArray(data.opcoes) ? data.opcoes.slice(0, 3) : [];
  const lines = [
    "ATLAS/1",
    `TYPE=${sanitize(data.tipo, 12) || "pergunta"}`,
    `TITLE=${sanitize(data.titulo, 24)}`,
    `TEXT=${sanitize(data.texto, 180)}`,
    `PROGRESS=${Math.max(0, Math.min(100, Number(data.progresso) || 0))}`,
    `DISCOVERY=${sanitize(data.descoberta, 140)}`,
    `ACTION=${sanitize(data.acao, 140)}`,
  ];
  options.forEach((option, index) => {
    lines.push(`OPT${index + 1}=${sanitize(option.rotulo, 24)}`);
    lines.push(`VAL${index + 1}=${sanitize(option.valor, 32) || `opcao_${index + 1}`}`);
  });
  return `${lines.join("\n")}\n`;
}

/**
 * Contrato do dispositivo Atlas: recebe JSON solto e devolve um passo.
 * Mantém uma sessão curta em memória via input.session, se vier.
 */
export function localJourney(input = {}, state = emptyState()) {
  const rawPath = String(input.caminho || input.path || input.estacao || "").toUpperCase();
  const pathId = DEVICE_PATH[rawPath] || PATHS.find((p) => p.id === input.path)?.id || "sentir";
  const selection = String(input.escolha || input.selection || input.valor || "").trim();
  const turn = Number(input.turno || input.turn || 0);

  let session = input.session;
  if (!session || typeof session !== "object") {
    session = startSession(pathId);
  }

  if (detectCrisisText(JSON.stringify(input))) {
    return presentSession({ ...session, answers: { ...session.answers, safety: "nao" } }, state);
  }

  if (!selection || /iniciar|start|jornada/i.test(selection) || turn <= 1) {
    if (!session.answers || Object.keys(session.answers).length === 0) {
      return presentSession(startSession(pathId), state);
    }
  }

  const current = presentSession(session, state);
  if (current.tipo !== "pergunta") return current;

  const idx = current.opcoes.findIndex(
    (o) => o.valor === selection || sanitize(o.rotulo, 24) === sanitize(selection, 24),
  );
  if (idx >= 0) return answerSession(session, idx, state);
  if (/^\d+$/.test(selection)) {
    const n = Number(selection) - 1;
    if (n >= 0 && n < current.opcoes.length) return answerSession(session, n, state);
  }
  return current;
}

export function mergeState(base, incoming) {
  const a = base && typeof base === "object" ? base : emptyState();
  const b = incoming && typeof incoming === "object" ? incoming : {};
  const merged = {
    ...emptyState(),
    ...a,
    ...b,
    config: { ...emptyState().config, ...(a.config || {}), ...(b.config || {}) },
    hoje: { ...emptyState().hoje, ...(a.hoje || {}), ...(b.hoje || {}) },
    placa: { ...emptyState().placa, ...(a.placa || {}), ...(b.placa || {}) },
    consents: { ...emptyState().consents, ...(a.consents || {}), ...(b.consents || {}) },
    ultimos_dias: Array.isArray(b.ultimos_dias) ? b.ultimos_dias : a.ultimos_dias || [],
  };
  merged.updatedAt = Math.max(Number(a.updatedAt || 0), Number(b.updatedAt || 0), Date.now());
  return rolloverDay(merged);
}
