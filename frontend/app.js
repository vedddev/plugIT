const app = document.querySelector('#app');
const periods = { today: 'Today', '7d': '7 Days', '30d': '30 Days', all: 'All Time' };
let state = { key: sessionStorage.getItem('smartllm.adminKey') || '', period: 'all', loading: false, error: null, data: null };
const esc = value => String(value ?? '—').replace(/[&<>"']/g, char => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;' }[char]));
const num = value => new Intl.NumberFormat().format(value || 0);
const usd = value => new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 6 }).format(value || 0);
const ms = value => `${Math.round(value || 0)} ms`;

async function api(path) {
  const response = await fetch(`/dashboard/${path}`, { headers: { 'X-Admin-Key': state.key } });
  if (response.status === 401 || response.status === 403) throw Object.assign(new Error('Your admin key was not accepted.'), { auth: true });
  if (!response.ok) throw new Error(`Dashboard API returned ${response.status}.`);
  return response.json();
}
async function load() {
  state.loading = true; state.error = null; render();
  try {
    const query = `period=${state.period}`;
    const [stats, usage, recent] = await Promise.all([api(`stats?${query}`), api(`usage?${query}`), api(`recent?${query}&limit=50`)]);
    state.data = { stats, usage, recent: recent.data || [] };
  } catch (error) { state.data = null; state.error = error; }
  state.loading = false; render();
}
function login() {
  app.innerHTML = `<section class="login"><div class="login-card"><div class="brand-mark">S</div><p class="eyebrow">SMARTLLM</p><h1>Dashboard access</h1><p>Enter the local admin key to view live gateway analytics.</p><form id="login-form"><label>Admin key<input name="key" type="password" autocomplete="current-password" required autofocus /></label><button>Open dashboard</button></form><small>The key is retained only for this browser session and is never stored in source code.</small></div></section>`;
  document.querySelector('#login-form').addEventListener('submit', event => { event.preventDefault(); state.key = new FormData(event.target).get('key').trim(); sessionStorage.setItem('smartllm.adminKey', state.key); load(); });
}
function line(items, field, color) {
  if (!items.length) return `<div class="chart-empty">No activity in this range.</div>`;
  const values = items.map(item => Number(item[field]) || 0), max = Math.max(...values, 1);
  const points = values.map((value, index) => `${index * (100 / Math.max(values.length - 1, 1))},${92 - (value / max) * 76}`).join(' ');
  return `<svg viewBox="0 0 100 100" preserveAspectRatio="none"><line x1="0" y1="92" x2="100" y2="92" class="grid"/><polyline points="${points}" fill="none" stroke="${color}" stroke-width="2.5" vector-effect="non-scaling-stroke"/></svg><div class="chart-labels"><span>${esc(items[0].date)}</span><span>${esc(items.at(-1).date)}</span></div>`;
}
function bars(items) {
  if (!items.length) return `<div class="chart-empty">No usage recorded.</div>`;
  const max = Math.max(...items.map(item => item.requests), 1);
  return `<div class="bars">${items.map(item => `<div class="bar-row"><span title="${esc(item.name)}">${esc(item.name)}</span><div><i style="width:${item.requests / max * 100}%"></i></div><b>${num(item.requests)}</b></div>`).join('')}</div>`;
}
function card(name, value, note, color) { return `<article class="metric ${color}"><span>${name}</span><strong>${value}</strong><small>${note}</small></article>`; }
function render() {
  if (!state.key) return login();
  const { stats = {}, usage = {}, recent = [] } = state.data || {};
  const screen = state.loading ? `<div class="state"><div class="spinner"></div><h2>Loading live dashboard data…</h2></div>` : state.error ? `<div class="state error"><h2>${state.error.auth ? 'Authentication required' : 'Unable to load dashboard'}</h2><p>${esc(state.error.message)}</p><button id="retry">Try again</button></div>` : !stats.total_requests ? `<div class="state"><h2>No requests yet</h2><p>Requests made through SmartLLM will appear here for ${periods[state.period].toLowerCase()}.</p></div>` : `<section class="metrics">${card('Total Requests', num(stats.total_requests), `${num(stats.requests_today)} today`, 'purple')}${card('Total Tokens', num(stats.total_tokens), `${num(stats.total_input_tokens)} input · ${num(stats.total_output_tokens)} output`, 'blue')}${card('Total Cost', usd(stats.total_cost), 'Across selected period', 'green')}${card('Average Latency', ms(stats.average_latency), 'Response time', 'orange')}${card('Cache Hit Rate', `${Math.round((stats.cache_hit_rate || 0) * 100)}%`, `${num(stats.cache_hits)} hits / ${num(stats.cache_misses)} misses`, 'cyan')}${card('Successful Requests', num(stats.successful_requests), 'Completed successfully', 'green')}${card('Failed Requests', num(stats.failed_requests), 'Require attention', 'red')}</section><section class="chart-grid"><article class="panel wide"><div class="panel-title"><h2>Requests over time</h2><span>Daily volume</span></div>${line(usage.time_series || [], 'requests', '#7c3aed')}</article><article class="panel"><div class="panel-title"><h2>Cache hits vs misses</h2></div><div class="donut" style="--value:${(stats.cache_hit_rate || 0) * 100}%"><b>${Math.round((stats.cache_hit_rate || 0) * 100)}%</b><small>hit rate</small></div></article><article class="panel"><div class="panel-title"><h2>Token usage</h2><span>Daily tokens</span></div>${line(usage.time_series || [], 'total_tokens', '#2563eb')}</article><article class="panel"><div class="panel-title"><h2>Cost over time</h2><span>Daily spend</span></div>${line(usage.time_series || [], 'total_cost', '#059669')}</article><article class="panel"><div class="panel-title"><h2>Provider usage</h2><span>By requests</span></div>${bars(usage.provider_usage || [])}</article><article class="panel"><div class="panel-title"><h2>Model usage</h2><span>By requests</span></div>${bars(usage.model_usage || [])}</article></section><section class="panel table-panel"><div class="panel-title"><div><h2>Recent requests</h2><span>Latest gateway activity</span></div><b>${num(recent.length)} events</b></div><div class="table-wrap"><table><thead><tr><th>Timestamp</th><th>Provider / model</th><th>Request</th><th>Latency</th><th>Input</th><th>Output</th><th>Total</th><th>Cost</th><th>Cache</th><th>Status</th></tr></thead><tbody>${recent.map(row => `<tr><td>${new Date(row.created_at).toLocaleString()}</td><td><b>${esc(row.provider)}</b><small>${esc(row.model)}</small></td><td>${esc(row.api_key_id)}</td><td>${ms(row.latency_ms)}</td><td>${num(row.input_tokens)}</td><td>${num(row.output_tokens)}</td><td>${num(row.total_tokens)}</td><td>${usd(row.cost)}</td><td><span class="pill ${row.cached ? 'cached' : ''}">${row.cached ? 'Hit' : 'Miss'}</span></td><td><span class="pill ${row.success ? 'success' : 'failed'}">${row.success ? 'Success' : 'Failed'}</span></td></tr>`).join('')}</tbody></table></div></section>`;
  app.innerHTML = `<div class="shell"><aside><div class="logo"><i>S</i><span>SmartLLM</span></div><nav><a class="active">⌘ Overview</a><a>◫ Usage analytics</a><a>▤ Request activity</a></nav><div class="side-note"><b>Live data</b><span>Connected to your local API</span></div></aside><section class="content"><header><div><p class="eyebrow">ANALYTICS</p><h1>Dashboard</h1><p class="subtitle">Understand how your LLM gateway is performing.</p></div><button class="key-button" id="change-key">Admin key</button></header><div class="filters">${Object.entries(periods).map(([id, title]) => `<button data-period="${id}" class="${state.period === id ? 'selected' : ''}">${title}</button>`).join('')}</div>${screen}</section></div>`;
  document.querySelectorAll('[data-period]').forEach(button => button.addEventListener('click', () => { state.period = button.dataset.period; load(); }));
  document.querySelector('#change-key')?.addEventListener('click', () => { sessionStorage.removeItem('smartllm.adminKey'); state.key = ''; state.data = null; login(); });
  document.querySelector('#retry')?.addEventListener('click', load);
}
render(); if (state.key) load();
