"""
PROYECTO DE INTELIGENCIA ARTIFICIAL
Algoritmo de Búsqueda A* para Rescate de Emergencia Post-Terremoto

Uso:
    python main.py                 -> ejecuta A*, guarda la traza y abre la interfaz web
    python main.py --resultados    -> además genera las figuras, imágenes por iteración y GIF
    python main.py --tk            -> abre la interfaz animada de escritorio (Tkinter) en lugar de la web
    python main.py --visor-clasico -> abre el visor de matplotlib en lugar de la web
    python main.py --sin-navegador -> arranca el servidor web sin abrir el navegador
"""

import argparse
import os
import sys

from astar_rescate import a_estrella, texto_traza, verificar_admisibilidad

CARPETA = "resultados"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(description="A* - Rescate post-terremoto")
    p.add_argument("--resultados", action="store_true",
                   help="generar figuras, imágenes por iteración y GIF en resultados/")
    p.add_argument("--tk", action="store_true", help="abrir la interfaz de escritorio (Tkinter)")
    p.add_argument("--visor-clasico", action="store_true", help="abrir el visor de matplotlib")
    p.add_argument("--sin-navegador", action="store_true", help="no abrir el navegador automáticamente")
    p.add_argument("--puerto", type=int, default=8000, help="puerto del servidor web (por defecto 8000)")
    args = p.parse_args()

    resultado = a_estrella()

    # Traza completa en consola y en archivo de texto
    traza = texto_traza(resultado)
    adm, cons, _, _ = verificar_admisibilidad()
    traza += (f"\nHeurística admisible (h(n) <= h*(n) en todas las casillas): {adm}"
              f"\nHeurística consistente (h(n) <= c(n,n') + h(n')):          {cons}\n")
    print(traza)
    os.makedirs(CARPETA, exist_ok=True)
    with open(os.path.join(CARPETA, "traza_astar.txt"), "w", encoding="utf-8") as fh:
        fh.write(traza)

    if args.resultados:
        import matplotlib
        matplotlib.use("Agg")
        from visualizacion import generar_todas_las_figuras
        print("\nGenerando visualizaciones...")
        generar_todas_las_figuras(resultado, CARPETA)
        print(f"Figuras generadas en la carpeta '{CARPETA}/'.")

    if args.visor_clasico:
        from visualizacion import VisorAEstrella
        print("Abriendo visor clásico (matplotlib)...")
        VisorAEstrella(resultado).mostrar()
    elif args.tk:
        from interfaz import InterfazAEstrella
        print("Abriendo interfaz animada (← → para avanzar, espacio para reproducir)...")
        InterfazAEstrella(resultado).mostrar()
    else:
        from servidor import iniciar
        iniciar(resultado, puerto=args.puerto, abrir=not args.sin_navegador)


if __name__ == "__main__":
    main()
