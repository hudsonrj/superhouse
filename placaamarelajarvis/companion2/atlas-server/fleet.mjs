function text(value, max = 80) {
  return String(value ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, max);
}

function count(value) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? Math.floor(number) : 0;
}

export function sanitizeFleet(raw) {
  const data = raw && typeof raw === "object" ? raw : {};
  const agents = Array.isArray(data.agents_list) ? data.agents_list : [];
  return {
    available: true,
    health: text(data.health, 24),
    brief: text(data.brief, 120),
    alerts: count(data.alerts),
    tasks: count(data.tasks),
    working: count(data.working),
    down: count(data.down),
    agents_list: agents.slice(0, 30).map((agent) => ({
      n: text(agent?.n, 40),
      st: agent?.st === "RUN" ? "RUN" : "IDLE",
      act: text(agent?.act, 60),
      nwork: count(agent?.nwork),
      head: text(agent?.head, 100),
      role: text(agent?.role, 100),
      short: text(agent?.short, 12),
      team: text(agent?.team, 24) || "outros",
    })),
  };
}
