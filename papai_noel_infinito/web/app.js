// Interface do Papai Noel infinito.
// Cada evento SSE traz o estado completo da simulação em C; a interface
// apenas desenha a última linha recebida e acumula o log e o gráfico.

const $ = (id) => document.getElementById(id);
const VELOCIDADES = [0.5, 1, 2, 4, 8, 16];
const ESTADO_ELFO = { T: "trabalhando", E: "esperando grupo", F: "na fila", A: "sendo ajudado" };
const ESTADO_RENA = { F: "férias", E: "estábulo", A: "atrelada", V: "viajando" };
const NOEL = {
  dormindo:   { rotulo: "Dormindo", det: "Esperando 9 renas ou um grupo de 3 elfos" },
  ajudando:   { rotulo: "Ajudando elfos", det: "" },
  preparando: { rotulo: "Atrelando o trenó", det: "As 9 renas estão sendo atreladas" },
  viajando:   { rotulo: "Entregando presentes", det: "Fora de casa: os elfos acumulam na fila" },
  encerrado:  { rotulo: "Encerrado", det: "A simulação terminou" },
};

let ultimo = null;          // último estado recebido
let rodando = false, pausado = false;
let esperas = [];           // [t, espera] para o gráfico
let viagemMs = 3000;
let ultimoT = 0, tRecebido = 0;
const MAX_LOG = 250, MAX_PONTOS = 300;

// ---------- utilidades ----------
function fmtMs(ms) {
  if (ms == null) return "—";
  return ms >= 1000 ? (ms / 1000).toFixed(2) + " s" : Math.round(ms) + " ms";
}
function fmtRelogio(ms) {
  const s = ms / 1000, m = Math.floor(s / 60);
  return String(m).padStart(2, "0") + ":" + (s - m * 60).toFixed(1).padStart(4, "0");
}
function setNum(id, valor) {
  const el = $(id), txt = String(valor);
  if (el.textContent !== txt) {
    el.textContent = txt;
    el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
  }
}
async function post(rota, corpo = {}) {
  const r = await fetch("/api/" + rota, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });
  return r.json();
}

// ---------- controles ----------
function lerParams() {
  const f = new FormData($("form-params"));
  const n = (k) => Number(f.get(k));
  viagemMs = n("viagem");
  return {
    elfos: n("elfos"), ajuda: n("ajuda"), preparo: n("preparo"), viagem: n("viagem"), semente: n("semente"),
    ferias: [n("ferias_min"), n("ferias_max")], trabalho: [n("trabalho_min"), n("trabalho_max")],
    velocidade: velAtual,
  };
}

let velAtual = 1;
function desenharVelocidades() {
  $("vel").innerHTML = "";
  for (const v of VELOCIDADES) {
    const b = document.createElement("button");
    b.textContent = v + "×";
    b.className = v === velAtual ? "ativo" : "";
    b.onclick = () => { velAtual = v; desenharVelocidades(); if (rodando) post("velocidade", { v }); };
    $("vel").appendChild(b);
  }
}

function iniciar() { return post("iniciar", lerParams()); }

$("btn-iniciar").onclick = iniciar;
$("btn-parar").onclick = () => post("parar");
$("btn-pausar").onclick = () => post(pausado ? "retomar" : "pausar");
$("form-params").onsubmit = (e) => { e.preventDefault(); iniciar(); };

document.querySelectorAll(".filtros input").forEach((cb) => (cb.onchange = aplicarFiltros));
function aplicarFiltros() {
  const vis = {};
  document.querySelectorAll(".filtros input").forEach((cb) => (vis[cb.dataset.f] = cb.checked));
  document.querySelectorAll("#log li").forEach((li) => li.classList.toggle("oculto", vis[li.dataset.q] === false));
}

// ---------- desenho ----------
function desenharStatus() {
  const pill = $("pill");
  pill.className = "pill " + (rodando ? (pausado ? "pausado" : "rodando") : "parado");
  pill.textContent = rodando ? (pausado ? "pausado" : "rodando") : "parado";
  $("btn-pausar").textContent = pausado ? "▶ Retomar" : "⏸ Pausar";
  $("btn-pausar").disabled = !rodando;
  $("btn-iniciar").textContent = rodando ? "↻ Reiniciar" : "▶ Iniciar";
}

function desenharElfos(s) {
  const box = $("elfos");
  const n = s.elfos.length;
  if (box.children.length !== n) {
    box.innerHTML = "";
    for (let i = 0; i < n; i++) {
      const d = document.createElement("div");
      d.innerHTML = `<span class="e">🧝</span><span class="n">#${i}</span><span class="g" hidden></span>`;
      box.appendChild(d);
    }
  }
  const cont = { T: 0, E: 0, F: 0, A: 0 };
  [...s.elfos].forEach((c, i) => {
    cont[c]++;
    const d = box.children[i];
    d.className = "elfo " + c;
    d.title = `Elfo ${i}: ${ESTADO_ELFO[c]}` + (s.grupo_do_elfo[i] ? ` (grupo ${s.grupo_do_elfo[i]})` : "");
    const g = d.querySelector(".g");
    g.hidden = c === "T";
    g.textContent = "G" + s.grupo_do_elfo[i];
  });
  $("cont-elfos").textContent = `${cont.T} trabalhando · ${n - cont.T} com Noel`;

  const slots = $("slots");
  slots.innerHTML = "";
  for (let k = 0; k < 3; k++) {
    const d = document.createElement("div");
    const m = s.aberto.m[k];
    d.className = "slot" + (m != null ? " cheio" : "");
    d.textContent = m != null ? "🧝 #" + m : "vago";
    slots.appendChild(d);
  }

  const fila = $("fila");
  fila.innerHTML = s.fila.length ? "" : '<span class="vazio">vazia</span>';
  for (const g of s.fila) {
    const c = document.createElement("span");
    c.className = "chip";
    c.textContent = `G${g.id}: ${g.m.join("·")}`;
    fila.appendChild(c);
  }
  $("fila-n").textContent = s.fila.length ? `(${s.fila.length} grupo${s.fila.length > 1 ? "s" : ""})` : "";
}

function desenharNoel(s) {
  const info = NOEL[s.noel] || NOEL.dormindo;
  $("noel").className = "noel " + s.noel;
  $("noel-estado").textContent = info.rotulo;
  const det = $("noel-detalhe");
  if (s.noel === "ajudando" && s.em_ajuda) {
    det.innerHTML = `Grupo ${s.em_ajuda.id}<br>` + s.em_ajuda.m.map((e) => `<span class="chip">🧝 #${e}</span>`).join(" ");
  } else {
    det.textContent = info.det;
  }
  const ceu = $("ceu");
  ceu.style.setProperty("--dur", Math.max(1.2, Math.min(8, viagemMs / 1000 / velAtual)) + "s");
  ceu.classList.toggle("voando", s.noel === "viajando");
}

function desenharRenas(s) {
  const box = $("renas");
  if (!box.children.length) {
    for (let i = 0; i < 9; i++) {
      const d = document.createElement("div");
      d.innerHTML = `<span class="e">🦌</span><span class="n">#${i}</span>`;
      box.appendChild(d);
    }
  }
  [...s.renas].forEach((c, i) => {
    box.children[i].className = "rena " + c;
    box.children[i].title = `Rena ${i}: ${ESTADO_RENA[c]}`;
  });
  const prontas = [...s.renas].filter((c) => c === "E").length;
  const txt = s.noel === "viajando" ? "viajando" : s.noel === "preparando" ? "atrelando" : `${prontas}/9`;
  $("cont-renas").textContent = txt;
  $("barra-renas").style.width = (s.noel === "preparando" || s.noel === "viajando" ? 100 : (prontas / 9) * 100) + "%";
}

function desenharMetricas(s) {
  const m = s.m;
  setNum("m-viagens", m.viagens);
  setNum("m-grupos", m.grupos);
  setNum("m-pedidos", m.pedidos);
  $("m-espera").textContent = m.grupos ? fmtMs(m.esp_med) : "—";
  $("m-espera-max").textContent = m.grupos ? "máx " + fmtMs(m.esp_max) : "média";
  $("m-resp").textContent = m.viagens ? fmtMs(m.resp_med) : "—";
  $("m-resp-max").textContent = m.viagens ? "máx " + fmtMs(m.resp_max) : "9ª rena → preparo";
  $("m-util").textContent = Math.round(m.util * 100) + "%";
  setNum("m-disp", m.disputas);
  setNum("m-viol", m.violacoes);
  $("m-viol").className = "v " + (m.violacoes ? "ruim" : "ok");
}

function registrarLog(ev) {
  if (!ev.msg) return;
  const li = document.createElement("li");
  li.className = "q-" + ev.quem;
  li.dataset.q = ev.quem;
  li.innerHTML = `<span class="t">${(ev.t / 1000).toFixed(1)}s</span><span class="m"></span>`;
  li.querySelector(".m").textContent = ev.msg;
  const cb = document.querySelector(`.filtros input[data-f="${ev.quem}"]`);
  if (cb && !cb.checked) li.classList.add("oculto");
  const log = $("log");
  const noTopo = log.scrollTop < 8;
  log.prepend(li);
  while (log.children.length > MAX_LOG) log.lastChild.remove();
  if (noTopo) log.scrollTop = 0;
}

// ---------- gráfico de esperas ----------
function desenharGrafico() {
  const cv = $("graf"), dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth, h = cv.clientHeight;
  if (cv.width !== w * dpr || cv.height !== h * dpr) { cv.width = w * dpr; cv.height = h * dpr; }
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  const css = getComputedStyle(document.documentElement);
  const cMuted = css.getPropertyValue("--muted").trim(), cLinha = css.getPropertyValue("--line").trim();
  const pad = { l: 46, r: 10, t: 10, b: 20 };
  $("graf-n").textContent = esperas.length ? `${esperas.length} elfos` : "";
  if (!esperas.length) {
    ctx.fillStyle = cMuted; ctx.font = "12px system-ui"; ctx.textAlign = "center";
    ctx.fillText("Aguardando o primeiro atendimento…", w / 2, h / 2);
    return;
  }
  const maxY = Math.max(500, ...esperas.map((p) => p[1])) * 1.1;
  const t0 = esperas[0][0], t1 = Math.max(esperas[esperas.length - 1][0], t0 + 1);
  const X = (t) => pad.l + ((t - t0) / (t1 - t0)) * (w - pad.l - pad.r);
  const Y = (v) => h - pad.b - (v / maxY) * (h - pad.t - pad.b);

  ctx.font = "11px ui-monospace, monospace"; ctx.textAlign = "right"; ctx.textBaseline = "middle";
  for (let i = 0; i <= 4; i++) {
    const v = (maxY / 4) * i, y = Y(v);
    ctx.strokeStyle = cLinha; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
    ctx.fillStyle = cMuted; ctx.fillText(v >= 1000 ? (v / 1000).toFixed(1) + "s" : Math.round(v) + "ms", pad.l - 6, y);
  }
  const media = esperas.reduce((a, p) => a + p[1], 0) / esperas.length;
  ctx.setLineDash([4, 4]); ctx.strokeStyle = "#f5a524"; ctx.beginPath(); ctx.moveTo(pad.l, Y(media)); ctx.lineTo(w - pad.r, Y(media)); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = "#f5a524"; ctx.textAlign = "left"; ctx.fillText("média " + fmtMs(media), pad.l + 4, Y(media) - 8);

  ctx.fillStyle = "#38bdf8";
  for (const [t, v] of esperas) { ctx.beginPath(); ctx.arc(X(t), Y(v), 2.6, 0, Math.PI * 2); ctx.fill(); }
}
window.addEventListener("resize", desenharGrafico);

// ---------- eventos ----------
function processar(ev) {
  if (ev.ev === "reinicio") {
    esperas = []; $("log").innerHTML = ""; $("elfos").innerHTML = "";
    desenharGrafico();
    return;
  }
  if (ev.ev === "processo_terminou") {
    rodando = false; pausado = false; desenharStatus();
    return;
  }
  ultimo = ev;
  rodando = ev.noel !== "encerrado";
  pausado = !!ev.ctl.pausado;
  ultimoT = ev.t; tRecebido = performance.now();
  if (ev.ctl.vel && ev.ctl.vel !== velAtual) { velAtual = ev.ctl.vel; desenharVelocidades(); }

  if (ev.ev === "inicio_ajuda") {
    for (const e of ev.m.esperas) esperas.push([ev.t, e]);
    if (esperas.length > MAX_PONTOS) esperas.splice(0, esperas.length - MAX_PONTOS);
    desenharGrafico();
  }
  registrarLog(ev);
  desenharStatus();
  desenharElfos(ev);
  desenharNoel(ev);
  desenharRenas(ev);
  desenharMetricas(ev);
}

// Relógio suave entre eventos (interpolado; o valor oficial vem do C).
function tique() {
  if (ultimo) {
    const t = rodando && !pausado ? ultimoT + (performance.now() - tRecebido) * velAtual : ultimoT;
    $("relogio").textContent = fmtRelogio(t);
  }
  requestAnimationFrame(tique);
}

async function conectar() {
  // Sem simulação em andamento, inicia uma com os parâmetros padrão.
  try {
    const r = await (await fetch("/api/estado")).json();
    if (!r.rodando) await iniciar();
  } catch (e) { /* servidor fora do ar: o EventSource tenta de novo */ }
  const es = new EventSource("/api/eventos");
  es.onopen = () => { if (!ultimo) $("pill").textContent = "conectado"; };
  es.onmessage = (m) => processar(JSON.parse(m.data));
  es.onerror = () => { rodando = false; desenharStatus(); $("pill").textContent = "desconectado"; };
}

// ---------- neve ----------
(function neve() {
  const cv = $("neve"), ctx = cv.getContext("2d");
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  let flocos = [];
  function tamanho() {
    cv.width = innerWidth; cv.height = innerHeight;
    flocos = Array.from({ length: Math.round(innerWidth / 14) }, () => ({
      x: Math.random() * innerWidth, y: Math.random() * innerHeight,
      r: Math.random() * 1.8 + .4, v: Math.random() * .5 + .2, d: Math.random() * 2 * Math.PI,
    }));
  }
  tamanho(); addEventListener("resize", tamanho);
  (function cair() {
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.fillStyle = "rgba(255,255,255,.55)";
    for (const f of flocos) {
      f.y += f.v; f.d += .01; f.x += Math.sin(f.d) * .3;
      if (f.y > cv.height) { f.y = -4; f.x = Math.random() * cv.width; }
      ctx.beginPath(); ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2); ctx.fill();
    }
    requestAnimationFrame(cair);
  })();
})();

desenharVelocidades();
desenharStatus();
desenharGrafico();
conectar();
tique();
