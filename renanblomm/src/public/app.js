// Interface web do SentinelTrade. Conversa SOMENTE com o BFF (/api/...).
const $ = (s) => document.querySelector(s);
const brl = (v) => Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const hora = (iso) => new Date(iso).toLocaleTimeString('pt-BR');
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

let token = sessionStorage.getItem('token');
let desafioId = null;
let atualizador = null;
let ultimoEnvio = null;

async function api(metodo, caminho, corpo) {
  const r = await fetch(caminho, {
    method: metodo,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  const json = await r.json().catch(() => ({}));
  if (r.status === 401 && token) { sair(); }
  if (!r.ok) throw new Error(json.erro || `Erro ${r.status}`);
  return json;
}

function mostrar(...ids) {
  ['#tela-login', '#tela-mfa', '#tela-investidor', '#tela-operador', '#tela-auditoria'].forEach((id) => $(id).classList.toggle('oculto', !ids.includes(id)));
}

function novoClientOrderId() { $('#inp-coid').value = 'ORD-' + crypto.randomUUID().slice(0, 8).toUpperCase(); }

// ---------- Login + MFA ----------
$('#form-login').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const r = await api('POST', '/api/login', Object.fromEntries(new FormData(e.target)));
    desafioId = r.desafioId;
    mostrar('#tela-mfa');
    $('#form-mfa [name=codigo]').focus();
  } catch (err) { alerta(err.message); }
});

$('#form-mfa').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const r = await api('POST', '/api/mfa', { desafioId, codigo: e.target.codigo.value });
    token = r.token;
    sessionStorage.setItem('token', token);
    e.target.reset();
    iniciarPainel();
  } catch (err) { alerta(err.message); }
});

function alerta(msg) { const p = document.createElement('p'); p.className = 'msg erro'; p.textContent = msg; const alvo = $('#tela-mfa').classList.contains('oculto') ? '#tela-login' : '#tela-mfa'; $(alvo).querySelectorAll('.msg').forEach((x) => x.remove()); $(alvo).appendChild(p); }

async function sair() {
  try { if (token) await fetch('/api/logout', { method: 'POST', headers: { Authorization: `Bearer ${token}` } }); } catch {}
  token = null; sessionStorage.removeItem('token'); clearInterval(atualizador);
  $('#topo-usuario').classList.add('oculto');
  mostrar('#tela-login');
}
$('#btn-sair').addEventListener('click', sair);

// ---------- Painel ----------
async function iniciarPainel() {
  try {
    const p = await api('GET', '/api/painel');
    $('#topo-usuario').classList.remove('oculto');
    $('#nome-usuario').textContent = `${p.usuario.nome} · ${p.usuario.perfil.replace('_', ' ')}`;
    if (p.usuario.perfil === 'INVESTIDOR') { mostrar('#tela-investidor'); novoClientOrderId(); }
    if (p.usuario.perfil === 'ANALISTA_RISCO') mostrar('#tela-operador', '#tela-auditoria');
    if (p.usuario.perfil === 'AUDITOR') mostrar('#tela-auditoria');
    render(p);
    clearInterval(atualizador);
    atualizador = setInterval(atualizar, 2000);
  } catch { sair(); }
}

async function atualizar() {
  try { render(await api('GET', '/api/painel')); } catch { /* sessão tratada em api() */ }
}

function render(p) {
  if (p.usuario.perfil === 'INVESTIDOR') renderInvestidor(p);
  if (p.usuario.perfil === 'ANALISTA_RISCO') renderOperador(p);
  if (p.usuario.perfil !== 'INVESTIDOR') carregarAuditoria();
}

function renderInvestidor(p) {
  $('#k-disp').textContent = brl(p.conta.saldoDisponivel);
  $('#k-bloq').textContent = brl(p.conta.saldoBloqueado);
  $('#k-lim').textContent = brl(p.conta.limiteRestante);
  $('#k-merc').textContent = p.mercado.estado;
  $('#k-merc').className = p.mercado.estado === 'ABERTO' ? 'pos' : 'neg';

  const sel = $('#sel-ativo');
  if (!sel.options.length) sel.innerHTML = p.cotacoes.map((c) => `<option>${esc(c.ativo)}</option>`).join('');
  $('#tb-cot').innerHTML = p.cotacoes.map((c) => `<tr><td>${esc(c.ativo)}</td><td class="num">${brl(c.preco)}</td><td class="num ${c.variacaoDia >= 0 ? 'pos' : 'neg'}">${c.variacaoDia.toFixed(2)}%</td></tr>`).join('');
  $('#cot-hora').textContent = p.cotacoes[0] ? `atualizado ${hora(p.cotacoes[0].atualizadoEm)}` : '';
  $('#tb-cart').innerHTML = p.conta.custodia.map((c) => `<tr><td>${esc(c.ativo)}</td><td class="num">${c.quantidade}</td><td class="num">${c.bloqueada}</td><td class="num">${c.livre}</td></tr>`).join('') || '<tr><td colspan="4">Sem ativos</td></tr>';
  $('#tb-ordens').innerHTML = p.ordens.map((o) => `<tr>
      <td>${hora(o.criadaEm)}</td><td>${esc(o.ativo)}</td><td>${esc(o.lado)}</td><td>${esc(o.tipo)}</td><td class="num">${o.quantidade}</td>
      <td class="num">${o.precoExecucao ? brl(o.precoExecucao) : o.precoLimite ? 'lim. ' + brl(o.precoLimite) : '-'}</td>
      <td><span class="estado ${esc(o.estado)}">${esc(o.estado)}</span></td><td>${esc(o.motivo || '')}</td>
      <td>${o.podeCancelar ? `<button class="mini" data-cancelar="${esc(o.id)}">Cancelar</button>` : ''}</td></tr>`).join('') || '<tr><td colspan="9">Nenhuma ordem ainda</td></tr>';
  $('#lista-notif').innerHTML = p.notificacoes.map((n) => `<li>${esc(n.mensagem)}<small>${hora(n.em)}</small></li>`).join('') || '<li><small>Sem notificações</small></li>';
}

$('#sel-tipo').addEventListener('change', (e) => { $('#form-ordem [name=precoLimite]').disabled = e.target.value !== 'LIMITADA'; });

async function enviarOrdem(dados) {
  const msg = $('#msg-ordem');
  try {
    const r = await api('POST', '/api/ordens', dados);
    if (r.duplicada) { msg.className = 'msg aviso'; msg.textContent = `Pedido duplicado descartado (ClientOrderId ${dados.clientOrderId}). Estado da ordem original: ${r.ordem.estado}`; }
    else if (r.ordem.estado === 'REJEITADA') { msg.className = 'msg erro'; msg.textContent = `Ordem rejeitada: ${r.ordem.motivo}`; }
    else { msg.className = 'msg ok'; msg.textContent = `Ordem ${r.ordem.estado} · validação de risco em ${r.ordem.latenciaRiscoMs.toFixed(2)} ms`; }
    atualizar();
  } catch (err) { msg.className = 'msg erro'; msg.textContent = err.message; }
}

$('#form-ordem').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const dados = Object.fromEntries(f);
  dados.quantidade = Number(dados.quantidade);
  ultimoEnvio = dados;
  await enviarOrdem(dados);
  novoClientOrderId();
});

$('#btn-reenviar').addEventListener('click', () => {
  if (!ultimoEnvio) { $('#msg-ordem').className = 'msg aviso'; $('#msg-ordem').textContent = 'Envie uma ordem primeiro.'; return; }
  enviarOrdem(ultimoEnvio);
});

$('#tb-ordens').addEventListener('click', async (e) => {
  const id = e.target.dataset.cancelar;
  if (!id) return;
  try { await api('POST', `/api/ordens/${id}/cancelar`); atualizar(); }
  catch (err) { $('#msg-ordem').className = 'msg erro'; $('#msg-ordem').textContent = err.message; }
});

// ---------- Operador de risco ----------
function renderOperador(p) {
  $('#op-merc').textContent = `${p.mercado.estado} (circuit breaker da bolsa: ${p.mercado.circuitBreakerBolsa})`;
  const sel = $('#sel-inv');
  if (!sel.options.length) sel.innerHTML = p.investidores.map((i) => `<option>${esc(i.usuario)}</option>`).join('');
  $('#tb-inv').innerHTML = p.investidores.map((i) => `<tr><td>${esc(i.usuario)}</td><td class="num">${brl(i.saldoDisponivel)}</td><td class="num">${brl(i.operadoHoje)}</td><td class="num">${brl(i.limiteDiario)}</td></tr>`).join('');
  $('#tb-fluxo').innerHTML = p.ordens.map((o) => `<tr><td>${hora(o.criadaEm)}</td><td>${esc(o.usuario)}</td><td>${esc(o.ativo)}</td><td>${esc(o.lado)}</td><td class="num">${o.quantidade}</td><td><span class="estado ${esc(o.estado)}">${esc(o.estado)}</span></td><td class="num">${o.latenciaRiscoMs != null ? o.latenciaRiscoMs.toFixed(2) : '-'}</td></tr>`).join('') || '<tr><td colspan="7">Sem ordens</td></tr>';
}

document.querySelectorAll('[data-merc]').forEach((b) => b.addEventListener('click', async () => {
  try { await api('PUT', '/api/operador/mercado', { estado: b.dataset.merc }); atualizar(); } catch (err) { $('#msg-limite').className = 'msg erro'; $('#msg-limite').textContent = err.message; }
}));

$('#form-limite').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    await api('PUT', '/api/operador/limite', Object.fromEntries(new FormData(e.target)));
    $('#msg-limite').className = 'msg ok'; $('#msg-limite').textContent = 'Limite atualizado.';
    atualizar();
  } catch (err) { $('#msg-limite').className = 'msg erro'; $('#msg-limite').textContent = err.message; }
});

// ---------- Auditoria ----------
async function carregarAuditoria() {
  try {
    const a = await api('GET', '/api/auditoria');
    const selo = $('#aud-integ');
    selo.className = 'selo ' + (a.integridade.integro ? 'ok' : 'falha');
    selo.textContent = a.integridade.integro ? `Cadeia íntegra · ${a.integridade.total} registros` : `Cadeia ADULTERADA no registro ${a.integridade.falhaNoRegistro}`;
    $('#tb-aud').innerHTML = a.registros.slice(0, 60).map((r) => `<tr><td>${r.seq}</td><td><code>${esc(r.timestamp)}</code></td><td>${esc(r.tipo)}</td><td>${esc(r.usuario)}</td><td><code>${esc(JSON.stringify(r.dados))}</code></td><td><code>${esc(r.hash.slice(0, 12))}…</code></td></tr>`).join('');
  } catch { /* sem permissão */ }
}

// sessão ainda válida ao recarregar a página
if (token) iniciarPainel(); else mostrar('#tela-login');
