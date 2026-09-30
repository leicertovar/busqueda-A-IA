"""
Servidor local de la interfaz web (web/index.html).

Python calcula A* y la página solo lo dibuja:
    GET  /api/datos      -> búsqueda sobre el tablero del enunciado
    POST /api/astar      -> búsqueda sobre un tablero editado  {"tablero": [[...], ...]}
    GET  /api/aleatorio  -> edificio aleatorio con solución y su búsqueda
El resto de rutas sirve los archivos de la carpeta web/.
"""

import dataclasses
import json
import os
import random
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from astar_rescate import INF, INICIO, META, TABLERO, a_estrella

CARPETA_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
VALORES = {1, 2, 4, 7, "X", "B", "S"}


def _limpio(x):
    """Convierte la salida de Python a JSON (tuplas -> listas, ∞ -> null, 3.0 -> 3)."""
    if isinstance(x, dict):
        return {k: _limpio(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_limpio(v) for v in x]
    if isinstance(x, float):
        if x == INF:
            return None
        return int(x) if x.is_integer() else x
    return x


def _buscar(tablero, valor):
    return next(((f, c) for f, fila in enumerate(tablero) for c, v in enumerate(fila) if v == valor), None)


def datos_busqueda(tablero=TABLERO, inicio=INICIO, meta=META, resultado=None) -> dict:
    """Ejecuta A* sobre `tablero` y devuelve todo lo que necesita la interfaz web."""
    if resultado is None:
        resultado = a_estrella(tablero, inicio, meta)
    return _limpio({
        "tablero": tablero,
        "inicio": inicio,
        "meta": meta,
        "encontrado": resultado.encontrado,
        "camino": resultado.camino,
        "coste": resultado.coste,
        "creados": resultado.creados,
        "expandidos": resultado.expandidos,
        "actualizados": resultado.actualizados,
        "iteraciones": resultado.iteraciones,
        "traza": [dataclasses.asdict(e) for e in resultado.traza],
    })


def validar_tablero(tablero):
    """Comprueba que el tablero editado sea 8x8, con valores válidos y un único B y S."""
    if not (isinstance(tablero, list) and len(tablero) == 8
            and all(isinstance(f, list) and len(f) == 8 for f in tablero)):
        raise ValueError("el tablero debe ser 8x8")
    if any(v not in VALORES or isinstance(v, bool) for f in tablero for v in f):
        raise ValueError("valor de casilla no válido")
    planos = [v for f in tablero for v in f]
    if planos.count("B") != 1 or planos.count("S") != 1:
        raise ValueError("debe haber exactamente un B y un S")
    return _buscar(tablero, "B"), _buscar(tablero, "S")


def tablero_aleatorio(intentos=300):
    """Genera edificios al azar hasta encontrar uno con una ruta de al menos 9 movimientos."""
    for _ in range(intentos):
        t = [[random.choices([1, 2, 4, 7, "X"], [50, 14, 11, 8, 17])[0] for _ in range(8)] for _ in range(8)]
        inicio = (random.randrange(3), random.randrange(8))
        meta = (random.randrange(5, 8), random.randrange(8))
        t[inicio[0]][inicio[1]] = "B"
        t[meta[0]][meta[1]] = "S"
        r = a_estrella(t, inicio, meta)
        if r.encontrado and len(r.camino) > 9:
            return datos_busqueda(t, inicio, meta, r)
    return datos_busqueda()


class Manejador(SimpleHTTPRequestHandler):
    datos_iniciales = None

    def _json(self, obj, estado=200):
        cuerpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(estado)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        if self.path == "/api/datos":
            return self._json(self.datos_iniciales)
        if self.path == "/api/aleatorio":
            return self._json(tablero_aleatorio())
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/astar":
            return self._json({"error": "ruta no encontrada"}, 404)
        try:
            n = int(self.headers.get("Content-Length", 0))
            tablero = json.loads(self.rfile.read(n))["tablero"]
            inicio, meta = validar_tablero(tablero)
        except (ValueError, KeyError, TypeError) as e:
            return self._json({"error": str(e)}, 400)
        self._json(datos_busqueda(tablero, inicio, meta))

    def end_headers(self):
        # Evita que el navegador sirva app.js / estilos antiguos tras editar el proyecto
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass  # silencia el registro de cada petición en la consola


def iniciar(resultado=None, puerto=8000, abrir=True):
    """Arranca el servidor en 127.0.0.1 (prueba puertos siguientes si está ocupado) y abre el navegador."""
    Manejador.datos_iniciales = datos_busqueda(resultado=resultado)
    manejador = partial(Manejador, directory=CARPETA_WEB)
    for p in range(puerto, puerto + 20):
        try:
            servidor = ThreadingHTTPServer(("127.0.0.1", p), manejador)
            break
        except OSError:
            continue
    else:
        raise OSError(f"No hay puertos libres entre {puerto} y {puerto + 19}")
    url = f"http://127.0.0.1:{servidor.server_port}/"
    print(f"Interfaz web en {url}  (Ctrl+C para detener)")
    if abrir:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    iniciar()
