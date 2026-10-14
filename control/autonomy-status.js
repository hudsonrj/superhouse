/* Indicador do estado autoritativo na interface já existente do Control. */
(() => {
  const badge = document.createElement('div');
  badge.setAttribute('role', 'status');
  badge.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:2147483647;padding:12px 16px;border-radius:12px;background:#172033;color:#e2e8f0;font:14px system-ui;box-shadow:0 4px 20px #0005;max-width:360px;pointer-events:none';
  badge.textContent = 'Autonomia: verificando…';
  document.body.append(badge);
  async function refresh() {
    try {
      const response = await fetch('/api/autonomy', { cache: 'no-store', redirect: 'error' });
      if (!response.ok) throw new Error();
      const state = await response.json();
      badge.textContent = state.enabled ? `● Autônomo ativo · ${state.level > 0 ? "+" : ""}${state.level} · escala −3 a +3 · ${state.label}` : state.expired ? 'Autonomia suspensa — macropad sem conexão' : '○ Modo autônomo desativado';
      badge.style.border = `1px solid ${state.enabled ? '#22c55e' : '#64748b'}`;
    } catch { badge.textContent = 'Autonomia: estado indisponível'; }
  }
  refresh(); setInterval(refresh, 5000);
})();
