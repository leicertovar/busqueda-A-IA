"""
PROYECTO DE INTELIGENCIA ARTIFICIAL
Algoritmo de Búsqueda A* para Rescate de Emergencia Post-Terremoto

Uso:
    python main.py                 -> ejecuta A*, genera resultados + informe PDF y abre el visor
    python main.py --sin-visor     -> igual, pero sin abrir la ventana interactiva
    python main.py --solo-visor    -> solo abre la interfaz animada paso a paso
    python main.py --visor-clasico -> usa el visor de matplotlib en lugar de la interfaz animada
    python main.py --web           -> abre la interfaz web (web/index.html) en el navegador
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
    p.add_argument("--sin-visor", action="store_true", help="no abrir la ventana interactiva")
    p.add_argument("--solo-visor", action="store_true", help="solo abrir el visor interactivo")
    p.add_argument("--visor-clasico", action="store_true",
                   help="usar el visor de matplotlib en lugar de la interfaz animada")
    p.add_argument("--web", action="store_true",
                   help="exportar la traza y abrir la interfaz web en el navegador")
    args = p.parse_args()

    resultado = a_estrella()

    if args.web:
        import pathlib
        import webbrowser
        from exportar_web import exportar
        ruta = exportar(resultado)
        print(f"Abriendo interfaz web: {ruta}")
        webbrowser.open(pathlib.Path(ruta).as_uri())
        return

    if not args.solo_visor:
        import matplotlib
        if args.sin_visor:
            matplotlib.use("Agg")

        # 1. Traza completa en consola y en archivo de texto
        traza = texto_traza(resultado)
        adm, cons, _, _ = verificar_admisibilidad()
        traza += (f"\nHeurística admisible (h(n) <= h*(n) en todas las casillas): {adm}"
                  f"\nHeurística consistente (h(n) <= c(n,n') + h(n')):          {cons}\n")
        print(traza)
        os.makedirs(CARPETA, exist_ok=True)
        with open(os.path.join(CARPETA, "traza_astar.txt"), "w", encoding="utf-8") as fh:
            fh.write(traza)

        # 2. Figuras, imágenes por iteración y GIF
        from visualizacion import generar_todas_las_figuras
        print("\nGenerando visualizaciones...")
        res_h0 = generar_todas_las_figuras(resultado, CARPETA)

        # 3. Informe PDF
        from generar_informe import generar_informe
        ruta_pdf = generar_informe(resultado, res_h0, CARPETA, "Informe_Proyecto_AStar.pdf")
        print(f"  Informe PDF generado: {ruta_pdf}")
        print(f"\nTodos los resultados están en la carpeta '{CARPETA}/'.")

    if not args.sin_visor:
        if args.visor_clasico:
            from visualizacion import VisorAEstrella
            print("Abriendo visor clásico (matplotlib)...")
            VisorAEstrella(resultado).mostrar()
        else:
            from interfaz import InterfazAEstrella
            print("Abriendo interfaz animada (← → para avanzar, espacio para reproducir)...")
            InterfazAEstrella(resultado).mostrar()


if __name__ == "__main__":
    main()
