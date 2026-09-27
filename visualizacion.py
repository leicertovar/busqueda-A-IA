"""
Visualización del algoritmo A* para el rescate post-terremoto.

- Representación gráfica del tablero 8x8 (colores iguales al enunciado).
- Visualización del espacio de búsqueda: qué casillas explora y en qué orden.
- Variables importantes en cada iteración: lista abierta, lista cerrada,
  nodos creados y nodos expandidos.
- Visor interactivo paso a paso (botones / teclado) y animación GIF.
"""

from __future__ import annotations

import os

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.widgets import Button, Slider

from astar_rescate import (INF, INICIO, META, TABLERO, Resultado, a_estrella,
                           coste_casilla, formato_num, formato_pos,
                           heuristica_cero, manhattan)

# Colores del enunciado ------------------------------------------------------
COLOR_CELDA = {
    1: "#f8fafc",    # Libre
    2: "#fef08a",    # Escombros leves
    4: "#fed7aa",    # Grietas / Humo
    7: "#fca5a5",    # Fuego parcial / Agua
    "X": "#1e293b",  # Bloqueado
    "B": "#22c55e",  # Bombero
    "S": "#ef4444",  # Superviviente
}
COLOR_ABIERTA = "#2563eb"
COLOR_CERRADA = "#64748b"
COLOR_ACTUAL = "#d946ef"
COLOR_CAMINO = "#16a34a"
COLOR_TITULO = "#1e3a8a"

FONDO = "#f4f7f9"


def _color(valor):
    return COLOR_CELDA.get(valor, "#ffffff")


def _etiqueta(valor):
    if valor == "B":
        return "B (1)"
    if valor == "S":
        return "S (1)"
    return str(valor)


def _preparar_ejes(ax, titulo=None):
    ax.set_xlim(0, 8)
    ax.set_ylim(8, 0)            # fila 0 arriba, igual que la tabla del enunciado
    ax.set_aspect("equal")
    ax.set_xticks([c + 0.5 for c in range(8)])
    ax.set_xticklabels(range(8))
    ax.set_yticks([f + 0.5 for f in range(8)])
    ax.set_yticklabels(range(8))
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")
    ax.set_xlabel("Columna (C)", fontsize=9)
    ax.set_ylabel("Fila (F)", fontsize=9)
    ax.tick_params(length=0, labelsize=9)
    for s in ax.spines.values():
        s.set_visible(False)
    if titulo:
        ax.set_title(titulo, fontsize=12, fontweight="bold", color=COLOR_TITULO, pad=26)


def _fondo_tablero(ax, tablero=TABLERO, etiquetas=True, alpha=1.0, esquina=False):
    for f in range(8):
        for c in range(8):
            v = tablero[f][c]
            ax.add_patch(patches.Rectangle((c, f), 1, 1, facecolor=_color(v),
                                           edgecolor="#cbd5e1", lw=1, alpha=alpha))
            if etiquetas:
                color_txt = "white" if v in ("X", "B", "S") else "#7c2d12" if v in (2, 4, 7) else "#334155"
                if esquina and v != "X":   # etiqueta arriba a la izquierda (deja libre el centro)
                    ax.text(c + 0.08, f + 0.22, _etiqueta(v), ha="left", va="center",
                            fontsize=9.5, fontweight="bold", color=color_txt)
                else:
                    ax.text(c + 0.5, f + 0.5, _etiqueta(v), ha="center", va="center",
                            fontsize=11, fontweight="bold", color=color_txt)


def _dibujar_camino(ax, camino, color=COLOR_CAMINO, lw=4):
    xs = [c + 0.5 for _, c in camino]
    ys = [f + 0.5 for f, _ in camino]
    ax.plot(xs, ys, color=color, lw=lw, alpha=0.85, solid_capstyle="round", zorder=5)
    for (f0, c0), (f1, c1) in zip(camino, camino[1:]):
        ax.annotate("", xy=(c1 + 0.5, f1 + 0.5), xytext=(c0 + 0.5, f0 + 0.5),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=0, mutation_scale=16),
                    zorder=6)


def _leyenda_tablero(fig, y=0.02):
    items = [
        (COLOR_CELDA["B"], "B: Bombero (0,0)"),
        (COLOR_CELDA["S"], "S: Superviviente (7,7)"),
        (COLOR_CELDA["X"], "X: Bloqueado (∞)"),
        (COLOR_CELDA[1], "1: Libre"),
        (COLOR_CELDA[2], "2: Escombros leves"),
        (COLOR_CELDA[4], "4: Grietas / Humo"),
        (COLOR_CELDA[7], "7: Fuego parcial / Agua"),
    ]
    handles = [patches.Patch(facecolor=col, edgecolor="#94a3b8", label=t) for col, t in items]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8.5,
               frameon=False, bbox_to_anchor=(0.5, y))


# ---------------------------------------------------------------------------
# FIGURAS ESTÁTICAS
# ---------------------------------------------------------------------------
def figura_tablero_inicial(ruta):
    fig, ax = plt.subplots(figsize=(7, 7.6), facecolor=FONDO)
    _preparar_ejes(ax, "Tablero 8 × 8 – Matriz de terreno y costes")
    _fondo_tablero(ax)
    _leyenda_tablero(fig)
    fig.subplots_adjust(bottom=0.14, top=0.88)
    fig.savefig(ruta, dpi=160, facecolor=FONDO)
    plt.close(fig)


def dibujar_estado(ax, estado, resultado: Resultado, mostrar_camino=False, tablero=TABLERO):
    """Dibuja el tablero con la lista abierta, la lista cerrada y el nodo actual."""
    ax.clear()
    _preparar_ejes(ax)
    _fondo_tablero(ax, tablero, etiquetas=False, alpha=0.9)

    cerradas = {p: i + 1 for i, p in enumerate(estado.cerrada)}
    abiertas = {n["pos"]: n for n in estado.abierta}
    actual = estado.actual["pos"] if estado.actual else None

    # Nodos conocidos hasta esta iteración (g, h, f que tenían en ese momento)
    conocidos = {}
    for e in resultado.traza[: estado.iteracion + 1]:
        if e.actual:
            conocidos[e.actual["pos"]] = e.actual
        for n in e.abierta:
            conocidos[n["pos"]] = n
    for n in estado.abierta:
        conocidos[n["pos"]] = n

    # Aristas del árbol de búsqueda (padre -> hijo), dibujadas cruzando el borde
    # entre ambas casillas para no tapar los valores g, h, f
    for pos, n in conocidos.items():
        if n["padre"] is not None:
            (f0, c0), (f1, c1) = n["padre"], pos
            df, dc = f1 - f0, c1 - c0
            desde = (c0 + 0.5 + 0.36 * dc, f0 + 0.5 + 0.36 * df + (0.0 if df else -0.2))
            hasta = (c1 + 0.5 - 0.36 * dc, f1 + 0.5 - 0.36 * df + (0.0 if df else -0.2))
            if df:
                desde = (desde[0] + 0.3, desde[1])
                hasta = (hasta[0] + 0.3, hasta[1])
            ax.annotate("", xy=hasta, xytext=desde,
                        arrowprops=dict(arrowstyle="-|>", color="#475569", lw=1.2,
                                        mutation_scale=10, shrinkA=0, shrinkB=0), zorder=5)

    for f in range(8):
        for c in range(8):
            v = tablero[f][c]
            pos = (f, c)
            if v == "X":
                ax.text(c + 0.5, f + 0.5, "X", ha="center", va="center",
                        color="white", fontsize=12, fontweight="bold")
                continue
            # peso de la casilla (esquina superior izquierda)
            ax.text(c + 0.07, f + 0.2, _etiqueta(v) if v in ("B", "S") else f"c={v}",
                    fontsize=6.5, color="#475569", ha="left", va="center")
            if pos in cerradas:
                ax.add_patch(patches.Rectangle((c, f), 1, 1, facecolor=COLOR_CERRADA,
                                               alpha=0.45, lw=0, zorder=1))
                ax.text(c + 0.93, f + 0.2, f"#{cerradas[pos]}", fontsize=6.5, ha="right",
                        va="center", color="white", fontweight="bold", zorder=4,
                        bbox=dict(boxstyle="round,pad=0.15", fc=COLOR_CERRADA, ec="none"))
            if pos in abiertas:
                ax.add_patch(patches.Rectangle((c + 0.04, f + 0.04), 0.92, 0.92, fill=False,
                                               edgecolor=COLOR_ABIERTA, lw=2.2, ls="--", zorder=3))
            if pos in conocidos:
                n = conocidos[pos]
                ax.text(c + 0.5, f + 0.52, f"g={formato_num(n['g'])} h={n['h']}",
                        fontsize=6.8, ha="center", va="center", color="#0f172a", zorder=4)
                ax.text(c + 0.5, f + 0.8, f"f={formato_num(n['f'])}", fontsize=8.5,
                        ha="center", va="center", fontweight="bold", color="#0f172a", zorder=4)

    if actual is not None:
        f, c = actual
        ax.add_patch(patches.Rectangle((c + 0.02, f + 0.02), 0.96, 0.96, fill=False,
                                       edgecolor=COLOR_ACTUAL, lw=3.5, zorder=6))
    if mostrar_camino and resultado.encontrado:
        _dibujar_camino(ax, resultado.camino, lw=3)


def texto_variables(estado, total_iter) -> str:
    L = []
    L.append(f"ITERACIÓN {estado.iteracion} / {total_iter}")
    L.append("")
    if estado.actual:
        a = estado.actual
        L.append(f"Nodo extraído (menor f): {formato_pos(a['pos'])}")
        L.append(f"   g={formato_num(a['g'])}  h={a['h']}  f={formato_num(a['f'])}  "
                 f"padre={formato_pos(a['padre']) if a['padre'] else '-'}")
    else:
        L.append("Inicialización: Bombero (0,0) en lista abierta, g(0,0)=0")
    if estado.es_meta:
        L.append(">>> META (7,7) EXTRAÍDA: FIN DE LA BÚSQUEDA <<<")
    L.append("")
    if estado.vecinos:
        L.append("Vecinos evaluados:")
        for v in estado.vecinos:
            fx = f" f={formato_num(v['f'])}" if v["f"] is not None else ""
            acc = v["accion"].split(" - ")[0]
            L.append(f"  {v['dir']:<9}{formato_pos(v['pos'])} c={formato_num(v['coste_paso'])}{fx:<6} {acc}")
        L.append("")
    L.append(f"Nodos creados: {estado.creados}    Nodos expandidos: {estado.expandidos}")
    L.append(f"Actualizaciones de g: {estado.actualizados}")
    L.append("")
    L.append(f"LISTA ABIERTA ({len(estado.abierta)})  [orden: f, h, antigüedad]")
    L.append("   nodo     g    h    f   padre")
    for n in estado.abierta[:14]:
        L.append(f"   {formato_pos(n['pos']):<7}{formato_num(n['g']):>3}  {n['h']:>3}  "
                 f"{formato_num(n['f']):>3}   {formato_pos(n['padre']) if n['padre'] else '-'}")
    if len(estado.abierta) > 14:
        L.append(f"   ... (+{len(estado.abierta) - 14} más)")
    if not estado.abierta:
        L.append("   (vacía)")
    L.append("")
    L.append(f"LISTA CERRADA ({len(estado.cerrada)})")
    fila = "   "
    for i, p in enumerate(estado.cerrada, 1):
        trozo = formato_pos(p) + " "
        if len(fila) + len(trozo) > 50:
            L.append(fila)
            fila = "   "
        fila += trozo
    if fila.strip():
        L.append(fila)
    return "\n".join(L)


def _leyenda_estado(fig, y=0.015):
    handles = [
        patches.Patch(facecolor="white", edgecolor=COLOR_ABIERTA, ls="--", lw=2, label="Lista abierta"),
        patches.Patch(facecolor=COLOR_CERRADA, alpha=0.6, label="Lista cerrada (#orden)"),
        patches.Patch(facecolor="white", edgecolor=COLOR_ACTUAL, lw=2.5, label="Nodo actual"),
        patches.Patch(facecolor=COLOR_CAMINO, label="Ruta óptima"),
        matplotlib.lines.Line2D([], [], color="#475569", marker=">", label="Padre → hijo"),
    ]
    fig.legend(handles=handles, loc="lower left", ncol=5, fontsize=8, frameon=False,
               bbox_to_anchor=(0.03, y))


def figura_iteracion(estado, resultado, ruta):
    fig = plt.figure(figsize=(15, 8.2), facecolor=FONDO)
    ax = fig.add_axes([0.04, 0.08, 0.5, 0.82])
    ax_txt = fig.add_axes([0.57, 0.04, 0.42, 0.9])
    ax_txt.axis("off")
    ultimo = estado.iteracion == resultado.traza[-1].iteracion
    dibujar_estado(ax, estado, resultado, mostrar_camino=ultimo)
    fig.suptitle(f"A* – Espacio de búsqueda en la iteración {estado.iteracion}",
                 fontsize=14, fontweight="bold", color=COLOR_TITULO, x=0.29, y=0.985)
    ax_txt.text(0, 1, texto_variables(estado, resultado.traza[-1].iteracion),
                va="top", ha="left", family="monospace", fontsize=9.2, color="#0f172a")
    _leyenda_estado(fig)
    fig.savefig(ruta, dpi=110, facecolor=FONDO)
    plt.close(fig)


def figura_ruta_optima(resultado: Resultado, ruta):
    fig, ax = plt.subplots(figsize=(7, 7.8), facecolor=FONDO)
    _preparar_ejes(ax, f"Ruta óptima encontrada por A* – coste total = {formato_num(resultado.coste)}")
    _fondo_tablero(ax, esquina=True)
    _dibujar_camino(ax, resultado.camino)
    acumulado = 0
    for i, p in enumerate(resultado.camino):
        acumulado += coste_casilla(TABLERO, p) if i else 0
        ax.text(p[1] + 0.95, p[0] + 0.9, f"g={formato_num(acumulado)}", fontsize=7,
                ha="right", va="bottom", color="#14532d", fontweight="bold", zorder=7,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec=COLOR_CAMINO, lw=0.6))
    _leyenda_tablero(fig)
    fig.text(0.5, 0.115, f"{len(resultado.camino) - 1} movimientos · "
             f"{resultado.creados} nodos creados · {resultado.expandidos} nodos expandidos",
             ha="center", fontsize=9.5, color="#334155")
    fig.subplots_adjust(bottom=0.16, top=0.88)
    fig.savefig(ruta, dpi=160, facecolor=FONDO)
    plt.close(fig)


def _mapa_exploracion(ax, resultado: Resultado, titulo):
    _preparar_ejes(ax, titulo)
    _fondo_tablero(ax, etiquetas=False, alpha=0.35)
    orden = {p: i + 1 for i, p in enumerate(resultado.orden_expansion)}
    n = max(len(orden), 1)
    cmap = plt.get_cmap("viridis_r")
    ultima = resultado.traza[-1]
    abiertas_fin = {x["pos"] for x in ultima.abierta}
    for f in range(8):
        for c in range(8):
            p = (f, c)
            if TABLERO[f][c] == "X":
                ax.add_patch(patches.Rectangle((c, f), 1, 1, facecolor=COLOR_CELDA["X"], lw=0))
                ax.text(c + 0.5, f + 0.5, "X", color="white", ha="center", va="center",
                        fontsize=11, fontweight="bold")
            elif p in orden:
                k = orden[p]
                col = cmap(0.1 + 0.8 * (k - 1) / max(n - 1, 1))
                ax.add_patch(patches.Rectangle((c, f), 1, 1, facecolor=col, edgecolor="white", lw=1))
                ax.text(c + 0.5, f + 0.5, str(k), ha="center", va="center", fontsize=10,
                        fontweight="bold", color="white" if k > n * 0.35 else "#0f172a")
            elif p in abiertas_fin:
                ax.add_patch(patches.Rectangle((c + 0.05, f + 0.05), 0.9, 0.9, fill=False,
                                               edgecolor=COLOR_ABIERTA, lw=2, ls="--"))
                ax.text(c + 0.5, f + 0.5, "abierta", ha="center", va="center", fontsize=7,
                        color=COLOR_ABIERTA)
            else:
                ax.text(c + 0.5, f + 0.5, "no\ngenerado", ha="center", va="center",
                        fontsize=6.5, color="#64748b")
    if resultado.encontrado:
        _dibujar_camino(ax, resultado.camino, color="#dc2626", lw=2.5)


def figura_espacio_busqueda(resultado: Resultado, ruta):
    fig, ax = plt.subplots(figsize=(7, 7.8), facecolor=FONDO)
    _mapa_exploracion(ax, resultado, "Espacio de búsqueda: orden de expansión (lista cerrada)")
    fig.text(0.5, 0.06,
             "Número = orden en que el nodo entró en la lista cerrada · recuadro azul = quedó en lista abierta\n"
             "Línea roja = ruta óptima · colores claros = explorado antes, oscuros = después",
             ha="center", fontsize=8.5, color="#334155")
    fig.subplots_adjust(bottom=0.13, top=0.88)
    fig.savefig(ruta, dpi=160, facecolor=FONDO)
    plt.close(fig)


def figura_comparacion(res_astar: Resultado, res_dijkstra: Resultado, ruta):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 7.4), facecolor=FONDO)
    _mapa_exploracion(a1, res_astar, f"A* con h = Manhattan\ncoste={formato_num(res_astar.coste)}, "
                                     f"expandidos={res_astar.expandidos}, creados={res_astar.creados}")
    _mapa_exploracion(a2, res_dijkstra, f"Sin heurística (h = 0, coste uniforme)\ncoste="
                                        f"{formato_num(res_dijkstra.coste)}, expandidos="
                                        f"{res_dijkstra.expandidos}, creados={res_dijkstra.creados}")
    fig.subplots_adjust(bottom=0.05, top=0.83, wspace=0.25)
    fig.savefig(ruta, dpi=140, facecolor=FONDO)
    plt.close(fig)


def figura_heuristica(h_real, ruta):
    """Tres matrices: h(n) Manhattan, h*(n) coste real óptimo, y la diferencia."""
    fig, axes = plt.subplots(1, 3, figsize=(13, 5.2), facecolor=FONDO)
    titulos = ["h(n) = Distancia de Manhattan", "h*(n) = coste real mínimo a (7,7)",
               "h*(n) − h(n)  (≥ 0 ⇒ admisible)"]
    for k, ax in enumerate(axes):
        _preparar_ejes(ax, titulos[k])
        for f in range(8):
            for c in range(8):
                if TABLERO[f][c] == "X":
                    ax.add_patch(patches.Rectangle((c, f), 1, 1, facecolor=COLOR_CELDA["X"], lw=0))
                    ax.text(c + 0.5, f + 0.5, "X", color="white", ha="center", va="center",
                            fontsize=15, fontweight="bold")
                    continue
                h = manhattan((f, c), META)
                hs = h_real[f][c]
                val = [h, hs, hs - h][k]
                fc = ["#dbeafe", "#dcfce7", "#fef9c3" if val > 0 else "#e2e8f0"][k]
                ax.add_patch(patches.Rectangle((c, f), 1, 1, facecolor=fc, edgecolor="#cbd5e1"))
                ax.text(c + 0.5, f + 0.5, formato_num(val), ha="center", va="center",
                        fontsize=15, fontweight="bold", color="#0f172a")
        ax.title.set_fontsize(15)
        ax.tick_params(labelsize=12)
    fig.subplots_adjust(left=0.03, right=0.99, top=0.82, bottom=0.03, wspace=0.18)
    fig.savefig(ruta, dpi=140, facecolor=FONDO)
    plt.close(fig)


def generar_gif(rutas_png, ruta_gif, ms=900):
    from PIL import Image
    frames = [Image.open(p).convert("P", palette=Image.ADAPTIVE) for p in rutas_png]
    duraciones = [ms] * len(frames)
    duraciones[0] = 1800
    duraciones[-1] = 4000
    frames[0].save(ruta_gif, save_all=True, append_images=frames[1:],
                   duration=duraciones, loop=0, optimize=True)


def generar_todas_las_figuras(resultado: Resultado, carpeta="resultados", log=print):
    from astar_rescate import verificar_admisibilidad
    os.makedirs(carpeta, exist_ok=True)
    carpeta_it = os.path.join(carpeta, "iteraciones")
    os.makedirs(carpeta_it, exist_ok=True)
    for viejo in os.listdir(carpeta_it):          # imágenes de ejecuciones anteriores
        if viejo.startswith("iteracion_") and viejo.endswith(".png"):
            os.remove(os.path.join(carpeta_it, viejo))

    figura_tablero_inicial(os.path.join(carpeta, "01_tablero_inicial.png"))
    figura_ruta_optima(resultado, os.path.join(carpeta, "02_ruta_optima.png"))
    figura_espacio_busqueda(resultado, os.path.join(carpeta, "03_espacio_busqueda.png"))
    res_d = a_estrella(heuristica=heuristica_cero)
    figura_comparacion(resultado, res_d, os.path.join(carpeta, "04_comparacion_h0.png"))
    _, _, _, h_real = verificar_admisibilidad()
    figura_heuristica(h_real, os.path.join(carpeta, "05_admisibilidad_heuristica.png"))
    log("  Figuras principales generadas.")

    rutas = []
    for e in resultado.traza:
        r = os.path.join(carpeta_it, f"iteracion_{e.iteracion:02d}.png")
        figura_iteracion(e, resultado, r)
        rutas.append(r)
    log(f"  {len(rutas)} imágenes de iteraciones generadas en {carpeta_it}")
    generar_gif(rutas, os.path.join(carpeta, "animacion_astar.gif"))
    log("  Animación GIF generada.")
    return res_d


# ---------------------------------------------------------------------------
# VISOR INTERACTIVO
# ---------------------------------------------------------------------------
class VisorAEstrella:
    """Ventana para recorrer la búsqueda iteración por iteración.

    Controles: botones |<  <  >  >|  Reproducir, deslizador, o teclado
    (← → Inicio Fin, barra espaciadora = reproducir/pausar).
    """

    def __init__(self, resultado: Resultado):
        self.res = resultado
        self.total = len(resultado.traza) - 1
        self.i = 0
        self.reproduciendo = False

        self.fig = plt.figure(figsize=(15.5, 8.6), facecolor=FONDO)
        self.fig.canvas.manager.set_window_title("A* – Rescate post-terremoto")
        self.ax = self.fig.add_axes([0.035, 0.14, 0.5, 0.78])
        self.ax_txt = self.fig.add_axes([0.57, 0.12, 0.42, 0.84])
        self.ax_txt.axis("off")

        self.slider = Slider(self.fig.add_axes([0.1, 0.075, 0.38, 0.025]), "Iteración",
                             0, self.total, valinit=0, valstep=1, color=COLOR_ABIERTA)
        self.slider.on_changed(self._slider)
        botones = [("|<", self._primero), ("<", self._anterior), (">", self._siguiente),
                   (">|", self._ultimo), ("Reproducir", self._play)]
        self._botones = []
        x = 0.57
        for texto, fn in botones:
            ancho = 0.09 if texto == "Reproducir" else 0.05
            b = Button(self.fig.add_axes([x, 0.06, ancho, 0.045]), texto,
                       color="#e2e8f0", hovercolor="#bfdbfe")
            b.on_clicked(fn)
            self._botones.append(b)
            x += ancho + 0.01
        self.fig.canvas.mpl_connect("key_press_event", self._tecla)
        self.timer = self.fig.canvas.new_timer(interval=800)
        self.timer.add_callback(self._tick)
        _leyenda_estado(self.fig, y=0.005)
        self._dibujar()

    def _dibujar(self):
        e = self.res.traza[self.i]
        dibujar_estado(self.ax, e, self.res, mostrar_camino=(self.i == self.total))
        self.ax_txt.clear()
        self.ax_txt.axis("off")
        self.ax_txt.text(0, 1, texto_variables(e, self.total), va="top", ha="left",
                         family="monospace", fontsize=9, color="#0f172a")
        titulo = "A* – Rescate post-terremoto  |  f(n) = g(n) + h(n)"
        if self.i == self.total and self.res.encontrado:
            titulo += f"  |  RUTA ÓPTIMA: coste {formato_num(self.res.coste)}"
        self.fig.suptitle(titulo, fontsize=13, fontweight="bold", color=COLOR_TITULO,
                          x=0.29, y=0.985)
        self.fig.canvas.draw_idle()

    def _ir(self, i):
        i = max(0, min(self.total, int(i)))
        if i != int(self.slider.val):
            self.slider.set_val(i)       # dispara _slider -> _dibujar
        else:
            self.i = i
            self._dibujar()

    def _slider(self, val):
        self.i = int(val)
        self._dibujar()

    def _primero(self, _=None): self._ir(0)
    def _anterior(self, _=None): self._ir(self.i - 1)
    def _siguiente(self, _=None): self._ir(self.i + 1)
    def _ultimo(self, _=None): self._ir(self.total)

    def _play(self, _=None):
        self.reproduciendo = not self.reproduciendo
        self._botones[-1].label.set_text("Pausa" if self.reproduciendo else "Reproducir")
        if self.reproduciendo:
            if self.i == self.total:
                self._ir(0)
            self.timer.start()
        else:
            self.timer.stop()
        self.fig.canvas.draw_idle()

    def _tick(self):
        if self.i >= self.total:
            self._play()
            return
        self._siguiente()

    def _tecla(self, ev):
        acciones = {"right": self._siguiente, "left": self._anterior,
                    "home": self._primero, "end": self._ultimo, " ": self._play}
        if ev.key in acciones:
            acciones[ev.key]()

    def mostrar(self):
        plt.show()


if __name__ == "__main__":
    VisorAEstrella(a_estrella()).mostrar()
