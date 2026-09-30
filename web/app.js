"use strict";

// Los datos los calcula Python (servidor.py): la página no ejecuta A* por su cuenta.
let D0;
async function api(ruta, cuerpo) {
  const r = await fetch(ruta, cuerpo === undefined ? {} :
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
  if (!r.ok) throw new Error(`${ruta}: ${r.status}`);
  return r.json();
}

const NS = "http://www.w3.org/2000/svg";
const $ = (id) => document.getElementById(id);
const k = (p) => p[0] + "," + p[1];
const fmt = (x) => (x === null || x === undefined ? "∞" : Number.isInteger(x) ? String(x) : x.toFixed(1));
const fpos = (p) => `(${p[0]},${p[1]})`;
const azar = (a, b) => a + Math.random() * (b - a);

const NOMBRE = { 1: "Libre", 2: "Escombros leves", 4: "Grietas / Humo", 7: "Fuego parcial / Agua",
                 B: "Bombero (inicio)", S: "Superviviente (meta)", X: "Derrumbe (bloqueado)" };
const ICONO = { 2: "escombros", 4: "grietas", 7: "fuego", B: "bombero", S: "superviviente", X: "bloqueado" };
const C = { azul: "#3b82f6", azulClaro: "#7cb4ff", magenta: "#e879f9", verde: "#22c55e", ambar: "#f59e0b",
            rojo: "#ef4444", gris: "#94a3b8", pizarra: "#64748b", cian: "#22d3ee", amarillo: "#facc15" };
const FLECHA = { arriba: "↑", abajo: "↓", izquierda: "←", derecha: "→" };
const VELS = [0.25, 0.5, 0.75, 1, 1.5, 2, 3];
const SUAVE = "cubic-bezier(.22,1,.36,1)";
const REBOTE = "cubic-bezier(.34,1.56,.64,1)";
const FRASES = ["¡Auxilio!", "¡Estoy aquí!", "¡Ayuda!", "¿Hay alguien?", "¡Por aquí!"];

// ------------------------------------------------------------------ estado
let DAT, T, TOTAL, TAB, META, INICIO, E, celdas = {};
let i = 0, vel = 1, jugando = false, arbol = true, heliVisto = false;
let cs = 80;
const G = { et: 20, muro: 10, techo: 50, calle: 44 };
let tPlay = null, gen = 0, anims = [], pendientes = [];
let introActiva = false, hoverPos = null;
const editor = { activo: false, pincel: "X", pintando: false, ultima: null };

function precalcular(traza) {
  const res = [], conocidos = {};
  for (const e of traza) {
    if (e.actual) conocidos[k(e.actual.pos)] = { ...e.actual };
    for (const n of e.abierta) conocidos[k(n.pos)] = { ...n };
    const orden = {};
    e.cerrada.forEach((p, j) => (orden[k(p)] = j + 1));
    const abiertos = new Set(e.abierta.map((n) => k(n.pos)));
    const est = {};
    for (const [kk, n] of Object.entries(conocidos)) {
      est[kk] = { ...n, estado: orden[kk] ? "cerrada" : abiertos.has(kk) ? "abierta" : "?", orden: orden[kk] || null };
    }
    res.push(est);
  }
  return res;
}

function tipo(accion) {
  if (accion.startsWith("NUEVO")) return ["NUEVO", C.azul];
  if (accion.startsWith("MEJOR")) return ["MEJORA g", C.ambar];
  if (accion.startsWith("BLOQ")) return ["BLOQUEADO", C.rojo];
  if (accion.startsWith("En lista cerrada")) return ["EN CERRADA", C.pizarra];
  return ["SIN CAMBIO", "#475569"];
}

// ------------------------------------------------------------------ animación: todo lo registrado se cancela con cortar()
const ms = (s) => (s / vel) * 1000;

function A(el, frames, dur, delay = 0, easing = SUAVE, fill = "backwards") {
  const a = el.animate(frames, { duration: ms(dur), delay: ms(delay), easing, fill });
  anims.push(a);
  return a;
}
function despues(s, fn) { pendientes.push(setTimeout(fn, ms(s))); }
function sonar(s, fn, ...args) { despues(s, () => fn(...args)); }

function cortar() {
  gen++;
  anims.forEach((a) => a.cancel());
  pendientes.forEach(clearTimeout);
  anims = [];
  pendientes = [];
  $("gHaz").replaceChildren();
  document.querySelectorAll(".tmp").forEach((n) => n.remove());
  introActiva = false;
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

// ------------------------------------------------------------------ geometría
const trans = (p) => `translate(${p[1] * cs}px, ${p[0] * cs}px)`;
const transFicha = (p) => `translate(${p[1] * cs + cs * 0.19}px, ${p[0] * cs + cs * 0.19}px)`;
const enEscena = (p) => ({ x: G.et + G.muro + (p[1] + 0.5) * cs, y: G.techo + G.muro + (p[0] + 0.5) * cs });

// ------------------------------------------------------------------ construcción
function construirFijo() {
  for (let n = 0; n < 8; n++) {
    $("etqCol").insertAdjacentHTML("beforeend", `<span>${n}</span>`);
    $("etqFil").insertAdjacentHTML("beforeend", `<span>${n}</span>`);
  }
  const est = [];
  for (let n = 0; n < 90; n++) {
    est.push(`${Math.round(azar(0, 1600))}px ${Math.round(azar(0, 700))}px 0 ${Math.random() < 0.2 ? 1 : 0}px rgba(255,255,255,${azar(0.25, 0.8).toFixed(2)})`);
  }
  $("estrellas").style.boxShadow = est.join(",");
  const polvo = $("polvoAmb");
  for (let n = 0; n < 16; n++) {
    const s = document.createElement("span");
    s.style.left = azar(0, 100) + "%";
    s.style.animationDuration = azar(9, 18) + "s";
    s.style.animationDelay = -azar(0, 18) + "s";
    polvo.appendChild(s);
  }
}

function construirCeldas() {
  const tb = $("tablero");
  tb.querySelectorAll(".celda").forEach((n) => n.remove());
  celdas = {};
  for (let f = 0; f < 8; f++) {
    for (let c = 0; c < 8; c++) {
      const v = TAB[f][c];
      const el = document.createElement("div");
      el.className = `celda t-${v}`;
      const ico = ICONO[v] ? `<svg class="ico" viewBox="0 0 100 100"><use href="#ico-${ICONO[v]}"/></svg>` : "";
      const brasas = v === 7
        ? [0, 1, 2].map(() => `<span class="brasa" style="left:${azar(25, 70).toFixed(0)}%;animation-delay:${(-azar(0, 2.2)).toFixed(2)}s"></span>`).join("")
        : "";
      const etiqueta = v === "B" ? "B · 1" : v === "S" ? "S · 1" : `c=${v}`;
      el.innerHTML =
        `<div class="caja"><div class="suelo"></div>${ico}${brasas}` +
        `<div class="tinte"></div><div class="verde"></div>` +
        (v === "X" ? "" :
          `<span class="coste">${etiqueta}</span><span class="orden"></span>` +
          `<div class="valores"><span class="gh"></span><span class="fv"></span></div>`) +
        `</div><div class="anillo"></div><div class="destello"></div>`;
      tb.insertBefore(el, $("capa"));
      const q = (s) => el.querySelector(s);
      celdas[k([f, c])] = { el, v, caja: q(".caja"), ico: q(".ico"), tinte: q(".tinte"), verde: q(".verde"),
                            anillo: q(".anillo"), destello: q(".destello"), valores: q(".valores"),
                            gh: q(".gh"), fv: q(".fv"), orden: q(".orden") };
    }
  }
}

function construirPuntos() {
  const puntos = $("puntos");
  puntos.replaceChildren();
  for (let j = 0; j <= TOTAL; j++) {
    const p = document.createElement("div");
    p.className = "punto";
    p.style.left = `${(j / Math.max(TOTAL, 1)) * 100}%`;
    puntos.appendChild(p);
  }
}

function cargar(datos) {
  DAT = datos;
  T = datos.traza;
  TOTAL = T.length - 1;
  TAB = datos.tablero.map((r) => r.slice());
  META = datos.meta;
  INICIO = datos.inicio;
  E = precalcular(T);
  i = 0;
  construirCeldas();
  construirPuntos();
}

// ------------------------------------------------------------------ render estático
function colocarDecorado() {
  $("helipuerto").style.left = `${G.muro + (INICIO[1] + 0.5) * cs}px`;
  const m = enEscena(META);
  const b = $("burbuja");
  b.style.left = m.x + "px";
  b.style.top = m.y - cs * 0.42 + "px";
  b.classList.toggle("der", META[1] >= 6);
}

function render(idx, conPanel = true) {
  const e = T[idx], est = E[idx];
  const final = idx === TOTAL && DAT.encontrado;
  const camino = new Set(final ? DAT.camino.map(k) : []);

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
  sel.style.display = e.actual && !editor.activo ? "block" : "none";
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
  $("ambulancia").classList.toggle("encendida", final);
  const b = $("burbuja");
  b.classList.toggle("fija", final);
  if (final) b.textContent = "¡Gracias!";
  colocarDecorado();

  if (conPanel) panel(idx);
  timeline();
  if (hoverPos) dibujarHover(hoverPos);
}

function dibujarArbol(est, nuevos) {
  const g = $("gArbol");
  g.replaceChildren();
  if (!arbol || editor.activo) return;
  const off = 0.42;
  for (const [kk, n] of Object.entries(est)) {
    if (!n.padre) continue;
    const [f0, c0] = n.padre, [f1, c1] = n.pos;
    const df = f1 - f0, dc = c1 - c0;
    const a = df
      ? { x1: c0 + 0.83, y1: f0 + 0.5 + df * off, x2: c0 + 0.83, y2: f1 + 0.5 - df * off }
      : { x1: c0 + 0.5 + dc * off, y1: f0 + 0.3, x2: c1 + 0.5 - dc * off, y2: f0 + 0.3 };
    const l = svg("line", { ...a, stroke: "#475a7a", "stroke-width": 0.035, "stroke-linecap": "round", "marker-end": marca("#475a7a") });
    g.appendChild(l);
    if (nuevos && nuevos.has(kk)) A(l, [{ opacity: 0 }, { opacity: 1 }], 0.3, nuevos.get(kk));
  }
}

function dibujarRuta() {
  const pts = DAT.camino.map((p) => `${p[1] + 0.5},${p[0] + 0.5}`).join(" ");
  const pl = svg("polyline", { points: pts, fill: "none", stroke: "#bbf7d0", "stroke-width": 0.045,
                               "stroke-linecap": "round", "stroke-linejoin": "round", opacity: 0.55, pathLength: 1 });
  $("gRuta").appendChild(pl);
  return pl;
}

// ------------------------------------------------------------------ narrador
function lista(ps) {
  const t = ps.map((p) => `<b>${fpos(p)}</b>`);
  return t.length < 2 ? t.join("") : t.slice(0, -1).join(", ") + " y " + t[t.length - 1];
}

function narrar(idx) {
  const e = T[idx];
  if (idx === 0) {
    const n = e.abierta[0];
    return `El bombero entra en <b>${fpos(INICIO)}</b>. A* lo coloca en la <b>lista abierta</b> con ` +
           `<span class="cg">g = 0</span> (todavía no ha caminado) y <span class="ch">h = ${n.h}</span> ` +
           `(distancia Manhattan hasta el superviviente), así que <span class="cf">f = ${fmt(n.f)}</span>. ` +
           `Pulsa <b>›</b> para dar el primer paso.`;
  }
  if (e.es_meta) {
    return `¡El superviviente <b>${fpos(META)}</b> sale de la lista abierta con <span class="cf">f = ${fmt(e.actual.f)}</span>! ` +
           `Como h(n) nunca sobreestima (es <b>admisible</b>), ningún otro camino puede ser más barato. ` +
           `La ruta se reconstruye siguiendo los <b>padres</b> desde la meta: coste <b>${fmt(DAT.coste)}</b> ` +
           `en ${DAT.camino.length - 1} movimientos.`;
  }
  const a = e.actual, prev = T[idx - 1].abierta;
  let s = prev.length > 1
    ? `De los <b>${prev.length}</b> nodos de la lista abierta, <b>${fpos(a.pos)}</b> tiene el menor <span class="cf">f = ${fmt(a.f)}</span>`
    : `<b>${fpos(a.pos)}</b> es el único nodo de la lista abierta (<span class="cf">f = ${fmt(a.f)}</span>)`;
  s += ": se expande y pasa a la <b>lista cerrada</b>.";
  const emp = prev.filter((n) => n.f === a.f && k(n.pos) !== k(a.pos));
  if (emp.length) {
    const mismoH = emp.filter((n) => n.h === a.h);
    s += mismoH.length
      ? ` Empata en f y en h con ${lista(mismoH.map((n) => n.pos))}: gana el que entró antes a la lista.`
      : ` Empata en f con ${lista(emp.map((n) => n.pos))}, pero tiene menor <span class="ch">h = ${a.h}</span>: está más cerca de la meta.`;
  }
  const grupo = (t) => e.vecinos.filter((v) => tipo(v.accion)[0] === t).map((v) => v.pos);
  const nu = grupo("NUEVO"), me = grupo("MEJORA g"), si = grupo("SIN CAMBIO"), ce = grupo("EN CERRADA"), bl = grupo("BLOQUEADO");
  const partes = [];
  if (nu.length) partes.push(`${lista(nu)} ${nu.length > 1 ? "entran" : "entra"} en la lista abierta`);
  if (me.length) partes.push(`${lista(me)} ${me.length > 1 ? "mejoran" : "mejora"} su g: encontramos un camino más barato`);
  if (si.length) partes.push(`${lista(si)} ya ${si.length > 1 ? "estaban" : "estaba"} en la abierta con un g igual o mejor`);
  if (ce.length) partes.push(`${lista(ce)} ya ${ce.length > 1 ? "fueron visitados" : "fue visitado"}`);
  if (bl.length) partes.push(`${lista(bl)} ${bl.length > 1 ? "están derrumbados" : "está derrumbado"}`);
  if (partes.length) s += ` Vecinos: ${partes.join("; ")}.`;
  if (idx === TOTAL && !DAT.encontrado) s += " <b>La lista abierta quedó vacía: no existe ningún camino hasta el superviviente.</b>";
  return s;
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

  const n = e.actual || e.abierta[0];
  const nPos = $("nPos");
  nPos.textContent = n ? fpos(n.pos) : "—";
  nPos.style.color = e.es_meta ? C.verde : e.actual ? C.magenta : C.azulClaro;
  $("eqG").textContent = n ? fmt(n.g) : "–";
  $("eqH").textContent = n ? n.h : "–";
  $("eqF").textContent = n ? fmt(n.f) : "–";
  $("narr").innerHTML = narrar(idx);
  if (animar) {
    A(nPos, [{ opacity: 0, transform: "translateY(8px)" }, { opacity: 1, transform: "none" }], 0.4);
    document.querySelectorAll(".eq").forEach((q, j) =>
      A(q, [{ transform: "scale(.7)", opacity: 0 }, { transform: "none", opacity: 1 }], 0.35, 0.08 * j, REBOTE));
    A($("narr"), [{ opacity: 0 }, { opacity: 1 }], 0.4, 0.1);
  }

  const tv = $("vecinos");
  tv.replaceChildren();
  if (e.es_meta) tv.innerHTML = `<tr><td class="fin-msg" colspan="6">Meta alcanzada: fin de la búsqueda</td></tr>`;
  if (idx === 0) tv.innerHTML = `<tr><td class="gris" colspan="6">Todavía no se ha expandido ningún nodo.</td></tr>`;
  e.vecinos.forEach((v, j) => {
    const [tp, col] = tipo(v.accion);
    const tr = document.createElement("tr");
    tr.title = v.accion;
    const calc = v.g === null
      ? `<td colspan="3" class="gris">${v.coste_paso === null ? "derrumbe: coste ∞" : "ya en lista cerrada"}</td>`
      : `<td class="cg">g=${fmt(e.actual.g)}+${fmt(v.coste_paso)}=${fmt(v.g)}</td><td class="ch">h=${v.h}</td><td class="cf">f=${fmt(v.f)}</td>`;
    tr.innerHTML = `<td>${FLECHA[v.dir]} ${v.dir}</td><td>${fpos(v.pos)}</td>${calc}` +
                   `<td><span class="badge" style="background:${col}">${tp}</span></td>`;
    tv.appendChild(tr);
    if (animar) A(tr, [{ opacity: 0, transform: "translateX(-10px)" }, { opacity: 1, transform: "none" }], 0.3, retrasos[j] || 0);
  });

  const retrasoDe = new Map();
  e.vecinos.forEach((v, j) => retrasoDe.set(k(v.pos), retrasos[j] || 0));
  const nuevos = new Set(e.vecinos.filter((v) => v.accion.startsWith("NUEVO")).map((v) => k(v.pos)));
  const mejorados = new Set(e.vecinos.filter((v) => v.accion.startsWith("MEJOR")).map((v) => k(v.pos)));
  const tb = $("tAbierta");
  tb.replaceChildren();
  e.abierta.forEach((nd, j) => {
    const kk = k(nd.pos);
    const tr = document.createElement("tr");
    if (j === 0 && !e.es_meta) tr.className = "siguiente";
    else if (mejorados.has(kk)) tr.className = "mejora";
    else if (nuevos.has(kk)) tr.className = "nuevo";
    tr.innerHTML = `<td>${fpos(nd.pos)}</td><td>${fmt(nd.g)}</td><td>${nd.h}</td><td>${fmt(nd.f)}</td><td>${nd.padre ? fpos(nd.padre) : "—"}</td>`;
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

  actualizarSub();
  mensaje();
}

function actualizarSub() {
  const sub = $("sub");
  sub.classList.remove("ok", "mal");
  if (editor.activo) {
    sub.textContent = DAT.encontrado
      ? `Vista previa: ruta de coste ${fmt(DAT.coste)} · ${DAT.expandidos} nodos expandidos`
      : "Vista previa: ¡no existe ningún camino hasta el superviviente!";
    if (!DAT.encontrado) sub.classList.add("mal");
  } else if (i === TOTAL && DAT.encontrado) {
    sub.textContent = `✔ Superviviente rescatado · coste total ${fmt(DAT.coste)} · ${DAT.camino.length - 1} movimientos`;
    sub.classList.add("ok");
  } else if (i === TOTAL) {
    sub.textContent = "✖ No existe camino hasta el superviviente";
    sub.classList.add("mal");
  } else {
    sub.textContent = `f(n) = g(n) + h(n) · h(n) = |x − ${META[0]}| + |y − ${META[1]}| (Manhattan)`;
  }
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

// ------------------------------------------------------------------ efectos
function destello(c, color, delay, dur = 0.45) {
  c.destello.style.borderColor = color;
  A(c.destello, [{ opacity: 1, transform: "scale(1)" }, { opacity: 0, transform: "scale(1.25)" }], dur, delay, SUAVE, "none");
}

function sacudir(el, delay = 0) {
  A(el, [{ transform: "translateX(0)" }, { transform: "translateX(-4px)" }, { transform: "translateX(4px)" },
         { transform: "translateX(-2px)" }, { transform: "translateX(0)" }], 0.3, delay, "linear", "none");
}

function flotar(p, texto, color, delay, persistente = false) {
  const d = document.createElement("div");
  d.className = "flotante" + (persistente ? "" : " tmp");
  d.textContent = texto;
  d.style.color = color;
  d.style.left = (p[1] + 0.5) * cs + "px";
  d.style.top = (p[0] + 0.15) * cs + "px";
  $("flotantes").appendChild(d);
  const frames = [
    { opacity: 0, transform: "translate(-50%, 10%) scale(.6)" },
    { opacity: 1, transform: "translate(-50%, -30%) scale(1)", offset: 0.2 },
    { opacity: 1, transform: "translate(-50%, -80%) scale(1)", offset: 0.75 },
    { opacity: 0, transform: "translate(-50%, -120%) scale(.95)" },
  ];
  if (persistente) {
    d.animate(frames, { duration: 1600, easing: "ease-out", fill: "both" }).onfinish = () => d.remove();
  } else {
    A(d, frames, 1.25, delay, "ease-out", "both");
    despues(delay + 1.3, () => d.remove());
  }
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

function particulas(x, y, delay, { n = 8, color = "rgba(203,213,225,.75)", radio = 30, dur = 0.7, persistente = false } = {}) {
  for (let j = 0; j < n; j++) {
    const p = document.createElement("div");
    p.className = "polvo-p" + (persistente ? "" : " tmp");
    p.style.left = x + "px";
    p.style.top = y + "px";
    p.style.background = Array.isArray(color) ? color[j % color.length] : color;
    const s = azar(0.4, 1.1);
    p.style.width = p.style.height = 12 * s + "px";
    $("fx").appendChild(p);
    const ang = (j / n) * Math.PI * 2 + azar(0, 0.5), r = radio * azar(0.6, 1.3);
    const frames = [{ opacity: 0.95, transform: "translate(0,0) scale(.4)" },
                    { opacity: 0, transform: `translate(${Math.cos(ang) * r}px, ${Math.sin(ang) * r - 10}px) scale(1.4)` }];
    if (persistente) p.animate(frames, { duration: dur * 1000, easing: "ease-out", fill: "both" }).onfinish = () => p.remove();
    else A(p, frames, dur, delay, "ease-out", "both");
  }
}

function confetiGrande(t) {
  const fx = $("fx"), W = fx.clientWidth, H = fx.clientHeight;
  const colores = [C.verde, C.ambar, C.azulClaro, C.magenta, C.amarillo, "#f8fafc", C.rojo];
  for (let j = 0; j < 80; j++) {
    const d = document.createElement("div");
    d.className = "conf tmp";
    d.style.left = azar(0, W) + "px";
    d.style.background = colores[j % colores.length];
    d.style.width = azar(6, 10) + "px";
    d.style.height = azar(9, 15) + "px";
    fx.appendChild(d);
    A(d, [{ transform: "translate(0,-30px) rotate(0)", opacity: 1 },
          { transform: `translate(${azar(-90, 90)}px, ${H * azar(0.75, 1.05)}px) rotate(${azar(-900, 900)}deg)`, opacity: 0.2 }],
      azar(1.8, 2.8), t + azar(0, 0.5), "cubic-bezier(.25,.6,.45,1)", "both");
  }
}

function decir(texto, dur = 2200) {
  const b = $("burbuja");
  if (b.classList.contains("fija")) return;
  b.textContent = texto;
  b.animate([
    { opacity: 0, scale: 0.4 },
    { opacity: 1, scale: 1.08, offset: 0.1 },
    { opacity: 1, scale: 1, offset: 0.16 },
    { opacity: 1, scale: 1, offset: 0.85 },
    { opacity: 0, scale: 0.9 },
  ], { duration: dur, easing: "ease-out" });
}

function ambiente() {
  if (introActiva || editor.activo || document.hidden) return;
  if (i === TOTAL && DAT.encontrado) return;
  if (Math.random() < 0.35) return;
  decir(FRASES[Math.floor(Math.random() * FRASES.length)]);
}

// ------------------------------------------------------------------ paso animado i -> i+1
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

  // 1. el selector salta al nodo de menor f
  if (selAntes) A($("selector"), [{ transform: selAntes }, { transform: trans(act) }], 0.3, 0, "cubic-bezier(.65,0,.35,1)");
  else A($("selector"), [{ opacity: 0, transform: trans(act) + " scale(1.3)" }, { opacity: 1, transform: trans(act) }], 0.3);
  sonar(0, Sonido.seleccionar);

  // 2. pasa de la lista abierta a la cerrada
  A(ca.tinte, [{ opacity: 0 }, { opacity: 0.8 }], 0.35, 0.2);
  A(ca.anillo, [{ opacity: 1, transform: "scale(1)" }, { opacity: 0, transform: "scale(.85)" }], 0.35, 0.2);
  A(ca.caja, [{ transform: "scale(1)" }, { transform: "scale(.92)" }, { transform: "scale(1)" }], 0.35, 0.2, SUAVE, "none");
  if (ca.orden) A(ca.orden, [{ transform: "scale(0)" }, { transform: "scale(1)" }], 0.35, 0.45, REBOTE);
  sonar(0.22, Sonido.cerrar);

  // 3. evaluación de los vecinos
  const nuevasAristas = new Map();
  let nNuevo = 0;
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
      flotar(v.pos, `g ${fmt(e.actual.g)}+${fmt(v.coste_paso)}=${fmt(v.g)}`, C.ambar, tr);
      nuevasAristas.set(k(v.pos), tr);
      sonar(tr, Sonido.nuevo, nNuevo++);
    } else if (tp === "MEJORA g") {
      A(c.valores, [{ opacity: 1 }, { opacity: 0 }, { opacity: 1 }], 0.5, tr, "linear");
      destello(c, C.ambar, tr);
      flotar(v.pos, `g ↓ ${fmt(v.g)}`, C.ambar, tr);
      nuevasAristas.set(k(v.pos), tr);
      sonar(tr, Sonido.mejora);
    } else if (tp === "BLOQUEADO") {
      destello(c, C.rojo, tr);
      sacudir(c.caja, tr);
      flotar(v.pos, "¡derrumbe!", "#fca5a5", tr);
      sonar(tr, Sonido.bloqueado);
    } else {
      destello(c, C.gris, tr);
      flotar(v.pos, tp === "EN CERRADA" ? "ya visitado" : "sin mejora", C.gris, tr);
      sonar(tr, Sonido.visitado);
    }
  });
  dibujarArbol(E[i], nuevasAristas);

  let fin = ini + e.vecinos.length * esc + 0.5;
  if (e.es_meta) fin = animarRuta(0.6);
  else if (i === TOTAL) sonar(fin, Sonido.incorrecto);
  return fin;
}

function animarRuta(t) {
  const cam = DAT.camino, seg = 0.17, dur = (cam.length - 1) * seg;
  const pl = $("gRuta").firstChild;
  A(pl, [{ strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDasharray: 1, strokeDashoffset: 0 }], dur, t, "linear");
  const ficha = $("ficha");
  A(ficha, [{ opacity: 0, transform: transFicha(cam[0]) + " scale(.3)" }, { opacity: 1, transform: transFicha(cam[0]) }], 0.3, t - 0.3, REBOTE);
  A(ficha, cam.map((p) => ({ transform: transFicha(p) })), dur, t, "linear");
  cam.forEach((p, j) => {
    A(celdas[k(p)].verde, [{ opacity: 0 }, { opacity: 0.72 }], 0.3, t + j * seg);
    if (j) sonar(t + j * seg, Sonido.paso, j);
  });
  const m = celdas[k(META)];
  const fin = t + dur;
  destello(m, C.verde, fin, 0.7);
  A(ficha, [{ transform: transFicha(META) }, { transform: transFicha(META) + " scale(1.3)" }, { transform: transFicha(META) }],
    0.5, fin, SUAVE, "none");
  const amb = $("ambulancia"), b = $("burbuja");
  amb.classList.remove("encendida");
  b.classList.remove("fija");
  despues(fin, () => {
    amb.classList.add("encendida");
    b.textContent = "¡Gracias!";
    b.classList.add("fija");
    A(b, [{ scale: 0.3 }, { scale: 1.15 }, { scale: 1 }], 0.45, 0, REBOTE, "none");
  });
  A($("escena"), [{ transform: "translateY(0)" }, { transform: "translateY(-6px)" }, { transform: "translateY(0)" }], 0.4, fin, REBOTE, "none");
  sonar(fin, Sonido.victoria);
  sonar(fin + 0.6, Sonido.sirena, 2.6);
  const pm = enEscena(META);
  particulas(pm.x, pm.y, fin, { n: 14, color: [C.verde, C.amarillo, "#f8fafc"], radio: cs * 0.9, dur: 0.9 });
  confetiGrande(fin);
  return fin + 1.2;
}

// ------------------------------------------------------------------ introducción (terremoto + helicóptero)
// Devuelve la duración (s) de la animación.
function intro() {
  cortar();
  i = 0;
  render(0);
  introActiva = true;
  Sonido.terremoto();

  const temblor = [];
  for (let j = 0; j <= 16; j++) {
    const a = j === 16 ? 0 : (1 - j / 16) * 7;
    temblor.push({ transform: `translate(${azar(-a, a).toFixed(1)}px, ${azar(-a, a).toFixed(1)}px) rotate(${azar(-a, a) * 0.08}deg)` });
  }
  A($("escena"), temblor, 1.9, 0, "linear", "none");

  const xs = Object.entries(celdas).filter(([, c]) => c.v === "X").sort(() => Math.random() - 0.5);
  xs.forEach(([kk, c], j) => {
    const d = 0.25 + j * (1.2 / Math.max(xs.length, 1));
    A(c.caja, [{ transform: "translateY(-70%) rotate(-10deg)", opacity: 0 },
               { transform: "translateY(5%) rotate(2deg)", opacity: 1, offset: 0.75 },
               { transform: "none", opacity: 1 }], 0.45, d, "cubic-bezier(.5,0,.8,.6)");
    const [f, cc] = kk.split(",").map(Number), pe = enEscena([f, cc]);
    particulas(pe.x, pe.y + cs * 0.3, d + 0.35, { n: 6, radio: cs * 0.45 });
    if (j % 3 === 0) sonar(d + 0.35, Sonido.derrumbe);
  });
  Object.values(celdas).filter((c) => c.ico && c.v !== "X" && c.v !== "B").forEach((c, j) => {
    A(c.ico, [{ opacity: 0, transform: "scale(.2)" }, { opacity: c.el.classList.contains("conocida") ? 0.2 : 0.92, transform: "none" }],
      0.45, 1.5 + j * 0.03, REBOTE);
  });

  // helicóptero
  const heli = $("helicoptero"), cuerda = $("cuerda"), ficha = $("ficha");
  const hw = cs * 1.5, hh = cs * 0.75;
  const pb = enEscena(INICIO);
  const hx = pb.x - hw * 0.46, hy = -hh * 0.2;
  A(heli, [{ opacity: 1, transform: `translate(${-hw - G.et}px, ${hy - cs}px)` },
           { opacity: 1, transform: `translate(${hx}px, ${hy}px)` }], 1.2, 2.0, "cubic-bezier(.2,.8,.3,1)", "both");
  A(heli, [{ opacity: 1, transform: `translate(${hx}px, ${hy}px)` },
           { opacity: 1, transform: `translate(${hx + cs * 4}px, ${hy - cs * 2.5}px)` }], 1.1, 4.3, "ease-in", "forwards");
  sonar(1.9, Sonido.helicoptero, 3.6);

  const yCuerda = hy + hh * 0.85;
  cuerda.style.left = pb.x + "px";
  cuerda.style.top = yCuerda + "px";
  cuerda.style.height = Math.max(0, pb.y - yCuerda) + "px";
  A(cuerda, [{ transform: "scaleY(0)" }, { transform: "scaleY(1)" }], 0.5, 3.1, "ease-out", "both");
  A(cuerda, [{ transform: "scaleY(1)" }, { transform: "scaleY(0)" }], 0.35, 4.0, "ease-in", "forwards");

  ficha.style.display = "block";
  const caida = pb.y - yCuerda;
  A(ficha, [{ opacity: 0, transform: transFicha(INICIO) + ` translateY(${-caida}px)` },
            { opacity: 1, transform: transFicha(INICIO) + ` translateY(${-caida}px)`, offset: 0.1 },
            { opacity: 1, transform: transFicha(INICIO) }], 0.8, 3.15, "ease-in", "both");
  A(ficha, [{ opacity: 1, transform: transFicha(INICIO) }, { opacity: 0, transform: transFicha(INICIO) + " scale(.4)" }],
    0.4, 4.4, "ease-in", "forwards");
  sonar(3.95, Sonido.aterrizar);
  particulas(pb.x, pb.y + cs * 0.25, 3.95, { n: 8, radio: cs * 0.4 });
  const cb = celdas[k(INICIO)];
  destello(cb, C.verde, 3.95, 0.6);

  despues(4.8, () => {
    ficha.style.display = "none";
    introActiva = false;
    decir("¡Auxilio!", 2600);
  });
  return 5;
}

// ------------------------------------------------------------------ hover didáctico
function dibujarHover(p) {
  const [f, c] = p;
  const g = $("gHover");
  g.replaceChildren();
  const tip = $("tip");
  if (editor.activo) { tip.hidden = true; return; }
  const v = TAB[f][c];
  const n = E[i][k(p)];
  const coste = v === "X" ? "∞" : v === "B" || v === "S" ? 1 : v;
  let html = `<div class="tip-t"><b>Casilla ${fpos(p)}</b><span>${NOMBRE[v]}</span></div>` +
             `<div>Coste de entrar: <b>${coste}</b></div>`;
  let msg = `Casilla ${fpos(p)} · ${NOMBRE[v]} (coste ${coste})`;
  if (v === "X") {
    html += `<div class="tip-e">Zona derrumbada: A* nunca puede pasar por aquí.</div>`;
  } else {
    const df = Math.abs(f - META[0]), dc = Math.abs(c - META[1]);
    g.appendChild(svg("polyline", {
      points: `${c + 0.5},${f + 0.5} ${META[1] + 0.5},${f + 0.5} ${META[1] + 0.5},${META[0] + 0.5}`,
      fill: "none", stroke: C.cian, "stroke-width": 0.05, "stroke-dasharray": "0.12 0.1", "stroke-linecap": "round",
    }));
    html += `<div class="ch">h = |${f} − ${META[0]}| + |${c} − ${META[1]}| = ${df} + ${dc} = <b>${df + dc}</b></div>`;
    msg += ` · h=${df + dc}`;
    if (n) {
      const pts = [];
      let cur = n, guarda = 0;
      while (cur && guarda++ < 80) {
        pts.push(`${cur.pos[1] + 0.5},${cur.pos[0] + 0.5}`);
        cur = cur.padre ? E[i][k(cur.padre)] : null;
      }
      if (pts.length > 1) {
        g.appendChild(svg("polyline", { points: pts.join(" "), fill: "none", stroke: C.ambar, "stroke-width": 0.06,
                                        "stroke-dasharray": "0.14 0.08", "stroke-linecap": "round", "stroke-linejoin": "round" }));
      }
      html += `<div class="cg">g = <b>${fmt(n.g)}</b> <small>(coste del camino ámbar desde el bombero)</small></div>` +
              `<div class="cf">f = g + h = ${fmt(n.g)} + ${n.h} = <b>${fmt(n.f)}</b></div>` +
              `<div class="tip-e">${n.estado === "cerrada" ? `En la lista cerrada (expandido en el paso ${n.orden})` : "En la lista abierta: esperando su turno"}</div>`;
      msg += ` · g=${fmt(n.g)} · f=${fmt(n.f)}`;
    } else {
      html += `<div class="tip-e">A* aún no ha descubierto esta casilla.</div>`;
    }
  }
  tip.innerHTML = html;
  tip.hidden = false;
  mensaje(msg);
}

function moverTip(ev) {
  const tip = $("tip");
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = ev.clientX + 18, y = ev.clientY + 18;
  if (x + w > innerWidth - 8) x = ev.clientX - w - 18;
  if (y + h > innerHeight - 8) y = ev.clientY - h - 18;
  tip.style.left = x + "px";
  tip.style.top = y + "px";
}

function quitarHover() {
  hoverPos = null;
  $("gHover").replaceChildren();
  $("tip").hidden = true;
  mensaje();
}

function celdaDe(ev) {
  const r = $("tablero").getBoundingClientRect();
  const c = Math.floor((ev.clientX - r.left) / cs), f = Math.floor((ev.clientY - r.top) / cs);
  return f < 0 || f > 7 || c < 0 || c > 7 ? null : [f, c];
}

// ------------------------------------------------------------------ editor
function alternarEditor() {
  editor.activo = !editor.activo;
  document.body.classList.toggle("editando", editor.activo);
  $("bEditor").classList.toggle("on", editor.activo);
  pausar();
  cortar();
  quitarHover();
  i = 0;
  render(0);
  if (editor.activo) {
    elegirPincel(editor.pincel);
    $("narr").innerHTML = "<b>Modo edición.</b> Elige un pincel y pinta sobre el edificio (puedes arrastrar). " +
                          "El bombero y el superviviente se mueven al pintarlos. Python recalcula A* en cada cambio.";
  }
}

function elegirPincel(v) {
  editor.pincel = v;
  document.querySelectorAll(".pincel").forEach((b) => b.classList.toggle("on", b.dataset.v === v));
}

// Las peticiones de pintado se encadenan para que las respuestas lleguen en orden.
let colaPintado = Promise.resolve();
function pintar(p) {
  const [f, c] = p;
  const v = editor.pincel === "X" || editor.pincel === "B" || editor.pincel === "S" ? editor.pincel : Number(editor.pincel);
  const actual = TAB[f][c];
  if (actual === v || actual === "B" || actual === "S") return;
  if (v === "B" || v === "S") {
    TAB.forEach((r, ff) => r.forEach((x, cc) => { if (x === v) TAB[ff][cc] = 1; }));
  }
  TAB[f][c] = v;
  const nuevo = TAB.map((r) => r.slice());
  colaPintado = colaPintado.then(() => api("/api/astar", { tablero: nuevo })).then((res) => {
    cargar(res);
    render(0);
    celdas[k(p)].caja.animate([{ transform: "scale(.5)" }, { transform: "scale(1)" }], { duration: 300, easing: REBOTE });
    Sonido.pintar();
  }).catch((err) => mensaje(`Error al recalcular A* en Python: ${err.message}`));
}

function aparecerTodo() {
  Object.entries(celdas).forEach(([kk, c]) => {
    const [f, cc] = kk.split(",").map(Number);
    c.caja.animate([{ transform: "scale(.2)", opacity: 0 }, { transform: "none", opacity: 1 }],
                   { duration: 380, delay: (f + cc) * 28, easing: REBOTE, fill: "backwards" });
  });
}

async function aleatorio() {
  try {
    cargar(await api("/api/aleatorio"));
    render(0);
    aparecerTodo();
    Sonido.derrumbe();
  } catch (err) {
    mensaje(`Error al generar el edificio en Python: ${err.message}`);
  }
}

// ------------------------------------------------------------------ navegación
function ir(n) {
  cortar();
  i = Math.max(0, Math.min(TOTAL, n));
  render(i);
}
function siguiente() {
  if (editor.activo) return;
  pausar();
  paso();
}
function anterior() { pausar(); ir(i - 1); }

function pausar() {
  jugando = false;
  clearTimeout(tPlay);
  $("bPlay").textContent = "▶ Reproducir";
}
function alternar() {
  if (editor.activo) return;
  if (jugando) return pausar();
  jugando = true;
  $("bPlay").textContent = "❚❚ Pausa";
  if (i >= TOTAL) ir(0);
  // La primera reproducción desde el inicio arranca con el terremoto y el helicóptero.
  if (i === 0 && !heliVisto) {
    heliVisto = true;
    tPlay = setTimeout(jugar, ms(intro()));
    return;
  }
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
  Sonido.tick();
}
function alternarArbol() {
  arbol = !arbol;
  $("bArbol").textContent = `Árbol: ${arbol ? "sí" : "no"}`;
  dibujarArbol(E[i]);
}
function alternarSonido() {
  const on = Sonido.alternar();
  $("bSonido").textContent = on ? "♪ Sonido" : "♪ Silencio";
  $("bSonido").classList.toggle("on", on);
}

// ------------------------------------------------------------------ tamaño
function ajustar() {
  const z = $("zona");
  const et = Math.round(Math.max(16, Math.min(26, z.clientHeight * 0.028)));
  cs = Math.max(34, Math.floor(Math.min((z.clientWidth - et - 16) / 8.24, (z.clientHeight - 16) / 9.41)));
  Object.assign(G, { et, muro: Math.round(cs * 0.12), techo: Math.round(cs * 0.62), calle: Math.round(cs * 0.55) });
  const r = document.documentElement.style;
  r.setProperty("--cs", cs + "px");
  for (const [n, v] of Object.entries(G)) r.setProperty("--" + n, v + "px");
  cortar();
  render(i);
}

// ------------------------------------------------------------------ eventos
function enlazar() {
  const clic = (id, fn) => $(id).addEventListener("click", () => { Sonido.iniciar(); fn(); });
  clic("bIni", () => { pausar(); ir(0); });
  clic("bAnt", anterior);
  clic("bPlay", alternar);
  clic("bSig", siguiente);
  clic("bFin", () => { pausar(); ir(TOTAL); });
  clic("vMenos", () => cambiarVel(-1));
  clic("vMas", () => cambiarVel(1));
  clic("bArbol", alternarArbol);
  clic("bEditor", alternarEditor);
  clic("bSonido", alternarSonido);
  clic("bListo", alternarEditor);
  clic("bOriginal", () => { cargar(D0); render(0); aparecerTodo(); });
  clic("bAleatorio", aleatorio);
  document.querySelectorAll(".pincel").forEach((b) => b.addEventListener("click", () => { elegirPincel(b.dataset.v); Sonido.tick(); }));

  const linea = $("linea");
  const buscar = (ev) => {
    const r = linea.querySelector(".pista").getBoundingClientRect();
    const destino = Math.max(0, Math.min(TOTAL, Math.round(((ev.clientX - r.left) / r.width) * TOTAL)));
    if (destino !== i) { pausar(); ir(destino); Sonido.tick(); }
  };
  linea.addEventListener("pointerdown", (ev) => { linea.setPointerCapture(ev.pointerId); buscar(ev); });
  linea.addEventListener("pointermove", (ev) => { if (linea.hasPointerCapture(ev.pointerId)) buscar(ev); });

  const tb = $("tablero");
  tb.addEventListener("pointerdown", (ev) => {
    Sonido.iniciar();
    const p = celdaDe(ev);
    if (!p || !editor.activo) return;
    editor.pintando = true;
    editor.ultima = k(p);
    pintar(p);
  });
  tb.addEventListener("pointermove", (ev) => {
    const p = celdaDe(ev);
    if (!p) return quitarHover();
    if (editor.activo && editor.pintando && k(p) !== editor.ultima) {
      editor.ultima = k(p);
      pintar(p);
    }
    if (!hoverPos || k(hoverPos) !== k(p)) {
      hoverPos = p;
      dibujarHover(p);
    }
    moverTip(ev);
  });
  tb.addEventListener("pointerleave", quitarHover);
  addEventListener("pointerup", () => { editor.pintando = false; });

  document.addEventListener("keydown", (ev) => {
    if (editor.activo) {
      const pinceles = { 1: "1", 2: "2", 4: "4", 7: "7", x: "X", b: "B", s: "S" };
      const pk = pinceles[ev.key.toLowerCase()];
      if (pk) return elegirPincel(pk);
      if (ev.key === "Escape" || ev.key.toLowerCase() === "e") return alternarEditor();
      return;
    }
    const acciones = {
      ArrowRight: siguiente, ArrowLeft: anterior, " ": alternar,
      Home: () => { pausar(); ir(0); }, End: () => { pausar(); ir(TOTAL); },
      "+": () => cambiarVel(1), "-": () => cambiarVel(-1),
      a: alternarArbol, e: alternarEditor, m: alternarSonido,
    };
    const fn = acciones[ev.key.length === 1 ? ev.key.toLowerCase() : ev.key];
    if (fn) {
      ev.preventDefault();
      Sonido.iniciar();
      fn();
    }
  });

  new ResizeObserver(ajustar).observe($("zona"));
  setInterval(ambiente, 6500);
}

// ------------------------------------------------------------------ arranque
(async () => {
  try {
    D0 = await api("/api/datos");
  } catch {
    document.body.innerHTML =
      "<p style='padding:2em;font-size:18px'>No se pudo conectar con Python. Inicia el proyecto con <code>python main.py</code>.</p>";
    return;
  }
  construirFijo();
  cargar(D0);
  enlazar();
  $("bSonido").classList.toggle("on", Sonido.activo);
  $("bSonido").textContent = Sonido.activo ? "♪ Sonido" : "♪ Silencio";
  const inicial = parseInt(location.hash.slice(1), 10);
  if (inicial >= 0 && inicial <= TOTAL) i = inicial;
  ajustar();
})();
