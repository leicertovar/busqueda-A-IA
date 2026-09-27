# Proyecto de Inteligencia Artificial
## Algoritmo de Búsqueda A* para Rescate de Emergencia Post-Terremoto

Implementación en Python del algoritmo A* sobre la matriz 8 × 8 del enunciado:
un Bombero en **(0,0)** debe llegar al Superviviente en **(7,7)** con el menor coste total,
usando `f(n) = g(n) + h(n)` y la **Distancia de Manhattan** como heurística.

### Instalación y ejecución
```bash
pip install -r requirements.txt
python main.py                # ejecuta A*, genera figuras, GIF, informe PDF y abre el visor
python main.py --sin-visor    # solo genera los resultados y el informe
python main.py --solo-visor   # solo abre el visor interactivo paso a paso
```

### Archivos
| Archivo | Contenido |
|---|---|
| `astar_rescate.py` | Matriz y costes del enunciado, heurística Manhattan, algoritmo A* (lista abierta / cerrada), traza por iteración, verificación de admisibilidad y consistencia |
| `interfaz.py` | Interfaz gráfica animada (Tkinter) para recorrer la búsqueda paso a paso |
| `visualizacion.py` | Tablero, ruta óptima, espacio de búsqueda, una imagen por iteración, GIF y visor clásico |
| `generar_informe.py` | Informe PDF (editar aquí `INTEGRANTES` y `DOCENTE`) |
| `main.py` | Programa principal |
| `GUION_VIDEO.md` | Propuesta de guion para el video (≤ 10 min, 4 integrantes) |

### Resultados (`resultados/`)
- `Informe_Proyecto_AStar.pdf` – informe completo (rúbrica 1)
- `02_ruta_optima.png`, `03_espacio_busqueda.png`, `04_comparacion_h0.png` – solución y exploración (rúbrica 2)
- `iteraciones/iteracion_XX.png`, `animacion_astar.gif`, `traza_astar.txt` – lista abierta, lista cerrada, nodos creados y expandidos en cada iteración (rúbrica 3)
- `05_admisibilidad_heuristica.png` – comparación h(n) vs. coste real h*(n)

### Resultado obtenido
- Ruta: (0,0) → (0,1) → (0,2) → (1,2) → (2,2) → (3,2) → (4,2) → (5,2) → (5,3) → (6,3) → (7,3) → (7,4) → (7,5) → (7,6) → (7,7)
- Coste total: **17** · 14 movimientos · 21 iteraciones · 29 nodos creados · 20 nodos expandidos

### Convenciones
- Mover a una casilla cuesta el peso de esa casilla (1, 2, 4, 7; X = ∞). B = 1 y S = 1
  (aclaración del profesor: se toman como puntos de valor 1; conservan su identificación visual B y S).
- Vecinos en el orden: arriba, abajo, izquierda, derecha.
- Desempate en la lista abierta: menor f → menor h → el creado primero.
- La búsqueda termina cuando la meta (7,7) es **extraída** de la lista abierta.

### Interfaz animada (`interfaz.py`, Tkinter)
Tema oscuro con animación en cada celda:
- El **selector magenta** se desliza hasta el nodo de menor f extraído de la lista abierta (con halo pulsante).
- La celda **pasa a la lista cerrada** con una transición de color y aparece su número de orden `#k`.
- Se lanzan **haces hacia los 4 vecinos**: azul = nuevo en lista abierta (la celda aparece con rebote),
  ámbar = mejora de g, rojo = bloqueado (X), gris = ya en lista cerrada.
- Contadores animados (iteración, nodos creados/expandidos, tamaño de las listas, mejoras de g),
  tabla de la lista abierta (siguiente en magenta, nuevos en azul, mejorados en ámbar) y lista cerrada.
- Al extraer la meta, **el bombero recorre la ruta óptima** y las celdas se tiñen de verde.
- Pasar el ratón sobre una celda muestra su terreno, coste, g, h, f, padre y lista.

Controles: `«  ‹  Reproducir  ›  »`, línea de tiempo (clic o arrastre), velocidad `− +`, árbol de búsqueda.
Teclado: `←` `→` `espacio` `Inicio` `Fin` `+` `−` `A`.
`python main.py --visor-clasico` abre el visor anterior de matplotlib.
