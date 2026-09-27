"""
PROYECTO DE INTELIGENCIA ARTIFICIAL
Algoritmo de Búsqueda A* para Rescate de Emergencia Post-Terremoto

Núcleo del algoritmo A* (A-Estrella):
    f(n) = g(n) + h(n)
    g(n): coste real acumulado desde el Bombero (0,0) hasta la casilla n.
    h(n): Distancia de Manhattan desde n hasta el Superviviente (7,7).

Además de encontrar la ruta óptima, este módulo registra una TRAZA completa de la
búsqueda (lista abierta, lista cerrada, nodos creados y expandidos en cada
iteración) para poder visualizar cómo explora el algoritmo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

INF = float("inf")

# ---------------------------------------------------------------------------
# 1. ENTORNO: matriz 8 x 8 exactamente igual a la del enunciado
#    'B' = Bombero (inicio), 'S' = Superviviente (meta), 'X' = bloqueado (∞)
#    1 = Libre, 2 = Escombros leves, 4 = Grietas / Humo, 7 = Fuego / Agua
# ---------------------------------------------------------------------------
TABLERO = [
    #  0    1    2    3    4    5    6    7      <- columnas
    ["B", 1,   2,   4,   "X", 1,   1,   1],    # fila 0
    [1,   "X", 1,   7,   "X", 2,   "X", 1],    # fila 1
    [2,   "X", 1,   1,   1,   4,   "X", 1],    # fila 2
    [1,   2,   2,   "X", "X", 1,   1,   2],    # fila 3
    [4,   "X", 1,   7,   1,   2,   "X", 4],    # fila 4
    [1,   "X", 1,   1,   "X", 1,   1,   1],    # fila 5
    [2,   1,   4,   1,   "X", 2,   "X", 1],    # fila 6
    [1,   1,   7,   2,   1,   1,   1,   "S"],  # fila 7
]

INICIO = (0, 0)  # Bombero
META = (7, 7)    # Superviviente

# Aclaración del profesor: B y S se toman como casillas de valor 1 (punto libre).
# Los valores altos (2, 4, 7) son penalizaciones para evitar ciertos tránsitos.
COSTE_BOMBERO = 1        # B (1)
COSTE_SUPERVIVIENTE = 1  # S (1)

DESCRIPCION_COSTES = {
    1: "Libre / Transitable",
    2: "Impedimento Leve - Escombros Menores",
    4: "Impedimento Moderado - Grietas / Humo Denso",
    7: "Impedimento Alto - Fuego Parcial / Agua Acumulada",
    INF: "Paso Prohibido / Infranqueable (X)",
}

# 4 direcciones en el orden del enunciado: arriba, abajo, izquierda, derecha
MOVIMIENTOS = [
    (-1, 0, "arriba"),
    (1, 0, "abajo"),
    (0, -1, "izquierda"),
    (0, 1, "derecha"),
]


def coste_casilla(tablero, pos) -> float:
    """Coste de ENTRAR en la casilla `pos` (peso de la matriz)."""
    valor = tablero[pos[0]][pos[1]]
    if valor == "X":
        return INF
    if valor == "B":
        return COSTE_BOMBERO
    if valor == "S":
        return COSTE_SUPERVIVIENTE
    return float(valor)


def manhattan(a, b) -> int:
    """h(n) = |x_n - x_meta| + |y_n - y_meta|"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def heuristica_cero(a, b) -> int:
    """h(n) = 0  ->  A* se convierte en Dijkstra (solo se usa para comparar)."""
    return 0


def formato_pos(pos) -> str:
    return f"({pos[0]},{pos[1]})"


def formato_num(x) -> str:
    if x == INF:
        return "∞"
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


# ---------------------------------------------------------------------------
# 2. ESTRUCTURAS DE DATOS
# ---------------------------------------------------------------------------
@dataclass
class Nodo:
    pos: tuple
    g: float
    h: int
    padre: tuple | None
    orden: int  # orden de creación (sirve para desempatar: primero en entrar)

    @property
    def f(self) -> float:
        return self.g + self.h

    def clave(self):
        """Criterio de selección: menor f; empate -> menor h; empate -> más antiguo."""
        return (self.f, self.h, self.orden)

    def resumen(self) -> dict:
        return {"pos": self.pos, "g": self.g, "h": self.h, "f": self.f,
                "padre": self.padre, "orden": self.orden}


@dataclass
class EstadoIteracion:
    """Fotografía de las variables del algoritmo al terminar una iteración."""
    iteracion: int
    actual: dict | None            # nodo extraído de la lista abierta
    vecinos: list                  # evaluación de cada vecino
    abierta: list                  # lista abierta ordenada por (f, h, orden)
    cerrada: list                  # lista cerrada en orden de cierre
    creados: int
    expandidos: int
    actualizados: int
    es_meta: bool = False
    mensaje: str = ""


@dataclass
class Resultado:
    camino: list
    coste: float
    encontrado: bool
    traza: list = field(default_factory=list)
    nodos: dict = field(default_factory=dict)       # todos los nodos creados
    orden_expansion: list = field(default_factory=list)
    creados: int = 0
    expandidos: int = 0
    actualizados: int = 0
    iteraciones: int = 0


# ---------------------------------------------------------------------------
# 3. ALGORITMO A*
# ---------------------------------------------------------------------------
def a_estrella(tablero=TABLERO, inicio=INICIO, meta=META, heuristica=manhattan) -> Resultado:
    filas, columnas = len(tablero), len(tablero[0])
    traza: list[EstadoIteracion] = []

    # Paso 1: Inicialización ---------------------------------------------
    contador_orden = 0
    nodo_inicio = Nodo(inicio, 0, heuristica(inicio, meta), None, contador_orden)
    abierta: dict[tuple, Nodo] = {inicio: nodo_inicio}   # lista abierta
    cerrada: list[tuple] = []                            # lista cerrada (orden)
    en_cerrada: set[tuple] = set()
    todos: dict[tuple, Nodo] = {inicio: nodo_inicio}     # nodos creados
    creados, expandidos, actualizados = 1, 0, 0

    def foto(it, actual, vecinos, es_meta=False, mensaje=""):
        ordenada = sorted(abierta.values(), key=Nodo.clave)
        traza.append(EstadoIteracion(
            iteracion=it,
            actual=actual.resumen() if actual else None,
            vecinos=vecinos,
            abierta=[n.resumen() for n in ordenada],
            cerrada=list(cerrada),
            creados=creados,
            expandidos=expandidos,
            actualizados=actualizados,
            es_meta=es_meta,
            mensaje=mensaje,
        ))

    foto(0, None, [], mensaje=f"Inicialización: se inserta {formato_pos(inicio)} en la "
                              f"lista abierta con g=0, h={nodo_inicio.h}, f={nodo_inicio.f}")

    iteracion = 0
    while abierta:
        iteracion += 1

        # Paso 2: extraer el nodo con menor f(n) de la lista abierta ------
        actual = min(abierta.values(), key=Nodo.clave)
        del abierta[actual.pos]
        cerrada.append(actual.pos)
        en_cerrada.add(actual.pos)

        # Paso 4: criterio de parada -> la meta sale de la lista abierta ---
        if actual.pos == meta:
            camino = reconstruir_camino(todos, meta)
            foto(iteracion, actual, [], es_meta=True,
                 mensaje=f"La meta {formato_pos(meta)} fue extraída de la lista abierta "
                         f"con f={formato_num(actual.f)}. FIN: se reconstruye el camino.")
            return Resultado(camino, actual.g, True, traza, todos, list(cerrada),
                             creados, expandidos, actualizados, iteracion)

        # Expansión: revisar los 4 vecinos contiguos ----------------------
        expandidos += 1
        vecinos = []
        for df, dc, nombre in MOVIMIENTOS:
            v = (actual.pos[0] + df, actual.pos[1] + dc)
            if not (0 <= v[0] < filas and 0 <= v[1] < columnas):
                continue  # fuera del tablero
            paso = coste_casilla(tablero, v)
            info = {"dir": nombre, "pos": v, "coste_paso": paso,
                    "g": None, "h": None, "f": None}

            if paso == INF:
                info["accion"] = "BLOQUEADO (X) - se omite"
            elif v in en_cerrada:
                info["accion"] = "En lista cerrada - se omite"
            else:
                g_nuevo = actual.g + paso
                h_v = heuristica(v, meta)
                info.update(g=g_nuevo, h=h_v, f=g_nuevo + h_v)
                if v not in abierta:
                    contador_orden += 1
                    nodo = Nodo(v, g_nuevo, h_v, actual.pos, contador_orden)
                    abierta[v] = nodo
                    todos[v] = nodo
                    creados += 1
                    info["accion"] = "NUEVO - se inserta en lista abierta"
                elif g_nuevo < abierta[v].g:
                    g_viejo = abierta[v].g
                    abierta[v].g = g_nuevo
                    abierta[v].padre = actual.pos
                    actualizados += 1
                    info["accion"] = (f"MEJOR CAMINO - g baja de {formato_num(g_viejo)} "
                                      f"a {formato_num(g_nuevo)}, nuevo padre")
                else:
                    info["accion"] = (f"Ya en lista abierta con g={formato_num(abierta[v].g)} "
                                      f"<= {formato_num(g_nuevo)} - sin cambios")
            vecinos.append(info)

        foto(iteracion, actual, vecinos,
             mensaje=f"Se expande {formato_pos(actual.pos)} (f={formato_num(actual.f)})")

    # Lista abierta vacía: no existe camino
    return Resultado([], INF, False, traza, todos, list(cerrada),
                     creados, expandidos, actualizados, iteracion)


def reconstruir_camino(nodos: dict, meta) -> list:
    """Recorre los punteros 'padre' desde la meta hasta el inicio y lo invierte."""
    camino = [meta]
    while nodos[camino[-1]].padre is not None:
        camino.append(nodos[camino[-1]].padre)
    camino.reverse()
    return camino


# ---------------------------------------------------------------------------
# 4. VERIFICACIÓN DE LA HEURÍSTICA:  h(n) <= h*(n)  para toda casilla
# ---------------------------------------------------------------------------
def coste_optimo_real(tablero=TABLERO, meta=META) -> list:
    """
    h*(n): coste real mínimo desde cada casilla n hasta la meta, calculado con
    búsqueda de coste uniforme (h = 0). Sirve para comprobar empíricamente la
    admisibilidad de la Distancia de Manhattan.
    """
    filas, columnas = len(tablero), len(tablero[0])
    h_real = [[None] * columnas for _ in range(filas)]
    for f in range(filas):
        for c in range(columnas):
            if tablero[f][c] == "X":
                continue
            r = a_estrella(tablero, (f, c), meta, heuristica_cero)
            h_real[f][c] = r.coste
    return h_real


def verificar_admisibilidad(tablero=TABLERO, meta=META):
    """Devuelve (es_admisible, es_consistente, tabla) comparando h(n) con h*(n)."""
    h_real = coste_optimo_real(tablero, meta)
    filas, columnas = len(tablero), len(tablero[0])
    tabla = []
    admisible = True
    for f in range(filas):
        for c in range(columnas):
            if h_real[f][c] is None:
                continue
            h = manhattan((f, c), meta)
            ok = h <= h_real[f][c]
            admisible &= ok
            tabla.append(((f, c), h, h_real[f][c], ok))

    # Consistencia (monotonía): h(n) <= c(n, n') + h(n') para todo vecino n'
    consistente = True
    for f in range(filas):
        for c in range(columnas):
            if tablero[f][c] == "X":
                continue
            for df, dc, _ in MOVIMIENTOS:
                v = (f + df, c + dc)
                if 0 <= v[0] < filas and 0 <= v[1] < columnas and tablero[v[0]][v[1]] != "X":
                    if manhattan((f, c), meta) > coste_casilla(tablero, v) + manhattan(v, meta):
                        consistente = False
    return admisible, consistente, tabla, h_real


# ---------------------------------------------------------------------------
# 5. SALIDA POR CONSOLA / ARCHIVO DE TEXTO
# ---------------------------------------------------------------------------
def texto_traza(resultado: Resultado) -> str:
    L = []
    sep = "=" * 78
    L.append(sep)
    L.append(" A* - RESCATE POST-TERREMOTO  |  f(n) = g(n) + h(n)  |  h = Manhattan")
    L.append(sep)
    L.append("Tablero 8x8 (B=Bombero, S=Superviviente, X=bloqueado):")
    L.append("F\\C  " + "  ".join(f"{c:>3}" for c in range(8)))
    for f, fila in enumerate(TABLERO):
        L.append(f" {f}   " + "  ".join(f"{str(v):>3}" for v in fila))
    L.append("")

    for e in resultado.traza:
        L.append("-" * 78)
        L.append(f"ITERACIÓN {e.iteracion}: {e.mensaje}")
        if e.actual:
            a = e.actual
            L.append(f"  Nodo extraído: {formato_pos(a['pos'])}  g={formato_num(a['g'])}  "
                     f"h={a['h']}  f={formato_num(a['f'])}  padre="
                     f"{formato_pos(a['padre']) if a['padre'] else '-'}")
        for v in e.vecinos:
            gh = ""
            if v["g"] is not None:
                gh = (f" g={formato_num(v['g'])} h={v['h']} f={formato_num(v['f'])}")
            L.append(f"    · {v['dir']:<9} {formato_pos(v['pos'])} coste={formato_num(v['coste_paso']):>2}"
                     f"{gh:<20} -> {v['accion']}")
        L.append(f"  LISTA ABIERTA ({len(e.abierta)}), ordenada por f, h, antigüedad:")
        if e.abierta:
            for n in e.abierta:
                L.append(f"      {formato_pos(n['pos'])}  g={formato_num(n['g']):>2}  h={n['h']:>2}  "
                         f"f={formato_num(n['f']):>2}  padre={formato_pos(n['padre']) if n['padre'] else '-'}")
        else:
            L.append("      (vacía)")
        L.append(f"  LISTA CERRADA ({len(e.cerrada)}): " + " ".join(formato_pos(p) for p in e.cerrada))
        L.append(f"  Nodos creados={e.creados}  expandidos={e.expandidos}  "
                 f"actualizados={e.actualizados}")

    L.append(sep)
    if resultado.encontrado:
        L.append("RUTA ÓPTIMA ENCONTRADA")
        L.append("  " + " -> ".join(formato_pos(p) for p in resultado.camino))
        L.append(f"  Coste total g(meta) = {formato_num(resultado.coste)}")
        L.append(f"  Número de movimientos = {len(resultado.camino) - 1}")
        acumulado = 0
        detalle = []
        for p in resultado.camino[1:]:
            c = coste_casilla(TABLERO, p)
            acumulado += c
            detalle.append(f"{formato_pos(p)}:+{formato_num(c)}={formato_num(acumulado)}")
        L.append("  Desglose: " + ", ".join(detalle))
    else:
        L.append("NO EXISTE CAMINO HASTA LA META")
    L.append(f"  Iteraciones={resultado.iteraciones}  Nodos creados={resultado.creados}  "
             f"Nodos expandidos={resultado.expandidos}  Actualizaciones={resultado.actualizados}")
    L.append(sep)
    return "\n".join(L)


if __name__ == "__main__":
    res = a_estrella()
    print(texto_traza(res))
    adm, cons, _, _ = verificar_admisibilidad()
    print(f"Heurística admisible (h <= h* en todas las casillas): {adm}")
    print(f"Heurística consistente (h(n) <= c(n,n') + h(n')):    {cons}")
