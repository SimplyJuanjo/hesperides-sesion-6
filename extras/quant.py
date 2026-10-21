"""Un nodo quant, "quant", entre analizar y redactar: volatilidad realizada y caída desde máximos.

Lo calcula Python y le llega al modelo como cifras nuevas, C12, C13... `verificar` las protege igual que a las
demás: el modelo no puede inventarse una volatilidad.

    python extras/quant.py            el brief con las cifras nuevas
    python extras/quant.py --copia    con los datos de datos/copia.json
    python extras/quant.py --dibujar  el grafo con el nodo nuevo, en grafo.md

Hacen falta los cinco peldaños de brief.py en verde. Cada serie trae unas 25 observaciones, un mes en las
diarias: para ventanas más largas, sube `n` en `serie_bce` y `range` en `serie_yahoo`, en fuentes.py.
"""

import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.graph import END, START, StateGraph

import brief
import generar

# Sesiones de la ventana de la volatilidad.
VENTANA = 20

brief.LECTOR += " Quiere saber también cuánto se mueve la bolsa y cuánto ha caído desde su máximo del mes."


def con_valor(obs: list[list]) -> list[list]:
    return [[f, v] for f, v in obs if v is not None]


def volatilidad(obs: list[list], ventana: int = VENTANA) -> list[list]:
    """Volatilidad realizada anualizada, en %, de cada día con `ventana` rentabilidades logarítmicas detrás."""
    o = con_valor(obs)
    r = [[o[i][0], math.log(o[i][1] / o[i - 1][1])] for i in range(1, len(o))]
    return [[r[i][0], 100 * statistics.stdev(x for _, x in r[i - ventana + 1:i + 1]) * math.sqrt(252)]
            for i in range(ventana - 1, len(r))]


def caida(obs: list[list]) -> list[list]:
    """Caída en % desde el máximo de lo que va de serie, día a día."""
    salida, maximo = [], -math.inf
    for f, v in con_valor(obs):
        maximo = max(maximo, v)
        salida.append([f, 100 * (v / maximo - 1)])
    return salida


def nodo_quant(estado: brief.Estado) -> dict:
    s = estado["series"]
    nuevas = {}
    for clave, nombre in (("ibex", "IBEX 35"), ("stoxx", "Euro Stoxx 50")):
        if clave in s:
            nuevas[f"vol_{clave}"] = {
                "nombre": f"Volatilidad realizada del {nombre} ({VENTANA} sesiones, anualizada)", "unidad": "%",
                "decimales": 1, "fuente": "Yahoo Finance, cálculo propio", "url": s[clave]["url"],
                "obs": volatilidad(s[clave]["obs"])}
    if "ibex" in s:
        nuevas["caida_ibex"] = {
            "nombre": "Caída del IBEX 35 desde su máximo del último mes", "unidad": "%", "decimales": 2,
            "fuente": "Yahoo Finance, cálculo propio", "url": s["ibex"]["url"], "obs": caida(s["ibex"]["obs"])}
    cifras = list(estado["cifras"])
    for c in brief.analizar(nuevas):
        c["id"] = f"C{len(cifras) + 1}"
        cifras.append(c)
    return {"cifras": cifras}


def construir_grafo(checkpointer=None):
    grafo = StateGraph(brief.Estado)
    grafo.add_node("recopilar", brief.nodo_recopilar)
    grafo.add_node("analizar", brief.nodo_analizar)
    grafo.add_node("quant", nodo_quant)
    grafo.add_node("redactar", brief.nodo_redactar)
    grafo.add_node("verificar", brief.nodo_verificar)
    grafo.add_node("aprobar", brief.aprobar)
    grafo.add_node("publicar", brief.nodo_publicar)
    grafo.add_edge(START, "recopilar")
    grafo.add_edge("recopilar", "analizar")
    grafo.add_edge("analizar", "quant")
    grafo.add_edge("quant", "redactar")
    grafo.add_edge("redactar", "verificar")
    grafo.add_conditional_edges("verificar", brief.ruta_tras_verificar, ["redactar", "aprobar"])
    grafo.add_conditional_edges("aprobar", brief.ruta_tras_aprobar, ["publicar", END])
    grafo.add_edge("publicar", END)
    return grafo.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    brief.construir_grafo = construir_grafo
    sys.exit(generar.main())
