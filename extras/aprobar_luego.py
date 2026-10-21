"""Parar hoy y aprobar mañana: el mismo grafo, con el estado guardado en disco (SQLite) en vez de en memoria.

    python extras/aprobar_luego.py [--copia]        corre hasta la pausa, guarda el estado y termina
    python extras/aprobar_luego.py --seguir HILO    otro día o en otra terminal: enseña el borrador y pide a, e o r
    python extras/aprobar_luego.py --historia HILO  cada paso que guardó el checkpointer, del primero al último

Con `InMemorySaver`, el estado muere con el proceso. Con `SqliteSaver` queda en brief.sqlite, y la persona
puede aprobar cuando lo lea. En producción sería una base de datos de verdad, como Postgres.

Necesita `pip install -r extras/requirements.txt` y los cinco peldaños de brief.py en verde.
"""

import argparse
import sqlite3
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

import brief
import generar

BASE = brief.AQUI / "brief.sqlite"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--copia", action="store_true", help="usa solo los datos de datos/copia.json")
    p.add_argument("--seguir", metavar="HILO", help="reanuda un brief parado")
    p.add_argument("--historia", metavar="HILO", help="enseña los pasos guardados de un brief")
    args = p.parse_args()

    grafo = brief.construir_grafo(SqliteSaver(sqlite3.connect(BASE, check_same_thread=False)))
    hilo = args.seguir or args.historia or uuid.uuid4().hex[:8]
    config = {"configurable": {"thread_id": hilo}}

    if args.historia:
        fotos = list(grafo.get_state_history(config))
        if not fotos:
            sys.exit(f"No hay nada guardado del hilo {hilo}.")
        for foto in reversed(fotos):
            v = foto.values
            print(f"paso {foto.metadata.get('step', '?'):>2}   siguiente: {', '.join(foto.next) or 'fin':<10}   "
                  f"borradores: {v.get('intentos', 0)}   problemas: {len(v.get('problemas') or [])}")
        print("\nCada línea es un checkpoint. Con su config, grafo.invoke(None, foto.config) seguiría desde ahí.")
        return

    if args.seguir:
        foto = grafo.get_state(config)
        if not foto.interrupts:
            sys.exit(f"El hilo {hilo} no está esperando a nadie.")
        final = grafo.invoke(Command(resume=generar.preguntar(foto.interrupts[0].value)), config)
        print(final.get("archivo") or "Rechazado: no se publica nada.")
        return

    for paso in grafo.stream({"usar_copia": args.copia}, config, stream_mode="updates"):
        for nodo, cambios in paso.items():
            if nodo != "__interrupt__":
                print(f"{nodo:>10}   {generar.resumen(nodo, cambios)}")
    print(f"\nParado, esperando a una persona. El estado está en {BASE.name}. Para aprobar, cuando quieras:\n"
          f"  python extras/aprobar_luego.py --seguir {hilo}")


if __name__ == "__main__":
    main()
