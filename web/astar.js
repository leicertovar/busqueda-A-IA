"use strict";

// Réplica exacta de a_estrella() de astar_rescate.py (misma traza, mismos desempates y mensajes).
function aEstrella(tablero) {
  const tab = tablero.map((r) => r.slice());
  const F = tab.length, Cn = tab[0].length;
  let inicio = null, meta = null;
  tab.forEach((r, f) => r.forEach((v, c) => {
    if (v === "B") inicio = [f, c];
    if (v === "S") meta = [f, c];
  }));

  const fmtN = (x) => (x === null ? "∞" : Number.isInteger(x) ? String(x) : x.toFixed(1));
  const fp = (p) => `(${p[0]},${p[1]})`;
  const key = (p) => p[0] + "," + p[1];
  const h = (p) => Math.abs(p[0] - meta[0]) + Math.abs(p[1] - meta[1]);
  const coste = (p) => {
    const v = tab[p[0]][p[1]];
    return v === "X" ? null : v === "B" || v === "S" ? 1 : v;
  };
  const MOV = [[-1, 0, "arriba"], [1, 0, "abajo"], [0, -1, "izquierda"], [0, 1, "derecha"]];
  const cmp = (a, b) => (a.g + a.h) - (b.g + b.h) || a.h - b.h || a.orden - b.orden;
  const res = (n) => ({ pos: n.pos, g: n.g, h: n.h, f: n.g + n.h, padre: n.padre, orden: n.orden });

  let orden = 0;
  const n0 = { pos: inicio, g: 0, h: h(inicio), padre: null, orden: 0 };
  const abierta = new Map([[key(inicio), n0]]);
  const todos = new Map([[key(inicio), n0]]);
  const cerrada = [], enCerrada = new Set(), traza = [];
  let creados = 1, expandidos = 0, actualizados = 0, it = 0;

  const foto = (actual, vecinos, esMeta, mensaje) => traza.push({
    iteracion: it,
    actual: actual ? res(actual) : null,
    vecinos,
    abierta: [...abierta.values()].sort(cmp).map(res),
    cerrada: cerrada.slice(),
    creados, expandidos, actualizados,
    es_meta: esMeta,
    mensaje,
  });
  const fin = (encontrado, camino, costeTotal) => ({
    tablero: tab, inicio, meta, encontrado, camino, coste: costeTotal,
    creados, expandidos, actualizados, iteraciones: it, traza,
  });

  foto(null, [], false, `Inicialización: se inserta ${fp(inicio)} en la lista abierta con g=0, h=${n0.h}, f=${n0.h}`);

  while (abierta.size) {
    it++;
    let actual = null;
    for (const n of abierta.values()) if (!actual || cmp(n, actual) < 0) actual = n;
    abierta.delete(key(actual.pos));
    cerrada.push(actual.pos);
    enCerrada.add(key(actual.pos));

    if (key(actual.pos) === key(meta)) {
      const camino = [meta];
      while (todos.get(key(camino[camino.length - 1])).padre) camino.push(todos.get(key(camino[camino.length - 1])).padre);
      camino.reverse();
      foto(actual, [], true, `La meta ${fp(meta)} fue extraída de la lista abierta con f=${fmtN(actual.g + actual.h)}. FIN: se reconstruye el camino.`);
      return fin(true, camino, actual.g);
    }

    expandidos++;
    const vecinos = [];
    for (const [df, dc, nombre] of MOV) {
      const v = [actual.pos[0] + df, actual.pos[1] + dc];
      if (v[0] < 0 || v[0] >= F || v[1] < 0 || v[1] >= Cn) continue;
      const paso = coste(v);
      const info = { dir: nombre, pos: v, coste_paso: paso, g: null, h: null, f: null };
      const kv = key(v);
      if (paso === null) {
        info.accion = "BLOQUEADO (X) - se omite";
      } else if (enCerrada.has(kv)) {
        info.accion = "En lista cerrada - se omite";
      } else {
        const gN = actual.g + paso, hv = h(v);
        Object.assign(info, { g: gN, h: hv, f: gN + hv });
        const ex = abierta.get(kv);
        if (!ex) {
          orden++;
          const n = { pos: v, g: gN, h: hv, padre: actual.pos, orden };
          abierta.set(kv, n);
          todos.set(kv, n);
          creados++;
          info.accion = "NUEVO - se inserta en lista abierta";
        } else if (gN < ex.g) {
          const gv = ex.g;
          ex.g = gN;
          ex.padre = actual.pos;
          actualizados++;
          info.accion = `MEJOR CAMINO - g baja de ${fmtN(gv)} a ${fmtN(gN)}, nuevo padre`;
        } else {
          info.accion = `Ya en lista abierta con g=${fmtN(ex.g)} <= ${fmtN(gN)} - sin cambios`;
        }
      }
      vecinos.push(info);
    }
    foto(actual, vecinos, false, `Se expande ${fp(actual.pos)} (f=${fmtN(actual.g + actual.h)})`);
  }
  return fin(false, [], null);
}
