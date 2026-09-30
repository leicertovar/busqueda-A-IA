"use strict";

// Efectos de sonido sintetizados con Web Audio (sin archivos externos).
const Sonido = (() => {
  let ctx = null, master = null, ruidoBuf = null;
  let activo = true;
  try { activo = localStorage.getItem("astar-sonido") !== "0"; } catch (_) { /* sin almacenamiento */ }

  function iniciar() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      ctx = new AC();
      master = ctx.createGain();
      master.gain.value = 0.5;
      master.connect(ctx.destination);
    }
    if (ctx.state === "suspended") ctx.resume();
  }

  const listo = () => activo && ctx && ctx.state === "running";

  function envolvente(g, t, vol, dur, ataque = 0.005) {
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + ataque);
    g.gain.setValueAtTime(vol, t + Math.max(ataque, dur * 0.6));
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  }

  function tono(freq, dur, { tipo = "sine", vol = 0.3, delay = 0, hasta = null, ataque = 0.005 } = {}) {
    if (!listo()) return null;
    const t = ctx.currentTime + delay;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = tipo;
    o.frequency.setValueAtTime(freq, t);
    if (hasta) o.frequency.exponentialRampToValueAtTime(hasta, t + dur);
    envolvente(g, t, vol, dur, ataque);
    o.connect(g).connect(master);
    o.start(t);
    o.stop(t + dur + 0.05);
    return { o, g, t };
  }

  function ruido(dur, { vol = 0.3, delay = 0, filtro = "lowpass", freq = 800, hasta = null, q = 1, ataque = 0.01 } = {}) {
    if (!listo()) return null;
    if (!ruidoBuf) {
      ruidoBuf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
      const d = ruidoBuf.getChannelData(0);
      for (let j = 0; j < d.length; j++) d[j] = Math.random() * 2 - 1;
    }
    const t = ctx.currentTime + delay;
    const s = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
    s.buffer = ruidoBuf;
    s.loop = true;
    f.type = filtro;
    f.frequency.setValueAtTime(freq, t);
    if (hasta) f.frequency.exponentialRampToValueAtTime(hasta, t + dur);
    f.Q.value = q;
    envolvente(g, t, vol, dur, ataque);
    s.connect(f).connect(g).connect(master);
    s.start(t);
    s.stop(t + dur + 0.05);
    return { g, t };
  }

  function modular(param, frecuencia, profundidad, t, dur) {
    const lfo = ctx.createOscillator(), lg = ctx.createGain();
    lfo.frequency.value = frecuencia;
    lg.gain.value = profundidad;
    lfo.connect(lg).connect(param);
    lfo.start(t);
    lfo.stop(t + dur);
  }

  return {
    iniciar,
    get activo() { return activo; },
    alternar() {
      activo = !activo;
      try { localStorage.setItem("astar-sonido", activo ? "1" : "0"); } catch (_) { /* sin almacenamiento */ }
      if (activo) iniciar();
      return activo;
    },
    tick: () => tono(1300, 0.035, { tipo: "triangle", vol: 0.06 }),
    seleccionar: () => {
      tono(660, 0.12, { tipo: "triangle", vol: 0.16 });
      tono(990, 0.14, { tipo: "triangle", vol: 0.12, delay: 0.06 });
    },
    cerrar: () => ruido(0.22, { vol: 0.1, filtro: "bandpass", freq: 1800, hasta: 400, q: 0.8 }),
    nuevo: (j = 0) => {
      const f = 520 * Math.pow(1.19, j);
      tono(f, 0.16, { vol: 0.2, hasta: f * 1.5 });
    },
    mejora: () => {
      tono(880, 0.25, { tipo: "triangle", vol: 0.16 });
      tono(1320, 0.35, { tipo: "triangle", vol: 0.13, delay: 0.08 });
    },
    bloqueado: () => {
      tono(150, 0.25, { vol: 0.32, hasta: 55 });
      ruido(0.14, { vol: 0.1, freq: 300 });
    },
    visitado: () => tono(320, 0.07, { tipo: "square", vol: 0.035 }),
    paso: (j = 0) => ruido(0.07, { vol: 0.16, filtro: "bandpass", freq: j % 2 ? 950 : 700, q: 2 }),
    victoria: () => {
      [523, 659, 784, 1046].forEach((f, j) => tono(f, 0.22, { tipo: "triangle", vol: 0.18, delay: j * 0.11 }));
      [523, 659, 784, 1046].forEach((f) => tono(f, 1.1, { tipo: "triangle", vol: 0.08, delay: 0.5, ataque: 0.02 }));
    },
    terremoto: () => {
      const r = ruido(2.4, { vol: 0.55, freq: 110, hasta: 50, ataque: 0.25 });
      if (r) modular(r.g.gain, 7, 0.25, r.t, 2.4);
      tono(42, 2.2, { vol: 0.35, ataque: 0.3 });
    },
    derrumbe: () => {
      tono(95, 0.3, { vol: 0.22, hasta: 40 });
      ruido(0.35, { vol: 0.16, freq: 600, hasta: 150 });
    },
    helicoptero: (dur = 3) => {
      const r = ruido(dur, { vol: 0.28, freq: 380, ataque: 0.4 });
      if (r) modular(r.g.gain, 12, 0.22, r.t, dur);
    },
    aterrizar: () => tono(300, 0.18, { tipo: "triangle", vol: 0.15, hasta: 600 }),
    sirena: (dur = 2.4) => {
      const s = tono(760, dur, { tipo: "triangle", vol: 0.07, ataque: 0.1 });
      if (s) modular(s.o.frequency, 1.6, 180, s.t, dur);
    },
    correcto: () => {
      tono(784, 0.12, { tipo: "triangle", vol: 0.2 });
      tono(1175, 0.28, { tipo: "triangle", vol: 0.2, delay: 0.1 });
    },
    incorrecto: () => {
      tono(233, 0.18, { tipo: "sawtooth", vol: 0.07 });
      tono(175, 0.32, { tipo: "sawtooth", vol: 0.07, delay: 0.15 });
    },
    pregunta: () => {
      tono(523, 0.1, { tipo: "triangle", vol: 0.12 });
      tono(698, 0.18, { tipo: "triangle", vol: 0.12, delay: 0.09 });
    },
    pintar: () => tono(380 + Math.random() * 240, 0.05, { tipo: "triangle", vol: 0.06 }),
  };
})();
