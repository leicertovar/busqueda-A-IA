# Guion propuesto para el video (máximo 10 minutos)

Requisito de la rúbrica: **cada integrante debe aparecer con cámara** explicando su parte.
Tiempo sugerido para 4 integrantes: ~2 min 20 s cada uno (total ≈ 9 min 30 s).
Si el grupo tiene menos integrantes, repartir los bloques.

---

## Integrante 1 – El problema y el entorno (0:00 – 2:20)
*En pantalla: enunciado y `resultados/01_tablero_inicial.png`.*
1. Presentación del grupo y del proyecto: A* para rescate post-terremoto.
2. El escenario: matriz 8 × 8, Bombero en (0,0), Superviviente en (7,7).
3. Los costes: 1 libre, 2 escombros, 4 grietas/humo, 7 fuego/agua, X bloqueado (∞).
4. Convención: moverse a una casilla cuesta su peso; B = 0 y S = 7.
5. Movimiento en 4 direcciones: arriba, abajo, izquierda, derecha.

## Integrante 2 – El algoritmo A* y el código (2:20 – 4:40)
*En pantalla: `astar_rescate.py`, función `a_estrella`.*
1. f(n) = g(n) + h(n): qué es g (coste real) y qué es h (estimación).
2. Paso 1: inicialización, (0,0) en la lista abierta con g = 0, h = 14, f = 14.
3. Paso 2: extraer el nodo de menor f, pasarlo a la lista cerrada, revisar los 4 vecinos,
   omitir X y cerrados, crear o actualizar nodos.
4. Desempate: menor f → menor h → el más antiguo.
5. Paso 4: se termina cuando la meta sale de la lista abierta; reconstrucción con los padres.

## Integrante 3 – La heurística y su admisibilidad (4:40 – 7:00)
*En pantalla: `resultados/05_admisibilidad_heuristica.png` y la sección 5 del informe.*
1. Manhattan: |F − 7| + |C − 7| = número mínimo de pasos en una cuadrícula de 4 direcciones.
2. Admisibilidad: cada paso reduce h como máximo en 1 y cuesta al menos 1 ⇒ h(n) ≤ h*(n).
3. Consistencia: h(n) ≤ c(n,n') + h(n'), por eso no hace falta reabrir la lista cerrada.
4. Verificación: el programa compara h con el coste real h* en las 50 casillas transitables (todas ≥ 0).
5. Comparación con h = 0: mismo coste 23, pero A* expande 44 nodos en lugar de 49.

## Integrante 4 – Demostración y resultados (7:00 – 9:30)
*En pantalla: `python main.py` y el visor interactivo.*
1. Ejecutar el programa y mostrar la traza en consola.
2. En el visor avanzar iteración por iteración: lista abierta (azul), lista cerrada (gris, #orden),
   nodo actual (magenta), nodos creados y expandidos.
3. Mostrar la iteración donde se actualiza un g (camino más barato encontrado).
4. Mostrar el espacio de búsqueda (`03_espacio_busqueda.png`) y la ruta final:
   coste 23, 14 movimientos, 48 nodos creados, 44 expandidos.
5. Conclusión: A* balanceó entre atravesar escombros (coste 2) y evitar humo y fuego (4 y 7).
   Cierre del grupo.
