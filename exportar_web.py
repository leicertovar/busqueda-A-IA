"""
Exporta la traza de A* a web/datos.js para la interfaz web (web/index.html).

La página no necesita servidor: datos.js define window.DATOS y se carga con <script>.
"""

import dataclasses
import json
import os

from astar_rescate import INF, INICIO, META, TABLERO, Resultado, a_estrella, verificar_admisibilidad

CARPETA_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


def _limpio(x):
    if isinstance(x, dict):
        return {k: _limpio(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_limpio(v) for v in x]
    if isinstance(x, float):
        if x == INF:
            return None
        return int(x) if x.is_integer() else x
    return x


def exportar(resultado: Resultado, carpeta=CARPETA_WEB) -> str:
    adm, cons, _, _ = verificar_admisibilidad()
    datos = {
        "tablero": TABLERO,
        "inicio": INICIO,
        "meta": META,
        "encontrado": resultado.encontrado,
        "camino": resultado.camino,
        "coste": resultado.coste,
        "creados": resultado.creados,
        "expandidos": resultado.expandidos,
        "actualizados": resultado.actualizados,
        "iteraciones": resultado.iteraciones,
        "admisible": adm,
        "consistente": cons,
        "traza": [dataclasses.asdict(e) for e in resultado.traza],
    }
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, "datos.js"), "w", encoding="utf-8") as fh:
        fh.write("window.DATOS = ")
        json.dump(_limpio(datos), fh, ensure_ascii=False)
        fh.write(";\n")
    return os.path.join(carpeta, "index.html")


if __name__ == "__main__":
    import pathlib
    import webbrowser
    ruta = exportar(a_estrella())
    print(f"Interfaz web exportada: {ruta}")
    webbrowser.open(pathlib.Path(ruta).as_uri())
