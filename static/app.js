'use strict';

const $ = (id) => document.getElementById(id);

const state = {
  sessionId: null, lastPrompt: '', historyId: null, complete: false,
  rawPrompt: '', turns: [], conn: null, tab: 'optimize'
};

const BASE_URL_PLACEHOLDER = {
  openai: 'z. B. https://api.openai.com/v1 oder http://localhost:11434/v1',
  anthropic: 'z. B. https://api.anthropic.com'
};

// Einziges Ziel fuer den externen Browser (= controllers/api.py REPO_URL, PyBridge.kt REPO_URL).
const REPO_URL = 'https://github.com/Nope-im-not-pro/PromptEngineer';

const TAB_TITLES = { optimize: 'Optimieren', history: 'Historie', settings: 'Einstellungen' };
const STEPS = ['input', 'question', 'result'];
const STEP_NAMES = { input: 'Eingabe', question: 'Rückfrage', result: 'Ergebnis' };

// ---------- Hilfen ----------

function showError(msg) {
  $('error-text').textContent = msg;
  $('error').hidden = !msg;
}

function setBusy(on) {
  $('busy').hidden = !on;
  document.querySelectorAll('button, #theme, #layout').forEach((b) => { b.disabled = on; });
}

async function call(method, ...args) {
  showError('');
  setBusy(true);
  try {
    const res = await window.pywebview.api[method](...args);
    if (!res || !res.ok) {
      showError((res && res.error) || 'Unbekannter Fehler.');
      return null;
    }
    return res;
  } catch (e) {
    showError('Interner Fehler: ' + e);
    return null;
  } finally {
    setBusy(false);
  }
}

function flash(el, text) {
  el.textContent = text;
  setTimeout(() => { if (el.textContent === text) el.textContent = ''; }, 2000);
}

async function copyText(textarea, statusEl) {
  if (window.AndroidBridge && window.AndroidBridge.copy_text) {
    window.AndroidBridge.copy_text(textarea.value);
  } else {
    try {
      await navigator.clipboard.writeText(textarea.value);
    } catch (e) {
      textarea.select();
      document.execCommand('copy');
    }
  }
  flash(statusEl, 'Kopiert');
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }) + ' ' +
    d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
}

function turnNode(role, text) {
  const div = el('div', 'turn ' + role);
  div.appendChild(el('span', 'tag', role));
  div.appendChild(document.createTextNode(text));
  return div;
}

// ---------- Segment-Umschalter (Quelle: verstecktes <select>) ----------

function initSegs() {
  document.querySelectorAll('.seg[data-for]').forEach((seg) => {
    const select = $(seg.dataset.for);
    Array.from(select.options).forEach((opt) => {
      const btn = el('button', '', opt.textContent);
      btn.type = 'button';
      btn.dataset.value = opt.value;
      btn.addEventListener('click', () => {
        if (select.value === opt.value) return;
        select.value = opt.value;
        select.dispatchEvent(new Event('change'));
      });
      seg.appendChild(btn);
    });
    select.addEventListener('change', () => syncSeg(select.id));
    syncSeg(select.id);
  });
}

function syncSeg(id) {
  const value = $(id).value;
  document.querySelectorAll('.seg[data-for="' + id + '"] button').forEach((b) => {
    b.setAttribute('aria-pressed', String(b.dataset.value === value));
  });
}

// ---------- Tabs ----------

function setTitle(title, tag) {
  $('view-title').textContent = title;
  $('view-tag').textContent = tag || '';
}

function showTab(name) {
  state.tab = name;
  $('app').dataset.tab = name;
  document.querySelectorAll('.tab').forEach((t) => {
    t.classList.toggle('active', t.dataset.tab === name);
    if (t.dataset.tab === name) t.setAttribute('aria-current', 'page');
    else t.removeAttribute('aria-current');
  });
  $('tab-optimize').hidden = name !== 'optimize';
  $('tab-history').hidden = name !== 'history';
  $('tab-settings').hidden = name !== 'settings';
  setTitle(TAB_TITLES[name]);
  if (name === 'history') {
    return loadHistory();
  }
  return Promise.resolve();
}

function goBack() {
  if (state.tab === 'history' && !$('history-detail').hidden) {
    closeDetail();
  } else {
    showTab('optimize');
  }
}

// ---------- Optimieren ----------

function showStep(step) {
  const index = STEPS.indexOf(step);
  STEPS.forEach((s, i) => {
    $('step-' + s).hidden = s !== step;
    const label = $('step-label-' + s);
    label.classList.toggle('current', s === step);
    label.classList.toggle('done', i < index);
    if (s === step) label.setAttribute('aria-current', 'step');
    else label.removeAttribute('aria-current');
  });
  $('step-caption-name').textContent = STEP_NAMES[step];
  $('step-caption-n').textContent = 'Schritt ' + (index + 1) + ' von 3';
}

function renderOwnTurns() {
  $('res-raw').textContent = state.rawPrompt;
  const box = $('res-turns');
  box.replaceChildren();
  state.turns.forEach((t) => box.appendChild(turnNode(t.role, t.text)));
}

function renderResult(result) {
  if (result.status === 'unclear') {
    state.turns.push({ role: 'assistant', text: result.question });
    $('question').textContent = result.question;
    const box = $('options');
    box.replaceChildren();
    result.options.forEach((opt, index) => {
      const btn = el('button', 'opt');
      btn.type = 'button';
      btn.appendChild(el('b', 'opt-label', opt.label));
      if (opt.description) {
        btn.appendChild(el('span', 'opt-desc', opt.description));
      }
      btn.addEventListener('click', () => choose(index, opt, btn));
      box.appendChild(btn);
    });
    $('q-mine-text').textContent = state.lastPrompt;
    $('refine-prompt').value = state.lastPrompt;
    showStep('question');
  } else {
    $('result').value = result.optimized_prompt;
    renderOwnTurns();
    showStep('result');
  }
}

async function optimize() {
  const prompt = $('raw-prompt').value.trim();
  if (!prompt) {
    showError('Bitte zuerst einen Prompt eingeben.');
    return;
  }
  const res = await call('optimize_start', prompt);
  if (!res) return;
  state.sessionId = res.session_id;
  state.lastPrompt = prompt;
  state.rawPrompt = prompt;
  state.turns = [];
  refreshRecent();
  renderResult(res.result);
}

async function choose(index, opt, btn) {
  document.querySelectorAll('#options .opt').forEach((b) => {
    b.setAttribute('aria-pressed', String(b === btn));
  });
  const res = await call('optimize_choose', state.sessionId, index);
  if (!res) return;
  state.turns.push({ role: 'user', text: opt.description ? opt.label + ' - ' + opt.description : opt.label });
  renderResult(res.result);
}

async function refine() {
  const prompt = $('refine-prompt').value.trim();
  if (!prompt) {
    showError('Bitte den Prompt neu formulieren.');
    return;
  }
  const res = await call('optimize_refine', state.sessionId, prompt);
  if (!res) return;
  state.lastPrompt = prompt;
  state.turns.push({ role: 'user', text: prompt });
  renderResult(res.result);
}

function newPrompt() {
  state.sessionId = null;
  state.lastPrompt = '';
  state.rawPrompt = '';
  state.turns = [];
  $('raw-prompt').value = '';
  $('refine-prompt').value = '';
  $('result').value = '';
  showError('');
  showStep('input');
  $('raw-prompt').focus();
}

// ---------- Historie ----------

function describeTurn(turn) {
  if (turn.role !== 'assistant') return turn.content;
  const text = turn.content;
  try {
    const data = JSON.parse(text.slice(text.indexOf('{'), text.lastIndexOf('}') + 1));
    if (data.status === 'unclear') {
      const labels = (data.options || []).map((o) => '- ' + o.label).join('\n');
      return 'Rückfrage: ' + data.question + '\n' + labels;
    }
    if (data.status === 'clear') return 'Ergebnis geliefert.';
  } catch (e) { /* Rohtext anzeigen */ }
  return text;
}

function entryNode(className, item, withStatus) {
  const btn = el('button', className);
  btn.type = 'button';
  btn.appendChild(el('span', '', item.raw_prompt.slice(0, 200)));
  const status = withStatus ? ' · ' + (item.status === 'done' ? 'fertig' : 'offen') : '';
  btn.appendChild(el('time', '', formatDate(item.created_at) + status));
  return btn;
}

function closeDetail() {
  state.historyId = null;
  $('history-detail').hidden = true;
  delete $('app').dataset.detail;
  document.querySelectorAll('#history-list li').forEach((li) => li.classList.remove('selected'));
  if (state.tab === 'history') setTitle(TAB_TITLES.history, $('history-count').textContent);
}

async function loadHistory() {
  closeDetail();
  const res = await call('history_list');
  const list = $('history-list');
  list.replaceChildren();
  if (!res) { $('history-empty').hidden = true; return; }
  const items = res.items;
  $('history-empty').hidden = items.length > 0;
  $('history-count').textContent = items.length === 1 ? '1 Eintrag' : items.length + ' Einträge';
  setTitle(TAB_TITLES.history, $('history-count').textContent);
  items.forEach((item) => {
    const li = document.createElement('li');
    li.dataset.id = item.id;
    const btn = entryNode('hist-item', item, true);
    btn.addEventListener('click', () => showHistoryItem(item.id, li));
    li.appendChild(btn);
    list.appendChild(li);
  });
  renderRecent(items);
}

async function showHistoryItem(id, li) {
  const res = await call('history_get', id);
  if (!res) return;
  const item = res.item;
  state.historyId = id;
  document.querySelectorAll('#history-list li').forEach((node) => {
    node.classList.toggle('selected', node === li);
    const btn = node.firstChild;
    if (node === li) btn.setAttribute('aria-current', 'true');
    else btn.removeAttribute('aria-current');
  });
  $('detail-raw').textContent = item.raw_prompt;
  const turns = $('detail-turns');
  turns.replaceChildren();
  item.turns.forEach((turn) => turns.appendChild(turnNode(turn.role, describeTurn(turn))));
  $('detail-result').value = item.optimized_prompt || '';
  $('detail-date').textContent = formatDate(item.created_at);
  $('history-detail').hidden = false;
  $('app').dataset.detail = '1';
  setTitle('Eintrag', formatDate(item.created_at));
}

async function deleteHistoryItem() {
  if (state.historyId === null || !confirm('Diesen Eintrag wirklich löschen?')) return;
  const res = await call('history_delete', state.historyId);
  if (!res) return;
  const li = document.querySelector('#history-list li[data-id="' + state.historyId + '"]');
  if (li) li.remove();
  closeDetail();
  const count = $('history-list').children.length;
  $('history-empty').hidden = count > 0;
  $('history-count').textContent = count === 1 ? '1 Eintrag' : count + ' Einträge';
  setTitle(TAB_TITLES.history, $('history-count').textContent);
  refreshRecent();
}

// Seitenleiste "Zuletzt" (Werkbank-Desktop): still nachladen, ohne Busy-/Fehleranzeige.
function renderRecent(items) {
  const box = $('recent-list');
  box.replaceChildren();
  items.slice(0, 4).forEach((item) => {
    const btn = entryNode('recent-item', item, false);
    btn.addEventListener('click', () => openRecent(item.id));
    box.appendChild(btn);
  });
  $('recent-empty').hidden = items.length > 0;
}

async function refreshRecent() {
  try {
    const res = await window.pywebview.api.history_list();
    if (res && res.ok) renderRecent(res.items);
  } catch (e) { /* Seitenleiste bleibt unveraendert */ }
}

async function openRecent(id) {
  await showTab('history');
  const li = document.querySelector('#history-list li[data-id="' + id + '"]');
  if (li) showHistoryItem(id, li);
}

// ---------- Einstellungen ----------

function updateBaseUrlPlaceholder() {
  $('base-url').placeholder = BASE_URL_PLACEHOLDER[$('api-type').value] || '';
}

function renderConn() {
  const c = state.conn;
  const ok = c && state.complete;
  const sep = document.documentElement.dataset.layout === 'werkbank' ? '\n' : ' / ';
  $('conn').textContent = ok ? c.api_type + sep + c.model : 'nicht verbunden';
  $('busy-conn').textContent = ok ? c.api_type + ' / ' + c.model : '';
  $('q-model').textContent = ok ? c.model : '';
  $('res-model').textContent = ok ? c.model : '';
}

function applySettings(s) {
  $('api-type').value = s.api_type || 'openai';
  $('base-url').value = s.base_url || '';
  $('model').value = s.model || '';
  $('api-key').value = '';
  $('clear-key').checked = false;
  $('api-key').placeholder = s.has_key
    ? 'Gespeichert: ' + s.key_hint + ' (leer lassen = beibehalten)'
    : 'API-Key eingeben (bei lokalen OpenAI-kompatiblen Endpunkten optional)';
  updateBaseUrlPlaceholder();
  syncSeg('api-type');
  state.conn = { api_type: s.api_type, model: s.model };
  renderConn();
}

function settingsForm() {
  return {
    api_type: $('api-type').value,
    base_url: $('base-url').value.trim(),
    api_key: $('api-key').value.trim()
  };
}

async function loadModels() {
  const res = await call('list_models', settingsForm());
  if (!res) return;
  const list = $('model-list');
  list.replaceChildren();
  res.models.forEach((m) => {
    const opt = document.createElement('option');
    opt.value = m;
    list.appendChild(opt);
  });
  $('save-status').textContent = res.models.length + ' Modelle geladen. Feld Modell anklicken zur Auswahl.';
}

async function saveSettings() {
  const data = settingsForm();
  data.model = $('model').value.trim();
  data.clear_key = $('clear-key').checked;
  if (!await call('save_settings', data)) return;
  const res = await call('get_settings');
  if (!res) return;
  const wasComplete = state.complete;
  state.complete = res.complete;
  applySettings(res.settings);
  $('first-run').hidden = res.complete;
  flash($('save-status'), 'Gespeichert');
  if (!wasComplete && res.complete) {
    showTab('optimize');
    $('raw-prompt').focus();
  }
}

// ---------- Darstellung ----------

function applyTheme(mode) {
  const valid = mode === 'light' || mode === 'dark';
  if (valid) {
    document.documentElement.dataset.theme = mode;
  } else {
    delete document.documentElement.dataset.theme;
  }
  $('theme').value = valid ? mode : 'system';
  syncSeg('theme');
}

async function changeTheme() {
  const mode = $('theme').value;
  applyTheme(mode);
  await call('set_theme', mode);
}

function applyLayout(layout) {
  const value = layout === 'werkbank' || layout === 'fokus' ? layout
    : (window.AndroidBridge ? 'fokus' : 'werkbank');
  document.documentElement.dataset.layout = value;
  $('layout').value = value;
  syncSeg('layout');
  renderConn();
}

async function changeLayout() {
  const layout = $('layout').value;
  applyLayout(layout);
  await call('set_layout', layout);
}

// ---------- Ueber: Repo-Link im externen Browser ----------

async function openRepo(e) {
  e.preventDefault();
  if (window.AndroidBridge && window.AndroidBridge.open_url) {
    if (!window.AndroidBridge.open_url(REPO_URL)) showError('Link konnte nicht geöffnet werden.');
    return;
  }
  await call('open_url', REPO_URL);
}

// ---------- Init ----------

function onCtrlEnter(node, fn) {
  node.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      if (!$('busy').hidden) return;
      fn();
    }
  });
}

function bindEvents() {
  document.querySelectorAll('.tab').forEach((t) => {
    t.addEventListener('click', () => showTab(t.dataset.tab));
  });
  $('btn-back').addEventListener('click', goBack);
  $('btn-optimize').addEventListener('click', optimize);
  $('btn-refine').addEventListener('click', refine);
  $('btn-copy').addEventListener('click', () => copyText($('result'), $('copy-status')));
  $('btn-new').addEventListener('click', newPrompt);
  $('btn-detail-copy').addEventListener('click', () => copyText($('detail-result'), $('detail-copy-status')));
  $('btn-detail-delete').addEventListener('click', deleteHistoryItem);
  $('detail-grip').addEventListener('click', closeDetail);
  $('api-type').addEventListener('change', updateBaseUrlPlaceholder);
  $('btn-models').addEventListener('click', loadModels);
  $('btn-save').addEventListener('click', saveSettings);
  $('theme').addEventListener('change', changeTheme);
  $('layout').addEventListener('change', changeLayout);
  $('repo-link').addEventListener('click', openRepo);
  onCtrlEnter($('raw-prompt'), optimize);
  onCtrlEnter($('refine-prompt'), refine);
}

window.addEventListener('pywebviewready', async () => {
  initSegs();
  bindEvents();
  showStep('input');
  try {
    const res = await call('get_settings');
    if (res) {
      state.complete = res.complete;
      applyLayout(res.layout);
      applySettings(res.settings);
      applyTheme(res.theme);
      $('first-run').hidden = res.complete;
      showTab(res.complete ? 'optimize' : 'settings');
      // Nur mit fertigen Einstellungen: history_list legt sonst history.db an (--selftest prueft das).
      if (res.complete) refreshRecent();
    } else {
      applyLayout();
      showTab('settings');
    }
  } finally {
    $('app').dataset.ready = '1';
  }
});
