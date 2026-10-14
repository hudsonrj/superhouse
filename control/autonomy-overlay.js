'use strict';
window.control.onAutonomy(state => {
  document.body.className = state.unavailable || state.error ? 'error' : state.enabled ? 'active' : '';
  document.getElementById('mode').textContent = state.unavailable ? 'SEM CONFIRMAÇÃO DO CONTROL' :
    state.pending ? 'AJUSTANDO · AGUARDANDO CONTROL…' : state.enabled ? 'AUTONOMIA ATIVA' : 'AUTONOMIA DESATIVADA';
  document.getElementById('level').textContent = state.unavailable ? '—' : `${(state.previewLevel ?? state.level) > 0 ? '+' : ''}${state.previewLevel ?? state.level} · −3 a +3`;
  document.getElementById('description').textContent = state.error || (state.pending ? 'Valor solicitado; autorização só muda após confirmação do Control.' : '') ||
    (state.enabled ? state.label : 'Ative com Ctrl+Alt+Shift+Win+A para ajustar o nível.');
});
