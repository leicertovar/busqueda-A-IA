"""
Genera el INFORME en PDF del proyecto A* (rúbrica, punto 1).

Todo el contenido numérico (tablas de iteraciones, lista abierta, lista cerrada,
nodos creados/expandidos, ruta y coste) se toma directamente de la ejecución
real del algoritmo, de modo que el informe siempre coincide con el programa.

>>> Editar la lista INTEGRANTES con los nombres del grupo (máximo 4). <<<
"""

from __future__ import annotations

import datetime
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from astar_rescate import (DESCRIPCION_COSTES, INF, INICIO, META, TABLERO,
                           Resultado, a_estrella, coste_casilla, formato_num,
                           formato_pos, heuristica_cero, manhattan,
                           verificar_admisibilidad)

# ---------------------------------------------------------------------------
INTEGRANTES = [
    "Integrante 1 – (nombre completo)",
    "Integrante 2 – (nombre completo)",
    "Integrante 3 – (nombre completo)",
    "Integrante 4 – (nombre completo)",
]
ASIGNATURA = "Inteligencia Artificial"
DOCENTE = "(nombre del docente)"
# ---------------------------------------------------------------------------

AZUL = colors.HexColor("#1e3a8a")
AZUL_CLARO = colors.HexColor("#dbeafe")
ROJO = colors.HexColor("#dc2626")
GRIS = colors.HexColor("#475569")
GRIS_CLARO = colors.HexColor("#f1f5f9")
BORDE = colors.HexColor("#cbd5e1")


def _registrar_fuentes():
    """Usa Arial (soporta ∞, ≤, ≥, ×) si está disponible; si no, Helvetica."""
    carpeta = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    archivos = {"Base": "arial.ttf", "Base-Bold": "arialbd.ttf",
                "Base-Italic": "ariali.ttf", "Base-BoldItalic": "arialbi.ttf",
                "Mono": "consola.ttf", "Mono-Bold": "consolab.ttf"}
    try:
        for nombre, arch in archivos.items():
            pdfmetrics.registerFont(TTFont(nombre, os.path.join(carpeta, arch)))
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily("Base", normal="Base", bold="Base-Bold",
                           italic="Base-Italic", boldItalic="Base-BoldItalic")
        registerFontFamily("Mono", normal="Mono", bold="Mono-Bold",
                           italic="Mono", boldItalic="Mono-Bold")
        return "Base", "Base-Bold", "Mono"
    except Exception:
        return "Helvetica", "Helvetica-Bold", "Courier"


BASE, NEGRITA, MONO = _registrar_fuentes()


def _estilos():
    s = getSampleStyleSheet()
    e = {
        "cuerpo": ParagraphStyle("cuerpo", parent=s["Normal"], fontName=BASE, fontSize=10.3,
                                 leading=14.5, alignment=TA_JUSTIFY, spaceAfter=6),
        "vineta": ParagraphStyle("vineta", parent=s["Normal"], fontName=BASE, fontSize=10.3,
                                 leading=14.5, leftIndent=16, bulletIndent=5, spaceAfter=3,
                                 alignment=TA_JUSTIFY),
        "h1": ParagraphStyle("h1", fontName=NEGRITA, fontSize=15, leading=19, textColor=AZUL,
                             spaceBefore=10, spaceAfter=8),
        "h2": ParagraphStyle("h2", fontName=NEGRITA, fontSize=12, leading=16, textColor=AZUL,
                             spaceBefore=8, spaceAfter=5),
        "formula": ParagraphStyle("formula", fontName=NEGRITA, fontSize=12.5, leading=18,
                                  alignment=TA_CENTER, textColor=ROJO, spaceBefore=4,
                                  spaceAfter=8, backColor=colors.white, borderColor=BORDE,
                                  borderWidth=0.8, borderPadding=6),
        "codigo": ParagraphStyle("codigo", fontName=MONO, fontSize=8.8, leading=11.5,
                                 backColor=GRIS_CLARO, borderColor=BORDE, borderWidth=0.6,
                                 borderPadding=7, spaceBefore=4, spaceAfter=10),
        "celda": ParagraphStyle("celda", fontName=BASE, fontSize=8.2, leading=10.2),
        "celda_c": ParagraphStyle("celda_c", fontName=BASE, fontSize=8.2, leading=10.2,
                                  alignment=TA_CENTER),
        "celda_mono": ParagraphStyle("celda_mono", fontName=MONO, fontSize=7.6, leading=9.6),
        "pie": ParagraphStyle("pie", fontName=BASE, fontSize=8.8, leading=11, textColor=GRIS,
                              alignment=TA_CENTER, spaceAfter=10),
        "portada_t": ParagraphStyle("pt", fontName=NEGRITA, fontSize=24, leading=30,
                                    alignment=TA_CENTER, textColor=AZUL),
        "portada_s": ParagraphStyle("ps", fontName=BASE, fontSize=14, leading=19,
                                    alignment=TA_CENTER, textColor=GRIS),
        "portada_n": ParagraphStyle("pn", fontName=BASE, fontSize=12, leading=18,
                                    alignment=TA_CENTER),
    }
    return e


E = _estilos()


def P(texto, estilo="cuerpo"):
    return Paragraph(texto, E[estilo])


def V(texto):
    return Paragraph(texto, E["vineta"], bulletText="•")


def tabla(datos, anchos, cabecera=True, zebra=True, estilo_extra=None, tam=8.2):
    filas = []
    for i, fila in enumerate(datos):
        nueva = []
        for x in fila:
            if isinstance(x, str):
                st = ParagraphStyle("t", parent=E["celda"], fontSize=tam, leading=tam + 2,
                                    fontName=NEGRITA if (cabecera and i == 0) else BASE,
                                    textColor=colors.white if (cabecera and i == 0) else colors.black)
                nueva.append(Paragraph(x, st))
            else:
                nueva.append(x)
        filas.append(nueva)
    t = Table(filas, colWidths=anchos, repeatRows=1 if cabecera else 0)
    cmds = [("GRID", (0, 0), (-1, -1), 0.5, BORDE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if cabecera:
        cmds.append(("BACKGROUND", (0, 0), (-1, 0), AZUL))
    if zebra:
        for i in range(1 if cabecera else 0, len(filas)):
            if i % 2 == 0:
                cmds.append(("BACKGROUND", (0, i), (-1, i), GRIS_CLARO))
    if estilo_extra:
        cmds += estilo_extra
    t.setStyle(TableStyle(cmds))
    return t


def imagen(ruta, ancho_cm):
    from PIL import Image as PILImage
    with PILImage.open(ruta) as im:
        w, h = im.size
    ancho = ancho_cm * cm
    return Image(ruta, width=ancho, height=ancho * h / w)


def _pie_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(AZUL)
    canvas.rect(0, A4[1] - 0.55 * cm, A4[0], 0.55 * cm, fill=1, stroke=0)
    canvas.setFillColor(ROJO)
    canvas.rect(0, A4[1] - 0.65 * cm, A4[0], 0.1 * cm, fill=1, stroke=0)
    if doc.page > 1:
        canvas.setFont(BASE, 8)
        canvas.setFillColor(GRIS)
        canvas.drawString(2 * cm, 1.1 * cm, "Proyecto de Inteligencia Artificial – A* para rescate post-terremoto")
        canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _tabla_tablero():
    """Matriz 8x8 con los mismos colores del enunciado."""
    col = {1: "#f8fafc", 2: "#fef08a", 4: "#fed7aa", 7: "#fca5a5", "X": "#1e293b",
           "B": "#22c55e", "S": "#ef4444"}
    datos = [["F \\ C"] + [str(c) for c in range(8)]]
    for f, fila in enumerate(TABLERO):
        datos.append([str(f)] + [{"B": "B (0)", "S": "S (7)"}.get(v, str(v)) for v in fila])
    t = Table(datos, colWidths=[1.5 * cm] + [1.6 * cm] * 8, rowHeights=0.75 * cm)
    cmds = [("GRID", (0, 0), (-1, -1), 0.6, BORDE),
            ("FONTNAME", (0, 0), (-1, -1), NEGRITA), ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#475569")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#475569")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("TEXTCOLOR", (0, 0), (0, -1), colors.white)]
    for f, fila in enumerate(TABLERO):
        for c, v in enumerate(fila):
            cmds.append(("BACKGROUND", (c + 1, f + 1), (c + 1, f + 1), colors.HexColor(col[v])))
            if v in ("X", "B", "S"):
                cmds.append(("TEXTCOLOR", (c + 1, f + 1), (c + 1, f + 1), colors.white))
            elif v in (2, 4, 7):
                cmds.append(("TEXTCOLOR", (c + 1, f + 1), (c + 1, f + 1), colors.HexColor("#7c2d12")))
    t.setStyle(TableStyle(cmds))
    return t


def _lista_abierta_txt(abierta, max_items=None):
    items = abierta if max_items is None else abierta[:max_items]
    txt = ", ".join(f"{formato_pos(n['pos'])}:{formato_num(n['f'])}" for n in items)
    if max_items is not None and len(abierta) > max_items:
        txt += f" … (+{len(abierta) - max_items})"
    return txt or "(vacía)"


# ---------------------------------------------------------------------------
def generar_informe(res: Resultado, res_h0: Resultado | None = None, carpeta="resultados",
                    nombre="Informe_Proyecto_AStar.pdf") -> str:
    if res_h0 is None:
        res_h0 = a_estrella(heuristica=heuristica_cero)
    admisible, consistente, tabla_h, h_real = verificar_admisibilidad()
    ruta_pdf = os.path.join(carpeta, nombre)
    img = lambda n: os.path.join(carpeta, n)
    img_it = lambda k: os.path.join(carpeta, "iteraciones", f"iteracion_{k:02d}.png")

    doc = SimpleDocTemplate(ruta_pdf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="Proyecto A* – Rescate post-terremoto",
                            author=", ".join(INTEGRANTES))
    H = []  # historia del documento
    ancho_util = A4[0] - 4 * cm

    # ----------------------------------------------------------- PORTADA
    H += [Spacer(1, 3 * cm),
          P("PROYECTO DE INTELIGENCIA ARTIFICIAL", "portada_t"), Spacer(1, 0.5 * cm),
          P("Algoritmo de Búsqueda A* para Rescate de Emergencia Post-Terremoto", "portada_s"),
          Spacer(1, 0.8 * cm),
          P("f(n) = g(n) + h(n)", "formula"), Spacer(1, 1.2 * cm),
          P("<b>Informe técnico del proyecto</b>", "portada_n"), Spacer(1, 1 * cm),
          P("<b>Integrantes</b>", "portada_n")]
    H += [P(n, "portada_n") for n in INTEGRANTES]
    H += [Spacer(1, 1 * cm), P(f"<b>Asignatura:</b> {ASIGNATURA}", "portada_n"),
          P(f"<b>Docente:</b> {DOCENTE}", "portada_n"),
          P(f"<b>Lenguaje:</b> Python 3", "portada_n"),
          P(f"<b>Fecha:</b> {datetime.date.today().strftime('%d/%m/%Y')}", "portada_n"),
          PageBreak()]

    # ----------------------------------------------------------- CONTENIDO
    H += [P("Contenido", "h1")]
    indice = ["1. Descripción general del proyecto",
              "2. Definición del entorno y pesos de la matriz",
              "3. Modelado del problema de búsqueda",
              "4. Flujo de ejecución del algoritmo A* (Pasos 1 a 4)",
              "5. La heurística: por qué funciona y por qué es admisible",
              "6. Ejecución paso a paso: lista abierta, lista cerrada, nodos creados y expandidos",
              "7. Solución: ruta óptima y espacio de búsqueda",
              "8. Implementación en Python y visualización",
              "9. Conclusiones",
              "Anexo A. Traza completa de la lista abierta y la lista cerrada"]
    H += [V(x) for x in indice]
    H.append(PageBreak())

    # ----------------------------------------------------------- 1
    H += [P("1. Descripción general del proyecto", "h1"),
          P("Este proyecto implementa el algoritmo de búsqueda informada <b>A* (A-Estrella)</b> para "
            "simular la navegación óptima de un bombero dentro de un entorno de desastre de "
            "<b>8 × 8</b> casilleros. Tras un evento sísmico de gran magnitud, la infraestructura de una "
            "edificación colapsa parcialmente, creando un escenario crítico donde el tiempo de respuesta "
            "es vital para rescatar a un superviviente atrapado."),
          P("El objetivo es encontrar la ruta de <b>menor coste total</b> desde la posición del "
            "Bombero <b>B (0,0)</b> hasta el Superviviente <b>S (7,7)</b>, evitando las casillas "
            "bloqueadas y decidiendo cuándo conviene rodear o atravesar las zonas con impedimentos. "
            "A* evalúa en cada iteración la función de coste total:"),
          P("f(n) = g(n) + h(n)", "formula"),
          V("<b><font color='#dc2626'>g(n)</font> (Coste Real):</b> coste acumulado desde la casilla "
            "inicial (posición del bombero) hasta la casilla actual <i>n</i>."),
          V("<b><font color='#dc2626'>h(n)</font> (Heurística):</b> estimación del coste restante desde "
            "la casilla actual <i>n</i> hasta la meta (superviviente). Se utiliza la <b>Distancia de "
            "Manhattan</b> dadas las restricciones del movimiento en cuadrícula (4 direcciones):"),
          P("h(n) = |x<sub>n</sub> − x<sub>meta</sub>| + |y<sub>n</sub> − y<sub>meta</sub>|", "formula"),
          P("El trabajo cubre los cuatro puntos de la rúbrica: (1) este informe explicando cada paso y la "
            "admisibilidad de la heurística; (2) la solución con representación gráfica y la visualización "
            "del espacio de búsqueda; (3) la visualización de las variables importantes (lista cerrada, "
            "lista abierta, nodos creados y expandidos) y (4) el material de apoyo para el video explicativo.")]

    # ----------------------------------------------------------- 2
    H += [P("2. Definición del entorno y pesos de la matriz", "h1"),
          P("El escenario se modela mediante una matriz de 8 × 8 casilleros donde el terreno presenta "
            "distintos grados de dificultad y accesibilidad:")]
    datos = [["Tipo de casilla", "Coste", "Descripción"],
             ["Libre / Transitable", "1", "Terreno despejado y seguro para avanzar a velocidad normal."],
             ["Paso Prohibido / Infranqueable (X)", "∞",
              "Paredes colapsadas, incendios totales o fallas estructurales. El bombero no puede transitar."],
             ["Impedimento Leve – Escombros Menores", "2",
              "Residuos ligeros de concreto o mobiliario caído. Reduce levemente el avance."],
             ["Impedimento Moderado – Grietas / Humo Denso", "4",
              "Daños estructurales moderados o baja visibilidad que requieren precaución."],
             ["Impedimento Alto – Fuego Parcial / Agua Acumulada", "7",
              "Zonas peligrosas que exigen un esfuerzo y tiempo considerable para ser atravesadas."]]
    H.append(tabla(datos, [5.3 * cm, 1.4 * cm, ancho_util - 6.7 * cm], tam=9))
    H += [Spacer(1, 10), KeepTogether([
          P("<b>Matriz de terreno y ponderación de costes (idéntica al enunciado):</b>"),
          _tabla_tablero(), Spacer(1, 4),
          P("B: Bombero (0,0) · S: Superviviente (7,7) · X: Bloqueado (∞) · 1: Libre · "
            "2: Escombros leves · 4: Grietas / Humo · 7: Fuego parcial / Agua acumulada", "pie")]),
          P("<b>Convención de coste de movimiento.</b> Moverse de una casilla a una vecina cuesta el "
            "<b>peso de la casilla a la que se entra</b>. Así, g(n) acumula los pesos de todas las "
            "casillas atravesadas después de la inicial. La casilla del Bombero tiene coste 0 (B (0)), "
            "pues es donde ya se encuentra, y la del Superviviente tiene coste 7 (S (7)), tal como indica "
            "el tablero del enunciado. Las casillas X tienen coste ∞ y nunca se generan como sucesores.")]

    # ----------------------------------------------------------- 3
    H += [P("3. Modelado del problema de búsqueda", "h1"),
          P("Para aplicar A* el escenario se formaliza como un problema de búsqueda en un grafo:")]
    datos = [["Elemento", "Definición en este proyecto"],
             ["Estado", "Posición (F, C) del bombero en la matriz, con 0 ≤ F, C ≤ 7."],
             ["Estado inicial", "(0,0) – casilla del Bombero, con g(0,0) = 0."],
             ["Acciones", "Moverse a una de las 4 casillas contiguas, en este orden: arriba (F−1), abajo "
                          "(F+1), izquierda (C−1), derecha (C+1). Sin movimientos diagonales."],
             ["Restricciones", "No se puede salir del tablero ni entrar en casillas X (coste ∞)."],
             ["Coste de paso c(n, n')", "Peso de la casilla destino n': 1, 2, 4 o 7 (7 al entrar en S)."],
             ["Test de meta", "La casilla (7,7) (Superviviente) es extraída de la lista abierta."],
             ["Coste del camino", "Suma de los costes de paso: g(meta)."],
             ["Heurística", "h(n) = |F<sub>n</sub> − 7| + |C<sub>n</sub> − 7| (Distancia de Manhattan)."]]
    H.append(tabla(datos, [4.2 * cm, ancho_util - 4.2 * cm], tam=9))
    H += [Spacer(1, 6),
          P("<b>Definiciones de las variables que se visualizan:</b>"),
          V("<b>Lista abierta (frontera):</b> nodos generados pendientes de evaluar. De ella se extrae "
            "siempre el nodo de menor f(n)."),
          V("<b>Lista cerrada:</b> nodos ya extraídos y evaluados; no se vuelven a procesar."),
          V("<b>Nodo creado (generado):</b> cada vez que una casilla se inserta por primera vez en la lista "
            "abierta (incluye el nodo inicial)."),
          V("<b>Nodo expandido:</b> nodo extraído de la lista abierta cuyos 4 vecinos se examinan. La meta "
            "se extrae pero no se expande, porque en ese momento termina la búsqueda."),
          V("<b>Actualización:</b> cuando se descubre un camino más barato hacia un nodo que ya estaba en la "
            "lista abierta; se reduce su g(n) y se cambia su padre."),
          V("<b>Criterio de desempate:</b> si dos nodos tienen el mismo f(n) se elige el de menor h(n) (el "
            "que está más cerca de la meta) y, si persiste el empate, el que fue creado primero. Esto hace "
            "que la ejecución sea determinista y reproducible.")]

    # ----------------------------------------------------------- 4
    H += [P("4. Flujo de ejecución del algoritmo A*", "h1"),
          P("<b>Paso 1: Inicialización.</b> Se posiciona al Bombero en la casilla inicial (0,0) y al "
            "Superviviente en la casilla meta (7,7). Se inserta el nodo inicial en la lista abierta con "
            f"g(0,0) = 0, h(0,0) = {manhattan(INICIO, META)} y f(0,0) = {manhattan(INICIO, META)}. "
            "La lista cerrada comienza vacía."),
          P("<b>Paso 2: Evaluación y Búsqueda.</b> En cada iteración el algoritmo extrae el nodo con la "
            "menor función f(n) de la lista abierta y lo pasa a la lista cerrada. Revisa sus 4 vecinos "
            "contiguos (arriba, abajo, izquierda, derecha) omitiendo casillas bloqueadas (X) o nodos ya "
            "evaluados (lista cerrada). Para cada vecino válido calcula g = g(actual) + coste de la casilla, "
            "h con Manhattan y f = g + h; si el vecino es nuevo lo inserta en la lista abierta, y si ya "
            "estaba pero se llegó con un g menor, actualiza su g y su padre."),
          P("<b>Paso 3: Selección de Ruta Óptima.</b> Como la lista abierta siempre entrega el nodo de "
            "menor f, el algoritmo balancea dinámicamente entre rodear zonas peligrosas usando vías libres "
            "(coste 1) o atravesar zonas de coste 2, 4 o 7 cuando la suma g(n) + h(n) demuestra que es la vía "
            "más barata en coste total acumulado."),
          P("<b>Paso 4: Criterio de Parada.</b> El proceso concluye con éxito cuando el nodo meta (7,7) es "
            "extraído de la lista abierta. Entonces se reconstruye el camino óptimo siguiendo los punteros "
            "<i>padre</i> desde la meta hasta el inicio, y se invierte. Si la lista abierta se vaciara antes, "
            "no existiría camino."),
          P("<b>Pseudocódigo implementado</b> (función <font face='Mono'>a_estrella</font> del archivo "
            "<font face='Mono'>astar_rescate.py</font>):"),
          P("ABIERTA ← { inicio con g=0, h=h(inicio), padre=nulo }<br/>"
            "CERRADA ← ∅<br/>"
            "<b>mientras</b> ABIERTA no esté vacía:<br/>"
            "&nbsp;&nbsp;&nbsp;n ← nodo de ABIERTA con menor (f, h, orden de creación)<br/>"
            "&nbsp;&nbsp;&nbsp;mover n de ABIERTA a CERRADA<br/>"
            "&nbsp;&nbsp;&nbsp;<b>si</b> n = meta: <b>devolver</b> reconstruir_camino(n)<br/>"
            "&nbsp;&nbsp;&nbsp;<b>para cada</b> vecino v de n en (arriba, abajo, izquierda, derecha):<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>si</b> v es X o v ∈ CERRADA: omitir<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;g' ← g(n) + coste(v)<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>si</b> v ∉ ABIERTA: crear v (g', h(v), padre=n) e insertarlo<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>si no, si</b> g' &lt; g(v): g(v) ← g', padre(v) ← n<br/>"
            "<b>devolver</b> \"no existe camino\"", "codigo")]

    # ----------------------------------------------------------- 5
    n_celdas = len(tabla_h)
    min_diff = min(hs - h for _, h, hs, _ in tabla_h if _ != META) if tabla_h else 0
    H += [PageBreak(), P("5. La heurística: por qué funciona y por qué es admisible", "h1"),
          P("5.1 ¿Por qué funciona la Distancia de Manhattan?", "h2"),
          P("El bombero solo puede moverse en 4 direcciones (arriba, abajo, izquierda, derecha). Cada "
            "movimiento cambia <b>exactamente una</b> coordenada en <b>exactamente una</b> unidad. Por lo tanto, "
            "para ir desde (F<sub>n</sub>, C<sub>n</sub>) hasta (7,7) se necesitan, como mínimo, "
            "|F<sub>n</sub> − 7| movimientos verticales y |C<sub>n</sub> − 7| movimientos horizontales: "
            "la Distancia de Manhattan es el <b>número mínimo de pasos</b> hasta la meta en un tablero sin "
            "obstáculos. Esta información dirige la búsqueda: entre dos nodos con el mismo g(n), A* prefiere "
            "el que está más cerca del superviviente, en lugar de explorar a ciegas en todas las direcciones "
            "como haría una búsqueda de coste uniforme."),
          P("5.2 Demostración de admisibilidad", "h2"),
          P("Una heurística es <b>admisible</b> si nunca sobreestima el coste real mínimo hasta la meta, es "
            "decir, si h(n) ≤ h*(n) para todo nodo n, donde h*(n) es el coste del camino óptimo desde n "
            "hasta (7,7)."),
          P("<b>Demostración.</b> Sea P = (n = n<sub>0</sub>, n<sub>1</sub>, …, n<sub>k</sub> = meta) "
            "cualquier camino válido desde n hasta la meta."),
          V("Cada paso cambia una coordenada en una unidad, luego el valor de Manhattan cambia como máximo en 1 "
            "por paso: |h(n<sub>i</sub>) − h(n<sub>i+1</sub>)| = 1. Como h(meta) = 0, el camino necesita "
            "<b>k ≥ h(n)</b> pasos."),
          V("El coste de cada paso es el peso de la casilla a la que se entra, que pertenece al conjunto "
            "{1, 2, 4, 7} (las X no se pueden pisar). Por tanto, <b>c(n<sub>i</sub>, n<sub>i+1</sub>) ≥ 1</b>."),
          V("Entonces coste(P) = Σ c(n<sub>i</sub>, n<sub>i+1</sub>) ≥ k · 1 ≥ h(n)."),
          P("Como esto se cumple para cualquier camino P, también se cumple para el óptimo: "
            "<b>h(n) ≤ h*(n)</b>. Los obstáculos X solo pueden alargar el camino (nunca acortarlo), y los "
            "impedimentos 2, 4 y 7 solo pueden encarecerlo, así que la heurística sigue siendo una cota "
            "inferior. <b>La Distancia de Manhattan es admisible</b> en este problema. ∎"),
          P("5.3 Consistencia (monotonía)", "h2"),
          P("Además es <b>consistente</b>: para todo nodo n y todo vecino n' se cumple "
            "h(n) ≤ c(n, n') + h(n'). En efecto, h(n) − h(n') ≤ 1 (se movió una casilla) y c(n, n') ≥ 1. "
            "La consistencia implica que los valores de f(n) nunca disminuyen a lo largo de un camino y que, "
            "cuando un nodo entra en la lista cerrada, ya se ha encontrado el camino más barato hasta él. Por "
            "eso es correcto <b>omitir los nodos de la lista cerrada</b> tal como pide el Paso 2 del "
            "enunciado: nunca será necesario reabrirlos."),
          P("5.4 Consecuencia: optimalidad garantizada", "h2"),
          P("Con una heurística admisible, A* es <b>óptimo</b>: cuando la meta sale de la lista abierta, "
            "f(meta) = g(meta) + 0 es menor o igual que el f de cualquier otro nodo pendiente, y como ningún "
            "f subestimado supera al coste real, ningún camino pendiente puede terminar con un coste menor. "
            "Por eso el Paso 4 detiene la búsqueda al <b>extraer</b> la meta y no al generarla."),
          P("5.5 Verificación experimental", "h2"),
          P(f"El programa calcula h*(n) exacto para las {n_celdas} casillas transitables (búsqueda de coste "
            f"uniforme desde cada una) y lo compara con h(n). Resultado: <b>admisible = "
            f"{'SÍ' if admisible else 'NO'}</b> (h(n) ≤ h*(n) en las {n_celdas} casillas) y <b>consistente = "
            f"{'SÍ' if consistente else 'NO'}</b> (se cumple la desigualdad triangular en todas las "
            f"transiciones). La diferencia mínima h* − h fuera de la meta es {formato_num(min_diff)}, es decir, "
            "la heurística nunca sobreestima."),
          imagen(img("05_admisibilidad_heuristica.png"), ancho_util / cm),
          P("Figura 1. Izquierda: h(n). Centro: coste real óptimo h*(n). Derecha: h*(n) − h(n) ≥ 0 en todas "
            "las casillas, lo que confirma la admisibilidad.", "pie"),
          P("<b>Observación.</b> La diferencia h* − h es grande (entre 6 y 12 en la mayoría de casillas) porque "
            "Manhattan supone que todo el recorrido es libre (coste 1) y sin obstáculos, mientras que el "
            "tablero tiene muros X y casillas de coste 2, 4 y 7; en particular, entrar al Superviviente ya "
            "cuesta 7. Esto hace que la heurística sea conservadora: garantiza la ruta óptima a cambio de "
            "explorar una parte importante del tablero (ver Sección 7.3).")]

    # ----------------------------------------------------------- 6
    H += [PageBreak(), P("6. Ejecución paso a paso", "h1"),
          P(f"La ejecución completa tuvo <b>{res.iteraciones} iteraciones</b>. A continuación se detallan las "
            "primeras iteraciones con todos sus cálculos; la tabla resumen y el Anexo A contienen el resto. "
            "Las imágenes muestran el tablero en cada momento: casillas grises = lista cerrada (con su número "
            "de orden #k), recuadro azul discontinuo = lista abierta, recuadro magenta = nodo actual; en cada "
            "casilla conocida se indica g, h y f.")]

    for e in res.traza[:5]:
        bloque = [P(f"Iteración {e.iteracion}", "h2"), P(e.mensaje + ".")]
        if e.vecinos:
            datos = [["Dirección", "Vecino", "Coste", "g", "h", "f", "Acción"]]
            for v in e.vecinos:
                datos.append([v["dir"], formato_pos(v["pos"]), formato_num(v["coste_paso"]),
                              formato_num(v["g"]) if v["g"] is not None else "–",
                              str(v["h"]) if v["h"] is not None else "–",
                              formato_num(v["f"]) if v["f"] is not None else "–", v["accion"]])
            bloque.append(tabla(datos, [1.9 * cm, 1.4 * cm, 1.4 * cm, 0.9 * cm, 0.9 * cm, 0.9 * cm,
                                        ancho_util - 7.4 * cm]))
        bloque.append(Spacer(1, 4))
        bloque.append(P(f"<b>Lista abierta ({len(e.abierta)}):</b> " + ", ".join(
            f"{formato_pos(n['pos'])} [g={formato_num(n['g'])}, h={n['h']}, f={formato_num(n['f'])}]"
            for n in e.abierta)))
        bloque.append(P(f"<b>Lista cerrada ({len(e.cerrada)}):</b> "
                        + (" ".join(formato_pos(p) for p in e.cerrada) or "(vacía)")
                        + f" &nbsp;·&nbsp; <b>Creados:</b> {e.creados} &nbsp;·&nbsp; "
                          f"<b>Expandidos:</b> {e.expandidos}"))
        H.append(KeepTogether(bloque))

    ejemplos = [1, 4]
    H += [Spacer(1, 6)]
    for k in ejemplos:
        H += [imagen(img_it(k), ancho_util / cm),
              P(f"Figura {ejemplos.index(k) + 2}. Estado del algoritmo en la iteración {k} "
                "(tablero + variables).", "pie")]

    # ¿Dónde hubo actualizaciones de g?
    actualizaciones = [(e.iteracion, v) for e in res.traza for v in e.vecinos
                       if v["accion"].startswith("MEJOR")]
    if actualizaciones:
        H.append(P("Actualización de caminos en la lista abierta", "h2"))
        for it, v in actualizaciones:
            padre = res.traza[it].actual["pos"]
            H.append(P(f"En la iteración {it}, al expandir {formato_pos(padre)}, se encontró un camino más "
                       f"barato hacia {formato_pos(v['pos'])}: {v['accion'].split(' - ')[1]}. Esto muestra que "
                       "A* no se queda con el primer camino que encuentra: si una ruta alternativa es más "
                       "barata, corrige el g(n) y el puntero al padre antes de que el nodo sea cerrado."))

    H += [PageBreak(), P("6.1 Tabla resumen de todas las iteraciones", "h2"),
          P("Para cada iteración: nodo extraído (el de menor f en la lista abierta), sus valores, los vecinos "
            "nuevos que generó, el tamaño de las listas y los contadores acumulados.")]
    datos = [["It.", "Nodo extraído", "g", "h", "f", "Vecinos generados / actualizados",
              "Abierta", "Cerrada", "Creados", "Expandidos"]]
    for e in res.traza:
        if e.actual is None:
            datos.append(["0", "– (inicio)", "–", "–", "–", "(0,0) insertado", str(len(e.abierta)),
                          "0", str(e.creados), "0"])
            continue
        a = e.actual
        gen = [formato_pos(v["pos"]) + ("*" if v["accion"].startswith("MEJOR") else "")
               for v in e.vecinos if v["accion"].startswith(("NUEVO", "MEJOR"))]
        datos.append([str(e.iteracion), formato_pos(a["pos"]) + (" META" if e.es_meta else ""),
                      formato_num(a["g"]), str(a["h"]), formato_num(a["f"]),
                      ", ".join(gen) if gen else ("fin" if e.es_meta else "ninguno"),
                      str(len(e.abierta)), str(len(e.cerrada)), str(e.creados), str(e.expandidos)])
    fila_meta = len(datos) - 1
    H.append(tabla(datos, [0.8 * cm, 2.3 * cm, 0.8 * cm, 0.8 * cm, 0.8 * cm, 4.4 * cm, 1.6 * cm,
                           1.6 * cm, 1.5 * cm, 1.8 * cm], tam=7.6,
                   estilo_extra=[("BACKGROUND", (0, fila_meta), (-1, fila_meta), colors.HexColor("#dcfce7"))]))
    H.append(P("* = vecino que ya estaba en la lista abierta y cuyo g(n) se mejoró (actualización).", "pie"))

    # ----------------------------------------------------------- 7
    desglose = [["Paso", "Casilla", "Tipo de terreno", "Coste", "g acumulado", "h", "f = g + h"]]
    acum = 0
    for i, p in enumerate(res.camino):
        c = coste_casilla(TABLERO, p) if i else 0
        acum += c
        v = TABLERO[p[0]][p[1]]
        tipo = {"B": "Bombero (inicio)", "S": "Superviviente (meta)"}.get(v, DESCRIPCION_COSTES.get(v, ""))
        tipo = tipo.replace("Impedimento ", "").replace(" / Transitable", "")
        h = manhattan(p, META)
        desglose.append([str(i), formato_pos(p), tipo, formato_num(c), formato_num(acum), str(h),
                         formato_num(acum + h)])
    H += [PageBreak(), P("7. Solución: ruta óptima y espacio de búsqueda", "h1"),
          P("7.1 Ruta óptima", "h2"),
          P("<b>Ruta encontrada:</b> " + " → ".join(formato_pos(p) for p in res.camino)),
          P(f"<b>Coste total g(7,7) = {formato_num(res.coste)}</b> · {len(res.camino) - 1} movimientos · "
            f"{res.iteraciones} iteraciones · <b>{res.creados} nodos creados</b> · "
            f"<b>{res.expandidos} nodos expandidos</b> · {res.actualizados} actualización(es) de g."),
          tabla(desglose, [1.4 * cm, 1.7 * cm, 5.7 * cm, 1.3 * cm, 2.3 * cm, 1.2 * cm, ancho_util - 13.6 * cm],
                tam=8.4),
          Spacer(1, 8),
          P("<b>Interpretación (Paso 3 del enunciado).</b> La ruta baja por la columna 2 y luego avanza por la "
            "fila 7. El algoritmo decidió <b>atravesar</b> tres casillas de escombros leves (coste 2) en (0,2), "
            "(3,2) y (7,3) porque rodearlas resultaba más caro, y <b>evitó</b> las casillas de coste 4 y 7 "
            "cercanas al camino, como (0,3), (1,3), (4,3), (6,2) y (7,2), rodeándolas por vías libres. "
            "La mejor alternativa por el lado derecho del tablero, …→(2,4)→(2,5)→(3,5)→(4,5)→(5,5)→(5,6)→(5,7)"
            "→(6,7)→(7,7), obliga a pasar por (2,5) con coste 4 y (4,5) con coste 2 y cuesta 25, por eso fue "
            "descartada. El coste final incluye los 7 puntos de entrar a la casilla del Superviviente, que son "
            "inevitables para cualquier ruta."),
          imagen(img("02_ruta_optima.png"), 12.5),
          P("Figura 4. Ruta óptima sobre el tablero, con el g acumulado en cada casilla.", "pie"),
          P("7.2 Visualización del espacio de búsqueda", "h2"),
          P("La siguiente figura muestra <b>cómo exploró</b> A*: cada casilla lleva el número de orden en que "
            "fue extraída de la lista abierta (entró en la lista cerrada). Las casillas con recuadro azul "
            "quedaron generadas en la lista abierta sin llegar a expandirse, y las marcadas \"no generado\" "
            "nunca fueron alcanzadas por la búsqueda."),
          imagen(img("03_espacio_busqueda.png"), 12.5),
          P("Figura 5. Espacio de búsqueda explorado y orden de expansión.", "pie"),
          P("Se observa que la búsqueda avanza primero por la zona izquierda y central (nodos 1 a 20), donde "
            "f(n) es más bajo, llega hasta la fila 7 y solo después, cuando esos caminos dejan de ser los más "
            "prometedores, abre la zona derecha del tablero. Las casillas (0,6) y (0,7) nunca se generaron: "
            "sus vecinos (0,5) y (1,7) quedaron en la lista abierta con f = 23, igual que la meta, y la meta "
            "(h = 0) se extrajo antes por el criterio de desempate, terminando la búsqueda."),
          P("7.3 Efecto de la heurística en la exploración", "h2"),
          P("Para evidenciar el aporte de h(n) se ejecutó el mismo algoritmo con h(n) = 0 (búsqueda de coste "
            "uniforme). Ambos encuentran el mismo coste óptimo, lo cual confirma de nuevo que Manhattan no "
            "altera la optimalidad, pero A* con Manhattan necesita menos trabajo:")]
    datos = [["Métrica", "A* (h = Manhattan)", "h = 0 (sin heurística)"],
             ["Coste de la ruta", formato_num(res.coste), formato_num(res_h0.coste)],
             ["Iteraciones", str(res.iteraciones), str(res_h0.iteraciones)],
             ["Nodos creados", str(res.creados), str(res_h0.creados)],
             ["Nodos expandidos", str(res.expandidos), str(res_h0.expandidos)]]
    H += [tabla(datos, [5 * cm, 5 * cm, 5 * cm], tam=9), Spacer(1, 6),
          imagen(img("04_comparacion_h0.png"), ancho_util / cm),
          P("Figura 6. Orden de expansión con Manhattan (izquierda) y sin heurística (derecha).", "pie"),
          P("La mejora es moderada porque, como se explicó en la Sección 5.5, la heurística subestima bastante "
            "el coste real en este tablero con muchos muros e impedimentos. Aun así, la heurística orienta la "
            "búsqueda hacia el superviviente y evita expandir casillas que nunca podrían formar parte de una "
            "ruta mejor.")]

    # ----------------------------------------------------------- 8
    H += [PageBreak(), P("8. Implementación en Python y visualización", "h1"),
          P("El proyecto está implementado en Python 3 con las bibliotecas matplotlib (gráficos y visor "
            "interactivo), Pillow (animación GIF) y reportlab (este informe)."),
          tabla([["Archivo", "Contenido"],
                 ["astar_rescate.py", "Matriz 8×8 del enunciado, costes, Distancia de Manhattan, algoritmo A* "
                                      "con lista abierta y cerrada, reconstrucción del camino, registro de la "
                                      "traza por iteración y verificación de admisibilidad/consistencia."],
                 ["interfaz.py", "Interfaz gráfica animada (Tkinter) para recorrer la búsqueda paso a paso, "
                                 "con animación en cada celda y todas las variables del algoritmo."],
                 ["visualizacion.py", "Dibujo del tablero, ruta óptima, espacio de búsqueda, imagen por "
                                      "iteración, animación GIF y visor clásico (matplotlib)."],
                 ["generar_informe.py", "Genera este informe PDF a partir de los resultados reales."],
                 ["main.py", "Programa principal: ejecuta todo y abre la interfaz animada."]],
                [4 * cm, ancho_util - 4 * cm], tam=9),
          Spacer(1, 8),
          P("<b>Ejecución:</b>"),
          P("pip install matplotlib pillow reportlab<br/>"
            "python main.py &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# todo + interfaz animada<br/>"
            "python main.py --sin-visor &nbsp;# solo genera resultados e informe<br/>"
            "python main.py --solo-visor # solo abre la interfaz animada", "codigo"),
          P("<b>Resultados generados en la carpeta <font face='Mono'>resultados/</font>:</b>"),
          V("<font face='Mono'>traza_astar.txt</font>: traza completa en texto (cada iteración con el nodo "
            "extraído, la evaluación de sus vecinos, lista abierta, lista cerrada y contadores)."),
          V("<font face='Mono'>01_tablero_inicial.png</font>, <font face='Mono'>02_ruta_optima.png</font>, "
            "<font face='Mono'>03_espacio_busqueda.png</font>, <font face='Mono'>04_comparacion_h0.png</font>, "
            "<font face='Mono'>05_admisibilidad_heuristica.png</font>."),
          V("<font face='Mono'>iteraciones/iteracion_XX.png</font>: una imagen por iteración con el tablero y "
            "todas las variables importantes."),
          V("<font face='Mono'>animacion_astar.gif</font>: animación de la búsqueda completa."),
          P("<b>Interfaz animada.</b> Muestra a la izquierda el tablero y a la derecha las variables del "
            "algoritmo. En cada iteración: (1) un selector magenta se desliza hasta el nodo de menor f extraído de "
            "la lista abierta; (2) la celda cambia de color al entrar en la lista cerrada y recibe su número de "
            "orden #k; (3) se lanzan haces hacia los 4 vecinos y cada celda reacciona según el resultado: azul = "
            "nuevo nodo creado en la lista abierta, ámbar = mejora de g, rojo = casilla bloqueada X, gris = ya "
            "estaba en la lista cerrada. Los contadores de nodos creados y expandidos, el tamaño de ambas listas, "
            "la tabla de la lista abierta ordenada por f y la lista cerrada se actualizan con animación. Al "
            "extraer la meta, el bombero recorre la ruta óptima y las celdas se tiñen de verde. Se controla con "
            "botones, una línea de tiempo, velocidad ajustable y teclado (← →, espacio, Inicio, Fin)."),
          *([imagen(img("interfaz_animada.png"), ancho_util / cm),
             P("Figura 7. Interfaz animada durante la iteración 34: haces hacia los vecinos (azul = nuevo, "
               "ámbar = mejora de g) y listas abierta y cerrada.", "pie")]
            if os.path.exists(img("interfaz_animada.png")) else []),
          imagen(img_it(res.iteraciones), ancho_util / cm),
          P(f"Figura 8. Última iteración ({res.iteraciones}): la meta (7,7) se extrae de la lista abierta y se "
            "dibuja la ruta óptima.", "pie")]

    # ----------------------------------------------------------- 9
    H += [P("9. Conclusiones", "h1"),
          V(f"A* encontró la ruta óptima desde el Bombero (0,0) hasta el Superviviente (7,7) con un coste total "
            f"de <b>{formato_num(res.coste)}</b> en {len(res.camino) - 1} movimientos, creando {res.creados} "
            f"nodos y expandiendo {res.expandidos}."),
          V("La Distancia de Manhattan es admisible y consistente porque cada movimiento en 4 direcciones "
            "reduce la distancia en a lo sumo 1 y cuesta al menos 1; esto se demostró formalmente y se verificó "
            "casilla por casilla comparando h(n) con el coste real h*(n)."),
          V("Gracias a la admisibilidad, detener la búsqueda al extraer la meta de la lista abierta garantiza "
            "la optimalidad; gracias a la consistencia, no es necesario reabrir nodos de la lista cerrada."),
          V("El algoritmo balancea entre rodear y atravesar zonas de riesgo: aceptó escombros leves (coste 2) "
            "cuando eran la opción más barata y evitó las zonas de humo (4) y fuego/agua (7)."),
          V("La visualización de la lista abierta, la lista cerrada y los contadores permite seguir cada "
            "decisión del algoritmo y comprobar que siempre elige el nodo de menor f(n).")]

    # ----------------------------------------------------------- ANEXO
    H += [PageBreak(), P("Anexo A. Traza completa de la lista abierta y la lista cerrada", "h1"),
          P("Lista abierta al terminar cada iteración, en el orden en que se extraerán (formato "
            "(F,C):f). La lista cerrada crece un nodo por iteración, en el orden indicado en la columna "
            "\"Entra a cerrada\". La traza completa con g, h y padre de cada nodo está en "
            "<font face='Mono'>resultados/traza_astar.txt</font>.")]
    datos = [["It.", "Entra a cerrada", "Lista abierta (F,C):f", "|A|", "|C|"]]
    for e in res.traza:
        entra = formato_pos(e.actual["pos"]) if e.actual else "–"
        datos.append([str(e.iteracion), entra, _lista_abierta_txt(e.abierta),
                      str(len(e.abierta)), str(len(e.cerrada))])
    H.append(tabla(datos, [0.8 * cm, 2.1 * cm, ancho_util - 4.9 * cm, 1 * cm, 1 * cm], tam=7.4))
    H += [Spacer(1, 8), P("<b>Lista cerrada final (orden de expansión):</b> "
                          + " → ".join(formato_pos(p) for p in res.orden_expansion))]

    doc.build(H, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
    return ruta_pdf


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    from visualizacion import generar_todas_las_figuras
    r = a_estrella()
    h0 = generar_todas_las_figuras(r)
    print(generar_informe(r, h0))
