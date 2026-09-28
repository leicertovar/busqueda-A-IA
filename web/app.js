"use strict";

const D = window.DATOS;
if (!D) {
  document.body.innerHTML =
    "<p style='padding:2em;font-size:18px'>No se encontró <b>datos.js</b>. Ejecuta <code>python main.py --web</code>.</p>";
  throw new Error("Falta datos.js");
}

const T = D.traza;
const TOTAL = T.length - 1;
const TAB = D.tablero;
const META = D.meta;
const NS = "http://www.w3.org/2000/svg";
const $ = (id) => document.getElementById(id);
const k = (p) => p[0] + "," + p[1];
const fmt = (x) => (x === null || x === undefined ? "∞" : Number.isInteger(x) ? String(x) : x.toFixed(1));
const fpos = (p) => `(${p[0]},${p[1]})`;

const NOMBRE = { 1: "Libre", 2: "Escombros leves", 4: "Grietas / Humo", 7: "Fuego parcial / Agua",
                 B: "Bombero (inicio)", S: "Superviviente (meta)", X: "Bloqueado" };
const ICONO = { 2: "escombros", 4: "grietas", 7: "fuego", B: "bombero", S: "superviviente", X: "bloqueado" };
const C = { azul: "#3b82f6", azulClaro: "#7cb4ff", magenta: "#e879f9", verde: "#22c55e",
            ambar: "#f59e0b", rojo: "#ef4444", gris: "#94a3b8", pizarra: "#64748b" };
const VELS = [0.25, 0.5, 0.75, 1, 1.5, 2, 3];
const SUAVE = "cubic-bezier(.22,1,.36,1)";
const REBOTE = "cubic-bezier(.34,1.56,.64,1)";
const SUB_BASE = $("sub").innerHTML;

let i = 0, vel = 1, jugando = false, arbol = true, cs = 80;
let tPlay = null, gen = 0;
let anims = [], pendientes = [];

// ------------------------------------------------------------------ estado de cada celda en cada iteración
const E = [];
{
  const conocidos = {};
  for (const e of T) {
    if (e.actual) conocidos[k(e.actual.pos)] = { ...e.actual };
    for (const n of e.abierta) conocidos[k(n.pos)] = { ...n };
    const orden = {};
    e.cerrada.forEach((p, j) => (orden[k(p)] = j + 1));
    const abiertos = new Set(e.abierta.map((n) => k(n.pos)));
    const est = {};
    for (const [kk, n] of Object.entries(conocidos)) {
      est[kk] = { ...n, estado: orden[kk] ? "cerrada" : abiertos.has(kk) ? "abierta" : "?", orden: orden[kk] || null };
    }
    E.push(est);
  }
}

function tipo(accion) {
  if (accion.startsWith("NUEVO")) return ["NUEVO", C.azul];
  if (accion.startsWith("MEJOR")) return ["MEJORA g", C.ambar];
  if (accion.startsWith("BLOQ")) return ["BLOQUEADO", C.rojo];
  if (accion.startsWith("En lista cerrada")) return ["EN CERRADA", C.pizarra];
  return ["SIN CAMBIO", "#475569"];
}

// ------------------------------------------------------------------ utilidades de animación
const ms = (s) => (s / vel) * 1000;

function A(el, frames, dur, delay = 0, easing = SUAVE, fill = "backwards") {
  const a = el.animate(frames, { duration: ms(dur), delay: ms(delay), easing, fill });
  anims.push(a);
  return a;
}

function despues(s, fn) {
  pendientes.push(setTimeout(fn, ms(s)));
}

function cortar() {
  gen++;
  anims.forEach((a) => a.cancel());
  pendientes.forEach(clearTimeout);
  anims = [];
  pendientes = [];
  $("gHaz").replaceChildren();
}

function svg(tag, attrs) {
  const el = document.createElementNS(NS, tag);
  for (const [a, v] of Object.entries(attrs)) el.setAttribute(a, v);
  return el;
}

const marcas = new Set();
function marca(color) {
  const id = "m" + color.slice(1);
  if (!marcas.has(id)) {
    const m = svg("marker", { id, viewBox: "0 0 10 10", refX: 6, refY: 5, markerWidth: 3.2, markerHeight: 3.2, orient: "auto" });
    m.appendChild(svg("path", { d: "M0 0 L10 5 L0 10z", fill: color }));
    $("capa").appendChild(m);
    marcas.add(id);
  }
  return `url(#${id})`;
}

const trans = (p) => `translate(${p[1] * cs}px, ${p[0] * cs}px)`;
const transFicha = (p) => `translate(${p[1] * cs + cs * 0.19}px, ${p[0] * cs + cs * 0.19}px)`;

// ------------------------------------------------------------------ construcción del tablero
const celdas = {};
function construir() {
  const tb = $("tablero");
  for (let f = 0; f < 8; f++) {
    $("etqCol").insertAdjacentHTML("beforeend", `<span>${f}</span>`);
    $("etqFil").insertAdjacentHTML("beforeend", `<span>${f}</span>`);
    for (let c = 0; c < 8; c++) {
      const v = TAB[f][c];
      const el = document.createElement("div");
      el.className = `celda t-${v}`;
      const ico = ICONO[v] ? `<svg class="ico" viewBox="0 0 100 100"><use href="#ico-${ICONO[v]}"/></svg>` : "";
      const etiqueta = v === "B" ? "B · 1" : v === "S" ? "S · 1" : `c=${v}`;
      el.innerHTML =
        `<div class="caja">${ico}<div class="tinte"></div><div class="verde"></div>` +
        (v === "X" ? "" :
          `<span class="coste">${etiqueta}</span><span class="orden"></span>` +
          `<div class="valores"><span class="gh"></span><span class="fv"></span></div>`) +
        `</div><div class="anillo"></div><div class="destello"></div>`;
      tb.insertBefore(el, $("capa"));
      const q = (s) => el.querySelector(s);
      celdas[k([f, c])] = { el, v, ico: q(".ico"), tinte: q(".tinte"), verde: q(".verde"), anillo: q(".anillo"),
                            destello: q(".destello"), valores: q(".valores"), gh: q(".gh"), fv: q(".fv"), orden: q(".orden") };
    }
  }
  const puntos = $("puntos");
  for (let j = 0; j <= TOTAL; j++) {
    const p = document.createElement("div");
    p.className = "punto";
    p.style.left = `${(j / Math.max(TOTAL, 1)) * 100}%`;
    puntos.appendChild(p);
  }
}

// ------------------------------------------------------------------ render estático de la iteración idx
function render(idx, conPanel = true) {
  const e = T[idx], est = E[idx];
  const final = idx === TOTAL && D.encontrado;
  const camino = new Set(final ? D.camino.map(k) : []);

  for (const [kk, c] of Object.entries(celdas)) {
    if (c.v === "X") continue;
    const n = est[kk];
    c.el.classList.toggle("conocida", !!n);
    c.el.classList.toggle("cerrada", n?.estado === "cerrada");
    c.el.classList.toggle("abierta", n?.estado === "abierta");
    c.el.classList.toggle("ruta", camino.has(kk));
    c.gh.textContent = n ? `g=${fmt(n.g)} h=${n.h}` : "";
    c.fv.textContent = n ? `f=${fmt(n.f)}` : "";
    c.orden.textContent = n?.orden ? `#${n.orden}` : "";
  }

  const sel = $("selector");
  sel.style.display = e.actual ? "block" : "none";
  if (e.actual) sel.style.transform = trans(e.actual.pos);

  dibujarArbol(est);
  $("gRuta").replaceChildren();
  const ficha = $("ficha");
  if (final) {
    dibujarRuta();
    ficha.style.display = "block";
    ficha.style.transform = transFicha(META);
  } else {
    ficha.style.display = "none";
  }
  if (conPanel) panel(idx);
  timeline();
}

function dibujarArbol(est, nuevos) {
  const g = $("gArbol");
  g.replaceChildren();
  if (!arbol) return;
  const off = 0.42;
  for (const [kk, n] of Object.entries(est)) {
    if (!n.padre) continue;
    const [f0, c0] = n.padre, [f1, c1] = n.pos;
    const df = f1 - f0, dc = c1 - c0;
    const a = df
      ? { x1: c0 + 0.83, y1: f0 + 0.5 + df * off, x2: c0 + 0.83, y2: f1 + 0.5 - df * off }
      : { x1: c0 + 0.5 + dc * off, y1: f0 + 0.32, x2: c1 + 0.5 - dc * off, y2: f0 + 0.32 };
    const l = svg("line", { ...a, stroke: "#475a7a", "stroke-width": 0.035, "stroke-linecap": "round", "marker-end": marca("#475a7a") });
    g.appendChild(l);
    if (nuevos && nuevos.has(kk)) A(l, [{ opacity: 0 }, { opacity: 1 }], 0.3, nuevos.get(kk));
  }
}

function dibujarRuta() {
  const pts = D.camino.map((p) => `${p[1] + 0.5},${p[0] + 0.5}`).join(" ");
  const pl = svg("polyline", { points: pts, fill: "none", stroke: "#bbf7d0", "stroke-width": 0.045,
                               "stroke-linecap": "round", "stroke-linejoin": "round", opacity: 0.55, pathLength: 1 });
  $("gRuta").appendChild(pl);
  return pl;
}

// ------------------------------------------------------------------ panel derecho
function setStat(id, valor, animar) {
  const el = $("s-" + id);
  const desde = Number(el.dataset.v || 0);
  el.dataset.v = valor;
  const f = (v) => (id === "it" ? `${Math.round(v)} / ${TOTAL}` : String(Math.round(v)));
  if (!animar || desde === valor) { el.textContent = f(valor); return; }
  const g = gen, t0 = performance.now(), dur = ms(0.5);
  const tick = (t) => {
    if (g !== gen) return;
    const x = Math.max(0, Math.min(1, (t - t0) / dur));
    el.textContent = f(desde + (valor - desde) * (1 - (1 - x) ** 3));
    if (x < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  pendientes.push(setTimeout(() => { if (g === gen) el.textContent = f(valor); }, dur + 50));
}

function panel(idx, animar = false, retrasos = []) {
  const e = T[idx];
  for (const [id, v] of [["it", e.iteracion], ["cre", e.creados], ["exp", e.expandidos],
                         ["ab", e.abierta.length], ["ce", e.cerrada.length], ["act", e.actualizados]]) {
    setStat(id, v, animar);
  }

  const nPos = $("nPos"), nVals = $("nVals");
  if (e.actual) {
    const a = e.actual;
    nPos.textContent = fpos(a.pos);
    nPos.style.color = e.es_meta ? C.verde : C.magenta;
    nVals.innerHTML = `g = ${fmt(a.g)} &nbsp; h = ${a.h} &nbsp; f = ${fmt(a.f)}<br>padre: ${a.padre ? fpos(a.padre) : "—"}`;
    if (animar) A(nPos, [{ opacity: 0, transform: "translateY(6px)" }, { opacity: 1, transform: "none" }], 0.4);
  } else {
    nPos.textContent = fpos(D.inicio);
    nPos.style.color = C.azulClaro;
    nVals.innerHTML = `Inicialización: g = 0 &nbsp; h = ${e.abierta[0].h}<br>en lista abierta`;
  }

  const tv = $("vecinos");
  tv.replaceChildren();
  if (e.es_meta) {
    tv.innerHTML = `<tr><td class="fin-msg" colspan="5">Meta alcanzada: fin de la búsqueda</td></tr>`;
  }
  e.vecinos.forEach((v, j) => {
    const [tp, col] = tipo(v.accion);
    const tr = document.createElement("tr");
    tr.title = v.accion;
    tr.innerHTML = `<td>${v.dir}</td><td>${fpos(v.pos)}</td><td>c=${fmt(v.coste_paso)}</td>` +
                   `<td>f=${v.f === null ? "–" : fmt(v.f)}</td><td><span class="badge" style="background:${col}">${tp}</span></td>`;
    tv.appendChild(tr);
    if (animar) A(tr, [{ opacity: 0, transform: "translateX(-10px)" }, { opacity: 1, transform: "none" }], 0.3, retrasos[j] || 0);
  });

  const retrasoDe = new Map();
  e.vecinos.forEach((v, j) => retrasoDe.set(k(v.pos), retrasos[j] || 0));
  const nuevos = new Set(e.vecinos.filter((v) => v.accion.startsWith("NUEVO")).map((v) => k(v.pos)));
  const mejorados = new Set(e.vecinos.filter((v) => v.accion.startsWith("MEJOR")).map((v) => k(v.pos)));
  const tb = $("tAbierta");
  tb.replaceChildren();
  e.abierta.forEach((n, j) => {
    const kk = k(n.pos);
    const tr = document.createElement("tr");
    if (j === 0 && !e.es_meta) tr.className = "siguiente";
    else if (mejorados.has(kk)) tr.className = "mejora";
    else if (nuevos.has(kk)) tr.className = "nuevo";
    tr.innerHTML = `<td>${fpos(n.pos)}</td><td>${fmt(n.g)}</td><td>${n.h}</td><td>${fmt(n.f)}</td><td>${n.padre ? fpos(n.padre) : "—"}</td>`;
    tb.appendChild(tr);
    if (animar && (nuevos.has(kk) || mejorados.has(kk))) {
      A(tr, [{ opacity: 0, transform: "translateX(-12px)" }, { opacity: 1, transform: "none" }], 0.35, retrasoDe.get(kk));
    }
  });

  const ce = $("cerrada");
  ce.replaceChildren();
  e.cerrada.forEach((p, j) => {
    const s = document.createElement("span");
    const ultimo = j === e.cerrada.length - 1;
    s.className = "chip" + (ultimo ? (e.es_meta ? " meta" : " ultimo") : "");
    s.textContent = fpos(p);
    ce.appendChild(s);
    if (ultimo && animar) A(s, [{ opacity: 0, transform: "scale(.5)" }, { opacity: 1, transform: "scale(1)" }], 0.35, 0.45, REBOTE);
  });
  ce.scrollTop = ce.scrollHeight;

  const sub = $("sub");
  if (idx === TOTAL && D.encontrado) {
    sub.textContent = `✔ Superviviente rescatado · coste total ${fmt(D.coste)} · ${D.camino.length - 1} movimientos`;
    sub.classList.add("ok");
  } else {
    sub.innerHTML = SUB_BASE;
    sub.classList.remove("ok");
  }
  mensaje();
}

function mensaje(texto) {
  const e = T[i];
  $("estado").textContent = texto ?? `Iteración ${e.iteracion}:  ${e.mensaje}`;
}

function timeline() {
  const x = (i / Math.max(TOTAL, 1)) * 100;
  $("progreso").style.width = x + "%";
  const per = $("perilla");
  per.style.left = x + "%";
  per.classList.toggle("fin", i === TOTAL);
  document.querySelectorAll(".punto").forEach((p, j) => p.classList.toggle("on", j <= i));
}

// ------------------------------------------------------------------ paso animado i -> i+1
function destello(c, color, delay) {
  c.destello.style.borderColor = color;
  A(c.destello, [{ opacity: 1, transform: "scale(1)" }, { opacity: 0, transform: "scale(1.22)" }], 0.45, delay, SUAVE, "none");
}

function haz(a, b, color, t0) {
  const dx = b[1] - a[1], dy = b[0] - a[0], s = 0.28;
  const l = svg("line", {
    x1: a[1] + 0.5 + dx * s, y1: a[0] + 0.5 + dy * s, x2: b[1] + 0.5 - dx * s, y2: b[0] + 0.5 - dy * s,
    stroke: color, "stroke-width": 0.07, "stroke-linecap": "round", "marker-end": marca(color),
    pathLength: 1, "stroke-dasharray": 1, "stroke-dashoffset": 1, opacity: 0,
  });
  $("gHaz").appendChild(l);
  A(l, [{ strokeDashoffset: 1, opacity: 1 }, { strokeDashoffset: 0, opacity: 1 }], 0.2, t0, SUAVE, "forwards");
  A(l, [{ opacity: 1 }, { opacity: 0 }], 0.35, t0 + 0.55, "linear", "forwards");
  despues(t0 + 1, () => l.remove());
}

function paso() {
  cortar();
  if (i >= TOTAL) return 0;
  const selAntes = $("selector").style.display === "none" ? null : $("selector").style.transform;
  i += 1;
  const e = T[i];
  const act = e.actual.pos, ca = celdas[k(act)];

  const ini = 0.55, esc = 0.2;
  const retrasos = e.vecinos.map((_, j) => ini + j * esc + 0.15);
  render(i, false);
  panel(i, true, retrasos);

  // 1. el selector se desliza hasta el nodo de menor f
  if (selAntes) A($("selector"), [{ transform: selAntes }, { transform: trans(act) }], 0.3, 0, "cubic-bezier(.65,0,.35,1)");
  else A($("selector"), [{ opacity: 0, transform: trans(act) + " scale(1.3)" }, { opacity: 1, transform: trans(act) }], 0.3);

  // 2. el nodo pasa de la lista abierta a la cerrada
  A(ca.tinte, [{ opacity: 0 }, { opacity: 0.8 }], 0.35, 0.2);
  A(ca.anillo, [{ opacity: 1, transform: "scale(1)" }, { opacity: 0, transform: "scale(.85)" }], 0.35, 0.2);
  if (ca.orden) A(ca.orden, [{ transform: "scale(0)" }, { transform: "scale(1)" }], 0.35, 0.45, REBOTE);

  // 3. evaluación de los vecinos
  const nuevasAristas = new Map();
  e.vecinos.forEach((v, j) => {
    const t0 = ini + j * esc, tr = retrasos[j];
    const [tp, col] = tipo(v.accion);
    const c = celdas[k(v.pos)];
    haz(act, v.pos, col, t0);
    if (tp === "NUEVO") {
      A(c.valores, [{ opacity: 0, transform: "scale(.5)" }, { opacity: 1, transform: "scale(1)" }], 0.45, tr, REBOTE);
      A(c.anillo, [{ opacity: 0, transform: "scale(.4)" }, { opacity: 1, transform: "scale(1)" }], 0.45, tr, REBOTE);
      if (c.ico) A(c.ico, [{ opacity: 0.92 }, { opacity: 0.2 }], 0.4, tr);
      destello(c, C.azulClaro, tr);
      nuevasAristas.set(k(v.pos), tr);
    } else if (tp === "MEJORA g") {
      A(c.valores, [{ opacity: 1 }, { opacity: 0 }, { opacity: 1 }], 0.5, tr, "linear");
      destello(c, C.ambar, tr);
      nuevasAristas.set(k(v.pos), tr);
    } else {
      destello(c, tp === "BLOQUEADO" ? C.rojo : C.gris, tr);
    }
  });
  dibujarArbol(E[i], nuevasAristas);

  let fin = ini + e.vecinos.length * esc + 0.45;
  if (e.es_meta) fin = animarRuta(0.6);
  return fin;
}

function animarRuta(t) {
  const cam = D.camino, seg = 0.17, dur = (cam.length - 1) * seg;
  const pl = $("gRuta").firstChild;
  A(pl, [{ strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDasharray: 1, strokeDashoffset: 0 }], dur, t, "linear");
  const ficha = $("ficha");
  A(ficha, [{ opacity: 0, transform: transFicha(cam[0]) + " scale(.3)" }, { opacity: 1, transform: transFicha(cam[0]) }], 0.3, t - 0.3, REBOTE);
  A(ficha, cam.map((p) => ({ transform: transFicha(p) })), dur, t, "linear");
  cam.forEach((p, j) => A(celdas[k(p)].verde, [{ opacity: 0 }, { opacity: 0.72 }], 0.3, t + j * seg));
  const m = celdas[k(META)];
  destello(m, C.verde, t + dur);
  A(ficha, [{ transform: transFicha(META) }, { transform: transFicha(META) + " scale(1.25)" }, { transform: transFicha(META) }],
    0.5, t + dur, SUAVE, "none");
  confeti(t + dur);
  return t + dur + 1.0;
}

function confeti(t) {
  const colores = [C.verde, C.ambar, C.azulClaro, C.magenta, "#f8fafc"];
  const cx = META[1] + 0.5, cy = META[0] + 0.5;
  for (let j = 0; j < 22; j++) {
    const ang = (j / 22) * Math.PI * 2 + Math.random() * 0.3;
    const r = 0.7 + Math.random() * 0.9;
    const p = svg("circle", { cx, cy, r: 0.05 + Math.random() * 0.04, fill: colores[j % colores.length], opacity: 0 });
    $("gHaz").appendChild(p);
    const dx = Math.cos(ang) * r, dy = Math.sin(ang) * r;
    A(p, [{ opacity: 1, transform: "translate(0,0)" }, { opacity: 0, transform: `translate(${dx}px, ${dy}px)` }],
      0.9, t, "cubic-bezier(.2,.8,.3,1)", "none");
  }
}

// ------------------------------------------------------------------ navegación
function ir(n) {
  cortar();
  i = Math.max(0, Math.min(TOTAL, n));
  render(i);
}
function siguiente() { pausar(); paso(); }
function anterior() { pausar(); ir(i - 1); }

function pausar() {
  jugando = false;
  clearTimeout(tPlay);
  $("bPlay").textContent = "▶ Reproducir";
}
function alternar() {
  if (jugando) return pausar();
  jugando = true;
  $("bPlay").textContent = "❚❚ Pausa";
  if (i >= TOTAL) ir(0);
  jugar();
}
function jugar() {
  if (!jugando) return;
  if (i >= TOTAL) return pausar();
  const d = paso();
  tPlay = setTimeout(jugar, ms(d + 0.25));
}

function cambiarVel(signo) {
  const j = VELS.indexOf(vel);
  vel = VELS[Math.max(0, Math.min(VELS.length - 1, j + signo))];
  $("vLbl").textContent = `${vel}×`;
}
function alternarArbol() {
  arbol = !arbol;
  $("bArbol").textContent = `Árbol: ${arbol ? "sí" : "no"}`;
  dibujarArbol(E[i]);
}

// ------------------------------------------------------------------ tamaño del tablero
function ajustar() {
  const z = $("zona");
  const et = Math.round(Math.max(18, Math.min(30, z.clientHeight * 0.035)));
  const disp = Math.min(z.clientWidth - et - 14, z.clientHeight - et - 14);
  cs = Math.max(40, Math.floor(disp / 8));
  document.documentElement.style.setProperty("--cs", cs + "px");
  document.documentElement.style.setProperty("--et", et + "px");
  cortar();
  render(i);
}

// ------------------------------------------------------------------ eventos
function enlazar() {
  $("bIni").onclick = () => { pausar(); ir(0); };
  $("bAnt").onclick = anterior;
  $("bPlay").onclick = alternar;
  $("bSig").onclick = siguiente;
  $("bFin").onclick = () => { pausar(); ir(TOTAL); };
  $("vMenos").onclick = () => cambiarVel(-1);
  $("vMas").onclick = () => cambiarVel(1);
  $("bArbol").onclick = alternarArbol;

  const linea = $("linea");
  const buscar = (ev) => {
    const r = linea.querySelector(".pista").getBoundingClientRect();
    const n = Math.round(((ev.clientX - r.left) / r.width) * TOTAL);
    const destino = Math.max(0, Math.min(TOTAL, n));
    if (destino !== i) { pausar(); ir(destino); }
  };
  linea.addEventListener("pointerdown", (ev) => { linea.setPointerCapture(ev.pointerId); buscar(ev); });
  linea.addEventListener("pointermove", (ev) => { if (linea.hasPointerCapture(ev.pointerId)) buscar(ev); });

  const tb = $("tablero");
  tb.addEventListener("mousemove", (ev) => {
    const r = tb.getBoundingClientRect();
    const c = Math.floor((ev.clientX - r.left) / cs), f = Math.floor((ev.clientY - r.top) / cs);
    if (f < 0 || f > 7 || c < 0 || c > 7) return mensaje();
    const v = TAB[f][c];
    const coste = v === "X" ? "∞" : v === "B" || v === "S" ? 1 : v;
    const partes = [`Casilla ${fpos([f, c])}`, `${NOMBRE[v]} (coste ${coste})`];
    const n = E[i][k([f, c])];
    if (n) {
      partes.push(`g=${fmt(n.g)}  h=${n.h}  f=${fmt(n.f)}`);
      partes.push(n.padre ? `padre ${fpos(n.padre)}` : "nodo inicial");
      partes.push(n.estado === "cerrada" ? `LISTA CERRADA #${n.orden}` : "LISTA ABIERTA");
    } else if (v !== "X") {
      partes.push("aún no generado");
    }
    mensaje(partes.join("   ·   "));
  });
  tb.addEventListener("mouseleave", () => mensaje());

  document.addEventListener("keydown", (ev) => {
    const acciones = {
      ArrowRight: siguiente, ArrowLeft: anterior, " ": alternar,
      Home: () => { pausar(); ir(0); }, End: () => { pausar(); ir(TOTAL); },
      "+": () => cambiarVel(1), "-": () => cambiarVel(-1), a: alternarArbol, A: alternarArbol,
    };
    const fn = acciones[ev.key];
    if (fn) { ev.preventDefault(); fn(); }
  });

  new ResizeObserver(ajustar).observe($("zona"));
}

construir();
enlazar();
const inicial = parseInt(location.hash.slice(1), 10);
if (inicial >= 0 && inicial <= TOTAL) i = inicial;
ajustar();
