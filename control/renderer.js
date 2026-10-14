'use strict';
const $ = id => document.getElementById(id);
let busy = false, held = false, recorder, stream, timer, generation = 0, playback;
const status = (text, type = '') => { $('status').textContent = text; $('status').className = type; };
async function invoke(promise) { const result = await promise; if (!result.ok) throw new Error(result.error); return result.value; }
function setBusy(value) { busy = value; $('send').disabled = value; $('question').disabled = value; }

function format(text) {
  const container = document.createDocumentFragment(); let code, list;
  for (const line of text.split('\n')) {
    if (/^\s*```/.test(line)) {
      if (code) code = null;
      else { const pre = document.createElement('pre'); code = document.createElement('code'); pre.append(code); container.append(pre); }
      list = null; continue;
    }
    if (code) { code.textContent += line + '\n'; continue; }
    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    const bullet = /^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+)$/.exec(line);
    if (bullet) {
      const tag = /^\s*\d/.test(line) ? 'OL' : 'UL';
      if (!list || list.tagName !== tag) { list = document.createElement(tag); container.append(list); }
      const item = document.createElement('li'); item.textContent = bullet[1]; list.append(item); continue;
    }
    list = null;
    const node = document.createElement(heading ? (heading[1].length < 3 ? 'h2' : 'h3') : 'p');
    const value = heading ? heading[2] : line;
    for (const part of value.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)) {
      if (part.startsWith('**') || part.startsWith('`')) {
        const element = document.createElement(part.startsWith('**') ? 'strong' : 'code');
        element.textContent = part.startsWith('**') ? part.slice(2, -2) : part.slice(1, -1); node.append(element);
      } else node.append(document.createTextNode(part));
    }
    container.append(node);
  }
  $('answer').replaceChildren(container);
}

async function speak(text, id) {
  const chunks = await invoke(window.control.chunks(text));
  for (const chunk of chunks) {
    if (id !== generation) return;
    const bytes = await invoke(window.control.speech(chunk));
    if (id !== generation || !bytes) continue;
    const url = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }));
    const audio = new Audio(url); playback = audio;
    try {
      await new Promise((resolve, reject) => {
        audio.onended = resolve; audio.onpause = resolve;
        audio.onerror = () => reject(new Error('Não foi possível reproduzir a resposta.'));
        audio.play().catch(reject);
      });
    } finally { URL.revokeObjectURL(url); if (playback === audio) playback = null; }
  }
}

async function ask(text, voice, id = generation) {
  const question = text.trim();
  if (!question) { status('Escreva uma pergunta antes de enviar.', 'error'); return; }
  setBusy(true); $('question').value = question;
  status('Consultando o Control…'); $('result').hidden = true;
  try {
    const answer = await invoke(window.control.ask(question));
    if (id !== generation) return;
    format(answer); $('answer').dataset.raw = answer; $('result').hidden = false;
    if (voice) { status('Resposta recebida. Preparando e reproduzindo a voz…'); await speak(answer, id); }
    if (id === generation) status('Resposta recebida do Control.');
  } catch (error) { if (id === generation) status(error.message, 'error'); }
  finally { if (id === generation) setBusy(false); }
}

async function startRecording() {
  if (busy || held) return;
  held = true; setBusy(true); const id = ++generation;
  status('Abrindo o microfone…'); $('result').hidden = true;
  let microphone;
  try {
    microphone = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    if (!held || id !== generation) {
      microphone.getTracks().forEach(track => track.stop());
      if (id === generation) { setBusy(false); status('Segure o botão até aparecer Gravando e fale sua pergunta.'); }
      return;
    }
    stream = microphone;
    const parts = []; const started = Date.now();
    const recording = new MediaRecorder(microphone, { mimeType: 'audio/webm;codecs=opus' }); recorder = recording;
    recording.ondataavailable = event => { if (event.data.size) parts.push(event.data); };
    recording.onstop = async () => {
      if (id === generation) clearTimeout(timer);
      microphone.getTracks().forEach(track => track.stop());
      if (stream === microphone) stream = null;
      if (recorder === recording) recorder = null;
      if (id !== generation) return;
      held = false;
      try {
        if (Date.now() - started < 300) throw new Error('Gravação muito curta. Segure o botão enquanto fala.');
        status('Transcrevendo sua pergunta…');
        const bytes = new Uint8Array(await new Blob(parts).arrayBuffer());
        const text = await invoke(window.control.transcribe(bytes));
        if (id === generation) await ask(text, true, id);
      } catch (error) { if (id === generation) { status(error.message, 'error'); setBusy(false); } }
    };
    recording.onerror = () => { if (id === generation) { cancel(); status('Erro ao gravar o microfone. Tente novamente.', 'error'); } };
    recording.start(); status('● Gravando — fale e solte o botão para enviar.', 'recording');
    timer = setTimeout(stopRecording, 120000);
  } catch (error) {
    microphone?.getTracks().forEach(track => track.stop());
    if (id === generation) { stream = null; held = false; setBusy(false); status('Não foi possível abrir o microfone: ' + error.message, 'error'); }
  }
}
function stopRecording() { held = false; if (recorder?.state === 'recording') recorder.stop(); }
function cancel() {
  generation++; held = false; clearTimeout(timer);
  if (recorder?.state === 'recording') recorder.stop();
  stream?.getTracks().forEach(track => track.stop()); playback?.pause();
  window.control.cancel(); setBusy(false);
}
$('form').addEventListener('submit', event => { event.preventDefault(); if (!busy) ask($('question').value, false); });
$('question').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); $('form').requestSubmit(); }
});
$('copy').onclick = () => navigator.clipboard.writeText($('answer').dataset.raw || '').catch(() => status('Não foi possível copiar a resposta.', 'error'));
$('close').onclick = () => { cancel(); window.control.hide(); };
document.addEventListener('keydown', event => { if (event.key === 'Escape') $('close').click(); });
window.control.onCommand(value => {
  if (value === 'start') startRecording();
  if (value === 'stop') stopRecording();
  if (value === 'cancel') cancel();
  if (value === 'text' && !busy) { status('Escreva sua pergunta para o Control.'); $('question').focus(); }
});
window.control.onAutonomy(state => {
  const badge = $('autonomy-status');
  badge.className = state.unavailable || state.error ? 'error' : state.enabled ? 'active' : '';
  badge.textContent = state.unavailable ? 'Autonomia indisponível — ' + (state.error || 'sem confirmação do Control') :
    state.pending ? 'Alterando autonomia no Control…' :
    state.enabled ? `● Modo autônomo ativo · ${state.level > 0 ? "+" : ""}${state.level} · escala −3 a +3 · ${state.label}` :
    state.expired ? 'Autonomia suspensa — conexão com o macropad expirou' : '○ Modo autônomo desativado';
  if (state.bridge === 'sending') badge.textContent += ' · Enviando à ponte…';
  if (state.bridge === 'accepted') badge.textContent += ' · Evento recebido pela ponte';
  if (state.bridge === 'unknown') badge.textContent += ' · Ponte sem confirmação';
});
window.control.ready();
