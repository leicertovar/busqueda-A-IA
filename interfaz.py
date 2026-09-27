"""
Interfaz gráfica animada del algoritmo A* (Tkinter, incluido en Python).

Muestra, iteración por iteración y con animaciones en cada celda:
  - El nodo extraído de la lista abierta (selector que se desplaza con halo pulsante).
  - El paso del nodo a la lista cerrada (transición de color + número de orden).
  - La evaluación de los 4 vecinos (haces hacia cada vecino y reacción de la celda:
    aparece en la lista abierta, mejora su g, está bloqueada o ya estaba cerrada).
  - Lista abierta, lista cerrada, nodos creados y expandidos (contadores animados).
  - Al extraer la meta: el bombero recorre la ruta óptima hasta el superviviente.

Controles: botones, línea de tiempo (clic o arrastre) y teclado
  ← →  paso anterior / siguiente      Espacio  reproducir / pausa
  Inicio / Fin                        + / −    velocidad       A  árbol de búsqueda
"""

from __future__ import annotations

import math
import time
import tkinter as tk
from tkinter import ttk

from astar_rescate import (INICIO, META, TABLERO, Resultado, a_estrella,
                           coste_casilla, formato_num, formato_pos)

# ---------------------------------------------------------------------------
# PALETA
# ---------------------------------------------------------------------------
BG = "#0b1120"
PANEL = "#111a2e"
CARD = "#17223a"
CARD2 = "#1f2c48"
BORDE = "#2a3a5c"
TEXTO = "#e5edf7"
TENUE = "#8fa3bf"
FONDO_TABLERO = "#0e1628"

AZUL = "#3b82f6"
AZUL_CLARO = "#7cb4ff"
MAGENTA = "#e879f9"
VERDE = "#22c55e"
AMBAR = "#f59e0b"
ROJO = "#ef4444"
PIZARRA = "#64748b"

TERRENO = {1: "#eef2f7", 2: "#fde68a", 4: "#fdba74", 7: "#fca5a5",
           "X": "#070c18", "B": "#22c55e", "S": "#ef4444"}
TINTA_CERRADA = "#34435f"
TEXTO_OSCURO = "#1e293b"
TEXTO_CLARO = "#f8fafc"

NOMBRE_TERRENO = {1: "Libre", 2: "Escombros leves", 4: "Grietas / Humo",
                  7: "Fuego parcial / Agua", "B": "Bombero (inicio)",
                  "S": "Superviviente (meta)", "X": "Bloqueado"}


ESCALA = 1.0   # factor de escalado de pantalla (DPI), se calcula al abrir la ventana


def S(px):
    """Convierte píxeles de diseño (a 96 DPI) a píxeles reales de la pantalla."""
    return px * ESCALA


def fuente_px(px, peso="normal", fam="Segoe UI"):
    """Fuente con tamaño en píxeles reales (ya escalados)."""
    return (fam, -int(round(px)), peso)


def fuente(px, peso="normal", fam="Segoe UI"):
    return (fam, -int(round(S(px))), peso)


def _activar_dpi():
    """En Windows con escalado (125 %, 150 %...) evita que la ventana se vea borrosa."""
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# UTILIDADES DE COLOR Y ANIMACIÓN
# ---------------------------------------------------------------------------
def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mezclar(a, b, t):
    t = max(0.0, min(1.0, t))
    ra, ga, ba = _rgb(a)
    rb, gb, bb = _rgb(b)
    return "#%02x%02x%02x" % (round(ra + (rb - ra) * t), round(ga + (gb - ga) * t),
                              round(ba + (bb - ba) * t))


def luminancia(h):
    r, g, b = _rgb(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def suave(t):          # ease-out cúbico
    return 1 - (1 - t) ** 3


def suave_io(t):       # ease-in-out
    return 3 * t * t - 2 * t * t * t


def rebote(t):         # ease-out-back (ligero rebote)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def lineal(t):
    return t


class Animador:
    """Motor de interpolaciones (tweens) a ~60 fps sobre el bucle de Tk."""

    def __init__(self, root, fps=60):
        self.root = root
        self.ms = int(1000 / fps)
        self.tweens = []
        self.continuos = []
        self.root.after(self.ms, self._tick)

    def tween(self, dur, fn, delay=0.0, ease=suave, fin=None):
        self.tweens.append([time.perf_counter() + delay, max(dur, 1e-3), fn, ease, fin])

    def en(self, delay, fn):
        self.tween(1e-3, lambda t: None, delay, lineal, fn)

    def terminar(self):
        """Lleva instantáneamente todas las animaciones pendientes a su estado final."""
        guardia = 0
        while self.tweens and guardia < 20:
            guardia += 1
            lista = sorted(self.tweens, key=lambda x: x[0])
            self.tweens = []
            for _, _, fn, ease, fin in lista:
                fn(ease(1.0))
                if fin:
                    fin()

    def _tick(self):
        ahora = time.perf_counter()
        lista, self.tweens = self.tweens, []
        for tw in lista:
            t0, dur, fn, ease, fin = tw
            if ahora < t0:
                self.tweens.append(tw)
                continue
            t = min(1.0, (ahora - t0) / dur)
            fn(ease(t))
            if t < 1.0:
                self.tweens.append(tw)
            elif fin:
                fin()
        for fn in self.continuos:
            fn(ahora)
        self.root.after(self.ms, self._tick)


def tipo_accion(accion: str):
    if accion.startswith("NUEVO"):
        return "NUEVO", AZUL
    if accion.startswith("MEJOR"):
        return "MEJORA g", AMBAR
    if accion.startswith("BLOQ"):
        return "BLOQUEADO", ROJO
    if accion.startswith("En lista cerrada"):
        return "EN CERRADA", PIZARRA
    return "SIN CAMBIO", "#475569"


# ---------------------------------------------------------------------------
# BOTÓN PLANO
# ---------------------------------------------------------------------------
class Boton(tk.Label):
    def __init__(self, master, texto, comando, ancho=None, acento=False):
        self.c_base = AZUL if acento else CARD2
        self.c_hover = "#5b9bff" if acento else "#2b3b60"
        super().__init__(master, text=texto, bg=self.c_base, fg=TEXTO, cursor="hand2",
                         font=fuente(14, "bold"), padx=int(S(12)), pady=int(S(6)), width=ancho)
        self.comando = comando
        self.bind("<Enter>", lambda e: self.config(bg=self.c_hover))
        self.bind("<Leave>", lambda e: self.config(bg=self.c_base))
        self.bind("<Button-1>", lambda e: self.comando())


# ---------------------------------------------------------------------------
# INTERFAZ PRINCIPAL
# ---------------------------------------------------------------------------
class InterfazAEstrella:
    def __init__(self, resultado: Resultado, root: tk.Tk | None = None):
        self.res = resultado
        self.traza = resultado.traza
        self.total = len(self.traza) - 1
        self.i = 0
        self.vel = 1.0
        self.jugando = False
        self._after_play = None
        self.mostrar_arbol = True

        global ESCALA
        if root is None:
            _activar_dpi()
        self.root = root or tk.Tk()
        self.root.title("A* – Rescate de emergencia post-terremoto")
        self.root.configure(bg=BG)
        ESCALA = max(1.0, self.root.winfo_fpixels("1i") / 96.0)

        sh = self.root.winfo_screenheight()
        self.gap = round(S(4))
        self.cs = int(max(S(46), min(S(84), (sh - S(330)) / 8 - self.gap)))  # celda adaptable
        self.ox, self.oy = S(28), S(24)

        self._precalcular()
        self._estilos()
        self._construir()
        self.anim = Animador(self.root)
        self.anim.continuos.append(self._pulso_selector)
        self._render(0)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ datos
    def _precalcular(self):
        """Estado (g, h, f, padre, abierta/cerrada, orden) de cada celda en cada iteración."""
        self.estados = []
        conocidos = {}
        for e in self.traza:
            if e.actual:
                conocidos[e.actual["pos"]] = dict(e.actual)
            for n in e.abierta:
                conocidos[n["pos"]] = dict(n)
            orden = {p: k + 1 for k, p in enumerate(e.cerrada)}
            abiertos = {n["pos"] for n in e.abierta}
            est = {}
            for p, n in conocidos.items():
                est[p] = dict(n, estado="cerrada" if p in orden else
                              "abierta" if p in abiertos else "?", orden=orden.get(p))
            self.estados.append(est)

    # ------------------------------------------------------------------ geometría
    def _caja(self, pos, infl=0.0):
        f, c = pos
        x1 = self.ox + c * (self.cs + self.gap)
        y1 = self.oy + f * (self.cs + self.gap)
        return x1 - infl, y1 - infl, x1 + self.cs + infl, y1 + self.cs + infl

    def _centro(self, pos):
        x1, y1, x2, y2 = self._caja(pos)
        return (x1 + x2) / 2, (y1 + y2) / 2

    def _centro_interp(self, a, b, t):
        (xa, ya), (xb, yb) = self._centro(a), self._centro(b)
        return xa + (xb - xa) * t, ya + (yb - ya) * t

    @staticmethod
    def _rr(x1, y1, x2, y2, r):
        r = max(1.0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
        return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
                x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]

    def _rr_centro(self, cx, cy, medio, r):
        return self._rr(cx - medio, cy - medio, cx + medio, cy + medio, r)

    # ------------------------------------------------------------------ estilos ttk
    def _estilos(self):
        st = ttk.Style(self.root)
        st.theme_use("clam")
        st.configure("A.Treeview", background=CARD, fieldbackground=CARD, foreground=TEXTO,
                     rowheight=int(S(24)), borderwidth=0, font=("Consolas", 10))
        st.configure("A.Treeview.Heading", background=CARD2, foreground=TENUE, relief="flat",
                     borderwidth=0, font=fuente(12, "bold"))
        st.map("A.Treeview", background=[("selected", CARD2)], foreground=[("selected", TEXTO)])
        st.map("A.Treeview.Heading", background=[("active", CARD2)])
        st.layout("A.Treeview", [("A.Treeview.treearea", {"sticky": "nswe"})])
        st.configure("A.Vertical.TScrollbar", background=CARD2, troughcolor=CARD,
                     bordercolor=CARD, arrowcolor=TENUE, relief="flat")

    # ------------------------------------------------------------------ construcción
    def _tarjeta(self, master, titulo=None, **pack):
        marco = tk.Frame(master, bg=CARD, highlightthickness=1, highlightbackground=BORDE)
        marco.pack(**pack)
        if titulo:
            tk.Label(marco, text=titulo, bg=CARD, fg=TENUE, font=fuente(11, "bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        return marco

    def _construir(self):
        raiz = tk.Frame(self.root, bg=BG)
        raiz.pack(fill="both", expand=True, padx=16, pady=(10, 6))

        # ---------------- columna izquierda: encabezado + tablero + controles
        izq = tk.Frame(raiz, bg=BG)
        izq.pack(side="left", fill="y")

        cab = tk.Frame(izq, bg=BG)
        cab.pack(fill="x")
        tk.Label(cab, text="Rescate post-terremoto  ·  A*", bg=BG, fg=TEXTO,
                 font=fuente(22, "bold")).pack(anchor="w")
        self.lbl_sub = tk.Label(cab, text="f(n) = g(n) + h(n)     h(n) = |x − 7| + |y − 7|  (Manhattan)",
                                bg=BG, fg=TENUE, font=fuente(13))
        self.lbl_sub.pack(anchor="w", pady=(0, 6))

        ancho = self.ox + 8 * (self.cs + self.gap) - self.gap + 12
        alto = self.oy + 8 * (self.cs + self.gap) - self.gap + 12
        marco_t = tk.Frame(izq, bg=FONDO_TABLERO, highlightthickness=1, highlightbackground=BORDE)
        marco_t.pack()
        self.cv = tk.Canvas(marco_t, width=ancho, height=alto, bg=FONDO_TABLERO,
                            highlightthickness=0)
        self.cv.pack(padx=6, pady=6)
        self._dibujar_tablero()
        self.cv.bind("<Motion>", self._hover)
        self.cv.bind("<Leave>", lambda e: self._mostrar_mensaje())

        self.tl = tk.Canvas(izq, width=ancho + S(12), height=S(30), bg=BG, highlightthickness=0)
        self.tl.pack(pady=(8, 2))
        self.tl.bind("<Button-1>", self._click_timeline)
        self.tl.bind("<B1-Motion>", self._click_timeline)

        ctrl = tk.Frame(izq, bg=BG)
        ctrl.pack(fill="x", pady=(2, 0))
        Boton(ctrl, "«", lambda: (self.pausar(), self.ir(0))).pack(side="left", padx=(0, 4))
        Boton(ctrl, "‹", self.anterior).pack(side="left", padx=4)
        self.btn_play = Boton(ctrl, "Reproducir", self.alternar, ancho=10, acento=True)
        self.btn_play.pack(side="left", padx=4)
        Boton(ctrl, "›", self.siguiente).pack(side="left", padx=4)
        Boton(ctrl, "»", lambda: (self.pausar(), self.ir(self.total))).pack(side="left", padx=4)
        self.btn_arbol = Boton(ctrl, "Árbol: sí", self.alternar_arbol)
        self.btn_arbol.config(font=fuente(12, "bold"))
        self.btn_arbol.pack(side="right")
        velf = tk.Frame(ctrl, bg=BG)
        velf.pack(side="right", padx=10)
        tk.Label(velf, text="VELOCIDAD", bg=BG, fg=TENUE, font=fuente(10, "bold")).pack()
        fila_v = tk.Frame(velf, bg=BG)
        fila_v.pack()
        menos = Boton(fila_v, "−", lambda: self._vel_paso(-1))
        menos.config(font=fuente(12, "bold"), pady=0, padx=int(S(8)))
        menos.pack(side="left")
        self.lbl_vel = tk.Label(fila_v, text="1×", bg=BG, fg=TEXTO, font=fuente(13, "bold"),
                                width=5)
        self.lbl_vel.pack(side="left")
        mas = Boton(fila_v, "+", lambda: self._vel_paso(1))
        mas.config(font=fuente(12, "bold"), pady=0, padx=int(S(8)))
        mas.pack(side="left")

        # ---------------- columna derecha: variables del algoritmo
        der = tk.Frame(raiz, bg=BG)
        der.pack(side="left", fill="both", expand=True, padx=(18, 0))

        # tarjetas de contadores
        stats = tk.Frame(der, bg=BG)
        stats.pack(fill="x")
        self.stats = {}
        defs = [("it", "ITERACIÓN", MAGENTA), ("cre", "NODOS CREADOS", AZUL_CLARO),
                ("exp", "NODOS EXPANDIDOS", VERDE), ("ab", "LISTA ABIERTA", AZUL),
                ("ce", "LISTA CERRADA", PIZARRA), ("act", "MEJORAS DE g", AMBAR)]
        for k, (clave, titulo, color) in enumerate(defs):
            t = tk.Frame(stats, bg=CARD, highlightthickness=1, highlightbackground=BORDE)
            t.grid(row=k // 3, column=k % 3, sticky="nsew", padx=(0 if k % 3 == 0 else 8, 0),
                   pady=(0, 8))
            tk.Frame(t, bg=color, width=int(S(4))).pack(side="left", fill="y")
            cuerpo = tk.Frame(t, bg=CARD)
            cuerpo.pack(side="left", fill="both", expand=True, padx=10, pady=5)
            tk.Label(cuerpo, text=titulo, bg=CARD, fg=TENUE, font=fuente(10, "bold"),
                     anchor="w").pack(fill="x")
            lbl = tk.Label(cuerpo, text="0", bg=CARD, fg=TEXTO, font=fuente(24, "bold"), anchor="w")
            lbl.pack(fill="x")
            self.stats[clave] = {"lbl": lbl, "val": 0.0}
        for c in range(3):
            stats.grid_columnconfigure(c, weight=1, uniform="s")

        # nodo actual + vecinos
        fila = tk.Frame(der, bg=BG)
        fila.pack(fill="x")
        nodo = self._tarjeta(fila, "NODO EXTRAÍDO (MENOR f)", side="left", fill="both")
        self.lbl_pos = tk.Label(nodo, text="—", bg=CARD, fg=MAGENTA, font=fuente(30, "bold"),
                                width=6, anchor="w")
        self.lbl_pos.pack(fill="x", padx=12)
        self.lbl_gh = tk.Label(nodo, text="", bg=CARD, fg=TEXTO, font=("Consolas", 11), anchor="w",
                               justify="left")
        self.lbl_gh.pack(fill="x", padx=12, pady=(0, 10))

        vec = self._tarjeta(fila, "VECINOS EVALUADOS  (arriba · abajo · izquierda · derecha)",
                            side="left", fill="both", expand=True, padx=(8, 0))
        cuerpo = tk.Frame(vec, bg=CARD)
        cuerpo.pack(fill="both", expand=True, padx=12, pady=(2, 8))
        self.filas_vec = []
        for r in range(4):
            celdas = []
            for cidx, (w, anc) in enumerate([(9, "w"), (6, "w"), (5, "w"), (6, "w"), (11, "center")]):
                lb = tk.Label(cuerpo, text="", bg=CARD, fg=TEXTO, width=w, anchor=anc,
                              font=("Consolas", 10) if cidx < 4 else fuente(10, "bold"))
                lb.grid(row=r, column=cidx, sticky="w", pady=1, padx=(0, 4))
                celdas.append(lb)
            self.filas_vec.append(celdas)

        # lista abierta
        ab = self._tarjeta(der, None, fill="both", expand=True, pady=(8, 0))
        cab_ab = tk.Frame(ab, bg=CARD)
        cab_ab.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(cab_ab, text="LISTA ABIERTA", bg=CARD, fg=TENUE, font=fuente(11, "bold")).pack(side="left")
        tk.Label(cab_ab, text="  ordenada por f → h → antigüedad   ", bg=CARD, fg="#5d7090",
                 font=fuente(11)).pack(side="left")
        for texto, col in [("● siguiente", MAGENTA), ("● nuevo", AZUL_CLARO), ("● mejorado", AMBAR)]:
            tk.Label(cab_ab, text=texto, bg=CARD, fg=col, font=fuente(11)).pack(side="right", padx=(8, 0))
        cont = tk.Frame(ab, bg=CARD)
        cont.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.tree = ttk.Treeview(cont, columns=("n", "g", "h", "f", "p"), show="headings",
                                 style="A.Treeview", height=6)
        for col, tit, w in [("n", "Nodo", 90), ("g", "g(n)", 70), ("h", "h(n)", 70),
                            ("f", "f(n)", 70), ("p", "Padre", 90)]:
            self.tree.heading(col, text=tit)
            self.tree.column(col, width=int(S(w)), anchor="center", stretch=True)
        sb = ttk.Scrollbar(cont, orient="vertical", command=self.tree.yview,
                           style="A.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("siguiente", background="#2c1d45", foreground=MAGENTA)
        self.tree.tag_configure("nuevo", foreground=AZUL_CLARO)
        self.tree.tag_configure("mejora", foreground=AMBAR)
        self.tree.tag_configure("par", background="#1a263f")

        # lista cerrada
        ce = self._tarjeta(der, "LISTA CERRADA  (orden de expansión)", fill="x", pady=(8, 0))
        self.cv_cerr = tk.Canvas(ce, height=S(4 * 24 + 6), bg=CARD, highlightthickness=0)
        self.cv_cerr.pack(fill="x", padx=12, pady=(2, 8))
        self.cv_cerr.bind("<Configure>", lambda e: self._dibujar_cerrada(self.i))

        # leyenda
        ley = tk.Canvas(der, height=S(24), bg=BG, highlightthickness=0)
        ley.pack(fill="x", pady=(8, 0))
        x = 2
        for col, txt, tipo in [(TERRENO[1], "1 Libre", "f"), (TERRENO[2], "2 Escombros", "f"),
                               (TERRENO[4], "4 Grietas/Humo", "f"), (TERRENO[7], "7 Fuego/Agua", "f"),
                               ("#1e293b", "X Bloqueado", "f"), (AZUL, "Abierta", "o"),
                               (TINTA_CERRADA, "Cerrada", "f"), (MAGENTA, "Actual", "o"),
                               (VERDE, "Ruta", "f")]:
            if tipo == "f":
                ley.create_rectangle(x, S(6), x + S(13), S(19), fill=col, outline="")
            else:
                ley.create_rectangle(x + S(1), S(7), x + S(12), S(18), outline=col, width=S(2))
            t = ley.create_text(x + S(18), S(12), text=txt, anchor="w", fill=TENUE, font=fuente(11))
            x = ley.bbox(t)[2] + S(12)

        # barra de estado
        self.lbl_msg = tk.Label(self.root, text="", bg=PANEL, fg=TENUE, font=fuente(12),
                                anchor="w", padx=int(S(16)), pady=int(S(5)))
        self.lbl_msg.pack(side="bottom", fill="x")

        for tecla, fn in [("<Right>", self.siguiente), ("<Left>", self.anterior),
                          ("<space>", self.alternar), ("<Home>", lambda: self.ir(0)),
                          ("<End>", lambda: self.ir(self.total)), ("<plus>", lambda: self._vel_paso(1)),
                          ("<KP_Add>", lambda: self._vel_paso(1)), ("<minus>", lambda: self._vel_paso(-1)),
                          ("<KP_Subtract>", lambda: self._vel_paso(-1)), ("a", self.alternar_arbol)]:
            self.root.bind(tecla, lambda e, f=fn: f())

    # ------------------------------------------------------------------ tablero
    def _dibujar_tablero(self):
        cv, cs = self.cv, self.cs
        for c in range(8):
            x = self._centro((0, c))[0]
            cv.create_text(x, self.oy / 2, text=str(c), fill=TENUE, font=fuente(12, "bold"))
        for f in range(8):
            y = self._centro((f, 0))[1]
            cv.create_text(self.ox / 2, y, text=str(f), fill=TENUE, font=fuente(12, "bold"))

        self.celdas = {}
        r = cs * 0.14
        for f in range(8):
            for c in range(8):
                pos = (f, c)
                v = TABLERO[f][c]
                x1, y1, x2, y2 = self._caja(pos)
                base = cv.create_polygon(self._rr(x1, y1, x2, y2, r), smooth=True,
                                         fill=TERRENO[v], outline="", tags=("celda",))
                if v == "X":
                    for d in range(-cs, cs, int(S(9))):
                        cv.create_line(x1 + max(d, 0), y1 + max(-d, 0), x1 + min(cs, d + cs),
                                       y1 + min(cs, cs - d), fill="#141d33", width=S(2), tags=("celda",))
                    cv.create_text((x1 + x2) / 2, (y1 + y2) / 2, text="✕", fill="#2b3a58",
                                   font=fuente_px(cs * 0.34, "bold"), tags=("celda",))
                    continue
                d = {"base": base, "terreno": v}
                d["anillo"] = cv.create_polygon(self._rr(x1 + 2, y1 + 2, x2 - 2, y2 - 2, r),
                                                smooth=True, fill="", outline=AZUL, width=S(3),
                                                state="hidden", tags=("anillo",))
                d["flash"] = cv.create_polygon(self._rr(x1, y1, x2, y2, r), smooth=True, fill="",
                                               outline=ROJO, width=S(3), state="hidden", tags=("flash",))
                etiqueta = {"B": "B · 1", "S": "S · 1"}.get(v, f"c={v}")
                d["t_coste"] = cv.create_text(x1 + 5, y1 + 4, text=etiqueta, anchor="nw",
                                              font=fuente_px(max(S(9), cs * 0.16), "bold"), tags=("texto",))
                d["t_gh"] = cv.create_text((x1 + x2) / 2, y1 + cs * 0.55, text="",
                                           font=fuente_px(max(S(9), cs * 0.155)), tags=("texto",))
                d["t_f"] = cv.create_text((x1 + x2) / 2, y1 + cs * 0.80, text="",
                                          font=fuente_px(max(S(11), cs * 0.22), "bold"), tags=("texto",))
                bw, bh = cs * 0.42, cs * 0.25
                d["b_rect"] = cv.create_polygon(self._rr(x2 - bw - 3, y1 + 3, x2 - 3, y1 + 3 + bh, 5),
                                                smooth=True, fill=PIZARRA, outline="",
                                                state="hidden", tags=("insignia",))
                d["b_txt"] = cv.create_text(x2 - 3 - bw / 2, y1 + 3 + bh / 2, text="", fill=TEXTO_CLARO,
                                            font=fuente_px(max(S(8), cs * 0.15), "bold"), state="hidden",
                                            tags=("insignia",))
                self.celdas[pos] = d

        m = self.cs / 2
        cx, cy = self._centro(INICIO)
        self.halo = self.cv.create_polygon(self._rr_centro(cx, cy, m + 2, r + 2), smooth=True, fill="",
                                           outline=MAGENTA, width=S(2), state="hidden", tags=("selector",))
        self.selector = self.cv.create_polygon(self._rr_centro(cx, cy, m + 1, r + 1), smooth=True,
                                               fill="", outline=MAGENTA, width=S(4), state="hidden",
                                               tags=("selector",))
        self.sel_pos = (cx, cy)

    def _z(self):
        for tag in ("anillo", "flash", "camino", "arbol", "haz", "texto", "insignia", "selector", "ficha"):
            self.cv.tag_raise(tag)

    def _pintar(self, pos, info, k=0.0, verde=0.0, alfa=1.0):
        """Colorea una celda: k = mezcla hacia 'cerrada', verde = ruta, alfa = opacidad del texto."""
        d = self.celdas[pos]
        cv = self.cv
        fill = TERRENO[d["terreno"]]
        if d["terreno"] not in ("B", "S"):
            fill = mezclar(fill, TINTA_CERRADA, 0.8 * k)
        fill = mezclar(fill, "#16a34a", 0.7 * verde)
        cv.itemconfig(d["base"], fill=fill)
        tinta = TEXTO_OSCURO if luminancia(fill) > 0.55 else TEXTO_CLARO
        cv.itemconfig(d["t_coste"], fill=mezclar(fill, tinta, 0.62))
        if info:
            cv.itemconfig(d["t_gh"], text=f"g={formato_num(info['g'])}  h={info['h']}",
                          fill=mezclar(fill, tinta, 0.85 * alfa))
            cv.itemconfig(d["t_f"], text=f"f={formato_num(info['f'])}", fill=mezclar(fill, tinta, alfa))
        else:
            cv.itemconfig(d["t_gh"], text="")
            cv.itemconfig(d["t_f"], text="")
        return fill

    def _anillo(self, pos, escala=1.0, color=AZUL, visible=True):
        d = self.celdas[pos]
        cx, cy = self._centro(pos)
        medio = (self.cs / 2 - 2) * escala
        self.cv.coords(d["anillo"], *self._rr_centro(cx, cy, medio, self.cs * 0.14 * escala))
        self.cv.itemconfig(d["anillo"], outline=color, state="normal" if visible else "hidden")

    def _insignia(self, pos, orden, escala=1.0):
        d = self.celdas[pos]
        if not orden:
            self.cv.itemconfig(d["b_rect"], state="hidden")
            self.cv.itemconfig(d["b_txt"], state="hidden")
            return
        x1, y1, x2, _ = self._caja(pos)
        bw, bh = self.cs * 0.42 * escala, self.cs * 0.25 * escala
        cx, cy = x2 - 3 - self.cs * 0.21, y1 + 3 + self.cs * 0.125
        self.cv.coords(d["b_rect"], *self._rr(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2, 5))
        self.cv.coords(d["b_txt"], cx, cy)
        self.cv.itemconfig(d["b_rect"], state="normal", fill=PIZARRA)
        self.cv.itemconfig(d["b_txt"], state="normal" if escala > 0.5 else "hidden", text=f"#{orden}")

    def _mover_selector(self, cx, cy):
        self.sel_pos = (cx, cy)
        m = self.cs / 2
        self.cv.coords(self.selector, *self._rr_centro(cx, cy, m + 1, self.cs * 0.14 + 1))

    def _pulso_selector(self, ahora):
        if self.cv.itemcget(self.selector, "state") == "hidden":
            self.cv.itemconfig(self.halo, state="hidden")
            return
        fase = (ahora % 1.3) / 1.3
        cx, cy = self.sel_pos
        m = self.cs / 2 + S(2) + S(7) * suave(fase)
        self.cv.coords(self.halo, *self._rr_centro(cx, cy, m, self.cs * 0.14 + 4))
        self.cv.itemconfig(self.halo, state="normal", outline=mezclar(MAGENTA, FONDO_TABLERO, fase))
        self.cv.itemconfig(self.selector, width=S(3.5 + 1.2 * math.sin(fase * 2 * math.pi)))

    def _flash(self, pos, color, delay):
        d = self.celdas.get(pos)
        if d is None:          # casilla X: destello sobre la celda bloqueada
            x1, y1, x2, y2 = self._caja(pos)
            item = self.cv.create_polygon(self._rr(x1, y1, x2, y2, self.cs * 0.14), smooth=True,
                                          fill="", outline=color, width=S(3), state="hidden",
                                          tags=("haz",))
            temporal = True
        else:
            item, temporal = d["flash"], False

        def paso(t):
            infl = S(1 + 5 * t)
            x1, y1, x2, y2 = self._caja(pos, infl)
            self.cv.coords(item, *self._rr(x1, y1, x2, y2, self.cs * 0.14 + infl))
            self.cv.itemconfig(item, state="normal", outline=mezclar(color, FONDO_TABLERO, t))

        def fin():
            if temporal:
                self.cv.delete(item)
            else:
                self.cv.itemconfig(item, state="hidden")

        self.anim.tween(self._d(0.45), paso, delay, suave, fin)

    def _dibujar_arbol(self, est):
        self.cv.delete("arbol")
        if not self.mostrar_arbol:
            return
        for pos, n in est.items():
            if n["padre"] is None:
                continue
            (f0, c0), (f1, c1) = n["padre"], pos
            df, dc = f1 - f0, c1 - c0
            xa, ya = self._centro(n["padre"])
            xb, yb = self._centro(pos)
            off = self.cs * 0.5 - S(7)
            if df:   # vertical: a la derecha del centro
                x = xa + self.cs * 0.33
                self.cv.create_line(x, ya + df * off, x, yb - df * off, fill="#475a7a", width=S(2),
                                    arrow="last", arrowshape=(S(7), S(8), S(3)), tags=("arbol",))
            else:    # horizontal: por encima del centro
                y = ya - self.cs * 0.18
                self.cv.create_line(xa + dc * off, y, xb - dc * off, y, fill="#475a7a", width=S(2),
                                    arrow="last", arrowshape=(S(7), S(8), S(3)), tags=("arbol",))

    def _conector(self, a, b, t=1.0):
        (xa, ya), (xb, yb) = self._centro(a), self._centro(b)
        dx, dy = (xb - xa), (yb - ya)
        lon = math.hypot(dx, dy)
        ux, uy = dx / lon, dy / lon
        s = self.cs / 2 - S(9)
        x0, y0 = xa + ux * s, ya + uy * s
        x1 = x0 + (xb - ux * s - x0) * t
        y1 = y0 + (yb - uy * s - y0) * t
        return x0, y0, x1, y1

    def _dibujar_camino_completo(self):
        self.cv.delete("camino")
        self.cv.delete("ficha")
        cam = self.res.camino
        for a, b in zip(cam, cam[1:]):
            self.cv.create_line(*self._conector(a, b), fill=VERDE, width=S(5), capstyle="round",
                                tags=("camino",))
        self._crear_ficha(*self._centro(cam[-1]))

    def _crear_ficha(self, cx, cy):
        self.cv.delete("ficha")
        r = self.cs * 0.2
        self.cv.create_oval(cx - r - S(4), cy - r - S(4), cx + r + S(4), cy + r + S(4), fill="",
                            outline="#bbf7d0", width=S(2), tags=("ficha", "ficha_halo"))
        self.cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#15803d", outline=TEXTO_CLARO,
                            width=S(2), tags=("ficha", "ficha_cuerpo"))
        self.cv.create_text(cx, cy, text="B", fill=TEXTO_CLARO, font=fuente_px(r * 1.1, "bold"),
                            tags=("ficha", "ficha_txt"))
        self.ficha_pos = (cx, cy)

    def _mover_ficha(self, cx, cy):
        x0, y0 = self.ficha_pos
        self.cv.move("ficha", cx - x0, cy - y0)
        self.ficha_pos = (cx, cy)

    # ------------------------------------------------------------------ render instantáneo
    def _render(self, i, panel=True):
        e = self.traza[i]
        est = self.estados[i]
        final = i == self.total and self.res.encontrado
        camino = set(self.res.camino) if final else set()
        self.cv.delete("haz")
        for pos, d in self.celdas.items():
            info = est.get(pos)
            cerrada = bool(info and info["estado"] == "cerrada")
            self._pintar(pos, info, 1.0 if cerrada else 0.0, 1.0 if pos in camino else 0.0)
            self.cv.itemconfig(d["flash"], state="hidden")
            self._anillo(pos, visible=bool(info and info["estado"] == "abierta"))
            self._insignia(pos, info["orden"] if cerrada else None)
        if e.actual:
            self._mover_selector(*self._centro(e.actual["pos"]))
            self.cv.itemconfig(self.selector, state="normal")
        else:
            self.cv.itemconfig(self.selector, state="hidden")
        self._dibujar_arbol(est)
        if final:
            self._dibujar_camino_completo()
        else:
            self.cv.delete("camino")
            self.cv.delete("ficha")
        self._z()
        if panel:
            self._actualizar_panel(i, animado=False)
        self._dibujar_timeline()

    # ------------------------------------------------------------------ panel derecho
    def _set_stat(self, clave, valor, animado):
        s = self.stats[clave]
        fmt = (lambda v: f"{int(round(v))} / {self.total}") if clave == "it" else (lambda v: str(int(round(v))))
        inicio = s["val"]
        s["val"] = float(valor)
        if not animado or inicio == valor:
            s["lbl"].config(text=fmt(valor))
            return

        def paso(t):
            s["lbl"].config(text=fmt(inicio + (valor - inicio) * t))
        self.anim.tween(self._d(0.5), paso, 0, suave)

    def _actualizar_panel(self, i, animado=False, retrasos=None):
        e = self.traza[i]
        for clave, valor in [("it", e.iteracion), ("cre", e.creados), ("exp", e.expandidos),
                             ("ab", len(e.abierta)), ("ce", len(e.cerrada)), ("act", e.actualizados)]:
            self._set_stat(clave, valor, animado)

        if e.actual:
            a = e.actual
            self.lbl_pos.config(text=formato_pos(a["pos"]), fg=VERDE if e.es_meta else MAGENTA)
            self.lbl_gh.config(text=f"g = {formato_num(a['g'])}   h = {a['h']}   f = {formato_num(a['f'])}\n"
                                    f"padre: {formato_pos(a['padre']) if a['padre'] else '—'}")
            if animado:
                col = VERDE if e.es_meta else MAGENTA
                self.anim.tween(self._d(0.4), lambda t: self.lbl_pos.config(fg=mezclar(CARD, col, t)))
        else:
            self.lbl_pos.config(text=formato_pos(INICIO), fg=AZUL_CLARO)
            self.lbl_gh.config(text=f"Inicialización: g = 0   h = {self.traza[0].abierta[0]['h']}"
                                    f"\nen lista abierta")

        for r, celdas in enumerate(self.filas_vec):
            for lb in celdas:
                lb.config(text="", bg=CARD)
            if r < len(e.vecinos):
                v = e.vecinos[r]
                if animado and retrasos:
                    self.anim.en(retrasos[r], lambda r=r, v=v: self._fila_vecino(r, v))
                else:
                    self._fila_vecino(r, v)
        if e.es_meta:
            self.filas_vec[0][0].config(text="Meta alcanzada: fin de la búsqueda", fg=VERDE,
                                        width=0, anchor="w")
        else:
            self.filas_vec[0][0].config(width=9)

        self._llenar_arbol_abierta(e)
        self._dibujar_cerrada(i, animado)
        self._mostrar_mensaje()
        final = i == self.total and self.res.encontrado
        if final:
            self.lbl_sub.config(text=f"✔  Superviviente rescatado  ·  coste total {formato_num(self.res.coste)}"
                                     f"  ·  {len(self.res.camino) - 1} movimientos", fg=VERDE)
        else:
            self.lbl_sub.config(text="f(n) = g(n) + h(n)     h(n) = |x − 7| + |y − 7|  (Manhattan)",
                                fg=TENUE)

    def _fila_vecino(self, r, v):
        tipo, color = tipo_accion(v["accion"])
        textos = [v["dir"], formato_pos(v["pos"]), f"c={formato_num(v['coste_paso'])}",
                  f"f={formato_num(v['f'])}" if v["f"] is not None else "f= –"]
        for lb, t in zip(self.filas_vec[r][:4], textos):
            lb.config(text=t, fg=TEXTO if t != textos[0] else TENUE)
        self.filas_vec[r][4].config(text=tipo, bg=color, fg=TEXTO_CLARO)

    def _llenar_arbol_abierta(self, e):
        nuevos = {v["pos"] for v in e.vecinos if v["accion"].startswith("NUEVO")}
        mejorados = {v["pos"] for v in e.vecinos if v["accion"].startswith("MEJOR")}
        self.tree.delete(*self.tree.get_children())
        for k, n in enumerate(e.abierta):
            tags = []
            if k == 0 and not e.es_meta:
                tags.append("siguiente")
            elif n["pos"] in mejorados:
                tags.append("mejora")
            elif n["pos"] in nuevos:
                tags.append("nuevo")
            if k % 2 == 1:
                tags.append("par")
            self.tree.insert("", "end", values=(formato_pos(n["pos"]), formato_num(n["g"]), n["h"],
                                                formato_num(n["f"]),
                                                formato_pos(n["padre"]) if n["padre"] else "—"),
                             tags=tags)

    def _dibujar_cerrada(self, i, animado=False):
        cv = self.cv_cerr
        cv.delete("all")
        e = self.traza[i]
        ancho = max(cv.winfo_width(), 300)
        pw, ph, g = S(54), S(20), S(5)
        por_fila = max(1, (ancho + g) // (pw + g))
        for k, p in enumerate(e.cerrada):
            x = (k % por_fila) * (pw + g)
            y = S(3) + (k // por_fila) * (ph + S(4))
            ultimo = k == len(e.cerrada) - 1
            es_meta = p == META and e.es_meta
            fill = "#14532d" if es_meta else "#3a1f4d" if ultimo else CARD2
            borde = VERDE if es_meta else MAGENTA if ultimo else ""
            item = cv.create_polygon(self._rr(x, y, x + pw, y + ph, 7), smooth=True, fill=fill,
                                     outline=borde, width=S(1.5))
            txt = cv.create_text(x + pw / 2, y + ph / 2, text=formato_pos(p), fill=TEXTO,
                                 font=("Consolas", 9, "bold" if ultimo else "normal"))
            if ultimo and animado:
                def paso(t, item=item, txt=txt, fill=fill):
                    cv.itemconfig(item, fill=mezclar(CARD, fill, t))
                    cv.itemconfig(txt, fill=mezclar(CARD, TEXTO, t))
                self.anim.tween(self._d(0.5), paso, self._d(0.2))

    def _mostrar_mensaje(self, texto=None):
        if texto is None:
            e = self.traza[self.i]
            texto = f"Iteración {e.iteracion}:  {e.mensaje}"
        self.lbl_msg.config(text=texto)

    def _hover(self, ev):
        c = int((ev.x - self.ox) // (self.cs + self.gap))
        f = int((ev.y - self.oy) // (self.cs + self.gap))
        if not (0 <= f < 8 and 0 <= c < 8):
            self._mostrar_mensaje()
            return
        pos = (f, c)
        v = TABLERO[f][c]
        coste = formato_num(coste_casilla(TABLERO, pos))
        partes = [f"Casilla {formato_pos(pos)}", f"{NOMBRE_TERRENO[v]} (coste {coste})"]
        info = self.estados[self.i].get(pos)
        if info:
            partes.append(f"g={formato_num(info['g'])}  h={info['h']}  f={formato_num(info['f'])}")
            partes.append(f"padre {formato_pos(info['padre'])}" if info["padre"] else "nodo inicial")
            partes.append(f"LISTA CERRADA #{info['orden']}" if info["estado"] == "cerrada" else "LISTA ABIERTA")
        elif v != "X":
            partes.append("aún no generado")
        self._mostrar_mensaje("   ·   ".join(partes))

    # ------------------------------------------------------------------ línea de tiempo
    def _dibujar_timeline(self):
        tl = self.tl
        tl.delete("all")
        w = int(float(tl["width"]))
        x0, x1, y = S(14), w - S(14), S(15)
        paso = (x1 - x0) / max(self.total, 1)
        xi = x0 + self.i * paso
        tl.create_line(x0, y, x1, y, fill=CARD2, width=S(4), capstyle="round")
        tl.create_line(x0, y, xi, y, fill=AZUL, width=S(4), capstyle="round")
        for k in range(self.total + 1):
            x = x0 + k * paso
            col = AZUL_CLARO if k <= self.i else "#34466b"
            tl.create_oval(x - S(2), y - S(2), x + S(2), y + S(2), fill=col, outline="")
        col = VERDE if self.i == self.total else MAGENTA
        tl.create_oval(xi - S(8), y - S(8), xi + S(8), y + S(8), fill=BG, outline=col, width=S(3))
        tl.create_oval(xi - S(3), y - S(3), xi + S(3), y + S(3), fill=col, outline="")

    def _click_timeline(self, ev):
        w = int(float(self.tl["width"]))
        x0, x1 = S(14), w - S(14)
        k = round((ev.x - x0) / ((x1 - x0) / max(self.total, 1)))
        k = max(0, min(self.total, k))
        if k != self.i:
            self.pausar()
            self.ir(k)

    # ------------------------------------------------------------------ velocidad
    def _d(self, s):
        return s / self.vel

    VELOCIDADES = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

    def _vel_paso(self, signo):
        k = self.VELOCIDADES.index(self.vel) if self.vel in self.VELOCIDADES else 3
        self.vel = self.VELOCIDADES[max(0, min(len(self.VELOCIDADES) - 1, k + signo))]
        self.lbl_vel.config(text=f"{self.vel:g}×")

    # ------------------------------------------------------------------ navegación
    def ir(self, k):
        self.anim.terminar()
        self.i = max(0, min(self.total, k))
        self._render(self.i)

    def anterior(self):
        self.pausar()
        self.ir(self.i - 1)

    def siguiente(self):
        self.pausar()
        self._paso_animado()

    def alternar(self):
        if self.jugando:
            self.pausar()
        else:
            self.jugando = True
            self.btn_play.config(text="Pausa")
            if self.i >= self.total:
                self.ir(0)
            self._jugar()

    def pausar(self):
        self.jugando = False
        self.btn_play.config(text="Reproducir")
        if self._after_play:
            self.root.after_cancel(self._after_play)
            self._after_play = None

    def _jugar(self):
        self._after_play = None
        if not self.jugando:
            return
        if self.i >= self.total:
            self.pausar()
            return
        dur = self._paso_animado()
        self._after_play = self.root.after(int((dur + self._d(0.25)) * 1000), self._jugar)

    def alternar_arbol(self):
        self.mostrar_arbol = not self.mostrar_arbol
        self.btn_arbol.config(text=f"Árbol: {'sí' if self.mostrar_arbol else 'no'}")
        self._dibujar_arbol(self.estados[self.i])
        self._z()

    # ------------------------------------------------------------------ paso animado
    def _paso_animado(self) -> float:
        """Anima la transición de la iteración i a la i+1. Devuelve su duración (s)."""
        self.anim.terminar()
        if self.i >= self.total:
            return 0.0
        i1 = self.i + 1
        e = self.traza[i1]
        est1 = self.estados[i1]
        est0 = self.estados[self.i]
        self.i = i1
        d = self._d
        self.cv.delete("haz")

        actual = e.actual["pos"]
        info_act = est1[actual]

        # 1. el selector se desliza hasta el nodo de menor f
        origen = self.sel_pos
        destino = self._centro(actual)
        if self.cv.itemcget(self.selector, "state") == "hidden":
            origen = destino
        self.cv.itemconfig(self.selector, state="normal")

        def mover(t):
            self._mover_selector(origen[0] + (destino[0] - origen[0]) * t,
                                 origen[1] + (destino[1] - origen[1]) * t)
        self.anim.tween(d(0.3), mover, 0, suave_io)

        # 2. el nodo pasa de la lista abierta a la lista cerrada
        def cerrar(t):
            fill = self._pintar(actual, info_act, k=t)
            self._anillo(actual, escala=1 - 0.15 * t, color=mezclar(AZUL, fill, t), visible=t < 1)
        self.anim.tween(d(0.35), cerrar, d(0.2), suave)
        self.anim.tween(d(0.35), lambda t: self._insignia(actual, info_act["orden"], max(t, 0.01)),
                        d(0.45), rebote)

        # 3. evaluación de los vecinos (haces + reacción de cada celda)
        inicio = d(0.55)
        escalon = d(0.2)
        retrasos = [inicio + j * escalon + d(0.15) for j in range(len(e.vecinos))]
        self._actualizar_panel(i1, animado=True, retrasos=retrasos)

        for j, v in enumerate(e.vecinos):
            t0 = inicio + j * escalon
            tipo, color = tipo_accion(v["accion"])
            self._animar_haz(actual, v["pos"], color, t0)
            pos = v["pos"]
            if tipo == "NUEVO":
                info = est1[pos]
                self.cv.itemconfig(self.celdas[pos]["anillo"], state="hidden")

                def aparecer(t, pos=pos, info=info):
                    self._pintar(pos, info, 0.0, 0.0, alfa=min(1.0, t * 1.4))
                    self._anillo(pos, escala=0.35 + 0.65 * t, visible=True)
                self.anim.tween(d(0.45), aparecer, t0 + d(0.15), rebote)
                self._flash(pos, AZUL_CLARO, t0 + d(0.15))
            elif tipo == "MEJORA g":
                viejo, nuevo = est0.get(pos), est1[pos]

                def mejorar(t, pos=pos, viejo=viejo, nuevo=nuevo):
                    info = nuevo if t > 0.5 else viejo
                    self._pintar(pos, info, 0.0, 0.0, alfa=abs(2 * t - 1))
                self.anim.tween(d(0.5), mejorar, t0 + d(0.15), lineal)
                self._flash(pos, AMBAR, t0 + d(0.15))
            elif tipo == "BLOQUEADO":
                self._flash(pos, ROJO, t0 + d(0.15))
            else:
                self._flash(pos, "#94a3b8", t0 + d(0.15))

        fin = inicio + len(e.vecinos) * escalon + d(0.45)

        if e.es_meta:
            fin = self._animar_ruta(d(0.8))

        def cierre():
            self.cv.delete("haz")
            self._render(i1, panel=False)
        self.anim.en(fin, cierre)
        self._dibujar_timeline()
        self._z()
        return fin

    def _animar_haz(self, a, b, color, t0):
        d = self._d
        (xa, ya), (xb, yb) = self._centro(a), self._centro(b)
        dx, dy = xb - xa, yb - ya
        s = self.cs * 0.28
        x0, y0 = xa + dx / (self.cs + self.gap) * s, ya + dy / (self.cs + self.gap) * s
        x1f = xb - dx / (self.cs + self.gap) * s
        y1f = yb - dy / (self.cs + self.gap) * s
        item = self.cv.create_line(x0, y0, x0, y0, fill=color, width=S(4), capstyle="round",
                                   arrow="last", arrowshape=(S(10), S(12), S(5)), state="hidden", tags=("haz",))

        def crecer(t):
            self.cv.coords(item, x0, y0, x0 + (x1f - x0) * t, y0 + (y1f - y0) * t)
            self.cv.itemconfig(item, state="normal")

        def desvanecer(t):
            self.cv.itemconfig(item, fill=mezclar(color, FONDO_TABLERO, t))
        self.anim.tween(d(0.2), crecer, t0, suave)
        self.anim.tween(d(0.35), desvanecer, t0 + d(0.55), lineal,
                        lambda: self.cv.delete(item))
        self.cv.tag_raise("haz")
        self.cv.tag_raise("texto")
        self.cv.tag_raise("insignia")
        self.cv.tag_raise("selector")

    def _animar_ruta(self, t_inicio) -> float:
        """El bombero recorre la ruta óptima; las celdas se tiñen de verde."""
        d = self._d
        cam = self.res.camino
        est = self.estados[self.total]
        seg = d(0.17)
        self.cv.delete("camino")
        self.anim.en(t_inicio, lambda: (self._crear_ficha(*self._centro(cam[0])), self._z()))

        def teñir(pos, t):
            info = est.get(pos)
            k = 1.0 if info and info["estado"] == "cerrada" else 0.0
            self._pintar(pos, info, k, verde=t)

        self.anim.tween(d(0.3), lambda t: teñir(cam[0], t), t_inicio)
        for j in range(1, len(cam)):
            a, b = cam[j - 1], cam[j]
            t0 = t_inicio + d(0.2) + (j - 1) * seg
            linea = {"id": None}

            def avanzar(t, a=a, b=b, linea=linea):
                if linea["id"] is None:
                    linea["id"] = self.cv.create_line(*self._conector(a, b, 0.01), fill=VERDE, width=S(5),
                                                      capstyle="round", tags=("camino",))
                    self._z()
                self.cv.coords(linea["id"], *self._conector(a, b, t))
                self._mover_ficha(*self._centro_interp(a, b, t))
            self.anim.tween(seg, avanzar, t0, suave_io)
            self.anim.tween(d(0.3), lambda t, b=b: teñir(b, t), t0 + seg * 0.6)
        fin = t_inicio + d(0.2) + (len(cam) - 1) * seg + d(0.4)

        # pulso de celebración sobre la meta
        def celebrar(t):
            self._flash_meta(t)
        self.anim.tween(d(0.9), celebrar, fin - d(0.3), lineal)
        return fin + d(0.6)

    def _flash_meta(self, t):
        d = self.celdas[META]
        infl = S(2 + 10 * t)
        x1, y1, x2, y2 = self._caja(META, infl)
        self.cv.coords(d["flash"], *self._rr(x1, y1, x2, y2, self.cs * 0.14 + infl))
        self.cv.itemconfig(d["flash"], state="normal" if t < 1 else "hidden",
                           outline=mezclar(VERDE, FONDO_TABLERO, t))

    # ------------------------------------------------------------------
    def mostrar(self):
        self.root.mainloop()


if __name__ == "__main__":
    InterfazAEstrella(a_estrella()).mostrar()
