"""Escribe el brief de hoy: recopila, analiza, redacta, verifica y te lo enseña antes de publicarlo.

    python generar.py             con datos en vivo; si una fuente falla, con su copia
    python generar.py --copia     con los datos de datos/copia.json (el LLM sí necesita internet)
    python generar.py --dibujar   escribe grafo.md con el dibujo del grafo y termina

Hacen falta los cinco peldaños en verde y una clave de LLM en .env.
"""

import argparse
import sys
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

import brief
import modelos


def resumen(nodo: str, cambios: dict) -> str:
    """Una línea con lo que ha hecho cada nodo."""
    if nodo == "recopilar":
        texto = f"{len(cambios['series'])} series y {len(cambios['titulares'])} titulares"
        return texto + "".join(f"\n             {a}" for a in cambios["avisos"])
    if nodo == "analizar":
        return f"{len(cambios['cifras'])} cifras calculadas con Python"
    if nodo == "redactar":
        return f"borrador {cambios['intentos']}"
    if nodo == "verificar":
        problemas = cambios["problemas"]
        return "todos los números y citas cuadran" if not problemas else \
            f"{len(problemas)} problemas" + "".join(f"\n             {p}" for p in problemas)
    if nodo == "aprobar":
        return "aprobado" if cambios.get("aprobado") else "rechazado"
    if nodo == "publicar":
        return cambios["archivo"]
    return f"cambia {', '.join(cambios)}" if cambios else "no cambia nada"


def preguntar(pausa: dict) -> dict:
    """Enseña el borrador y pide a la persona qué hacer. Devuelve la respuesta para `aprobar`."""
    print("\n" + "-" * 70 + f"\n{pausa['borrador']}\n" + "-" * 70)
    if pausa["problemas"]:
        print("La verificación encontró problemas que el modelo no ha corregido:")
        for p in pausa["problemas"]:
            print(f"  {p}")
    while True:
        accion = input("\n¿Aprobar (a), editar (e) o rechazar (r)? ").strip().lower()[:1]
        if accion == "a":
            return {"accion": "aprobar"}
        if accion == "r":
            return {"accion": "rechazar"}
        if accion == "e":
            brief.SALIDA.mkdir(exist_ok=True)
            borrador = brief.SALIDA / "borrador.md"
            borrador.write_text(pausa["borrador"], encoding="utf-8")
            input(f"Edita {borrador}, guárdalo y pulsa Enter. ")
            return {"accion": "editar", "texto": borrador.read_text(encoding="utf-8")}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--copia", action="store_true", help="usa solo los datos de datos/copia.json")
    p.add_argument("--dibujar", action="store_true", help="escribe grafo.md con el dibujo del grafo")
    args = p.parse_args()

    try:
        grafo = brief.construir_grafo(InMemorySaver())
        if args.dibujar:
            (brief.AQUI / "grafo.md").write_text(f"```mermaid\n{grafo.get_graph().draw_mermaid()}```\n",
                                                 encoding="utf-8")
            print("Dibujo en grafo.md. Ábrelo con la vista previa de Markdown de tu editor.")
            return
        lista = modelos.proveedores()
        print(f"LLM: {', '.join(f'{modelos.modelo_de(x)} ({x})' for x in lista) or 'ninguno, mira .env'}\n")
        # Cada ejecución es un hilo nuevo: el checkpointer guarda dónde se paró cada uno.
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        entrada = {"usar_copia": args.copia}
        while True:
            pausa = None
            for paso in grafo.stream(entrada, config, stream_mode="updates"):
                for nodo, cambios in paso.items():
                    if nodo == "__interrupt__":
                        pausa = cambios[0].value
                    else:
                        print(f"{nodo:>10}   {resumen(nodo, cambios)}")
            if pausa is None:
                break
            entrada = Command(resume=preguntar(pausa))
    except NotImplementedError:
        sys.exit("Te falta algún peldaño en tu brief.py. Ponlos en verde con pytest y vuelve.")


if __name__ == "__main__":
    main()
