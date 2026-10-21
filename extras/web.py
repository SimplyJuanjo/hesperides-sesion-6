"""Noticias de la web con Tavily, como un nodo más: "buscar_web", entre recopilar y analizar.

Tavily es un buscador hecho para LLM: devuelve título, enlace, fecha y un extracto. Las noticias entran como
titulares nuevos, T9, T10..., así que `verificar` las trata como a las del BCE y el Banco de España.

    python extras/web.py
    python extras/web.py --copia      los datos de la copia; la búsqueda web sí sale a internet
    python extras/web.py --dibujar    el grafo con el nodo nuevo, en grafo.md

La clave es gratis y sin tarjeta, en https://app.tavily.com, y va en .env como TAVILY_API_KEY. Sin clave, el
nodo avisa y el brief sigue con los titulares de siempre. Hacen falta los cinco peldaños de brief.py en verde.

El nodo lleva `retry_policy`: si la red falla, LangGraph lo vuelve a intentar solo, hasta tres veces.
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import date
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

import brief
import fuentes
import generar
import modelos

# Qué buscar. Cámbialo por lo que lea tu lector.
BUSQUEDA = "BCE tipos de interés Euríbor zona euro"
DIAS = 7
MAXIMO = 4


def fecha_iso(texto: str | None) -> str:
    """«Tue, 21 Oct 2026 08:00:00 GMT» o «2026-10-21T08:00:00» → «2026-10-21». Sin fecha, la de hoy."""
    if texto:
        try:
            return parsedate_to_datetime(texto).date().isoformat()
        except (TypeError, ValueError):
            if len(texto) >= 10 and texto[4] == "-":
                return texto[:10]
    return date.today().isoformat()


def buscar_tavily(consulta: str, clave: str) -> list[dict]:
    cuerpo = json.dumps({"query": consulta, "topic": "news", "days": DIAS, "max_results": MAXIMO}).encode()
    peticion = urllib.request.Request("https://api.tavily.com/search", data=cuerpo, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {clave}", "User-Agent": "hesperides-sesion-6"})
    with urllib.request.urlopen(peticion, timeout=30, context=fuentes.SSL) as r:
        return json.loads(r.read())["results"]


def nodo_buscar_web(estado: brief.Estado) -> dict:
    clave = modelos.clave("TAVILY_API_KEY")
    if not clave:
        return {"avisos": estado["avisos"] + ["Sin TAVILY_API_KEY en .env: no hay noticias de la web."]}
    try:
        resultados = buscar_tavily(BUSQUEDA, clave)
    except urllib.error.HTTPError as e:
        if e.code >= 500:
            raise  # lo reintenta la retry_policy
        return {"avisos": estado["avisos"] + [f"Tavily respondió {e.code}: mira la clave."]}
    titulares = list(estado["titulares"])
    for r in resultados:
        titulares.append({"id": f"T{len(titulares) + 1}", "fuente": f"Web ({urlparse(r['url']).netloc})",
                          "titulo": r["title"].strip(), "fecha": fecha_iso(r.get("published_date")), "url": r["url"]})
    return {"titulares": titulares}


def reintentar(e: Exception) -> bool:
    """Se reintentan los fallos de red y los errores 5xx; un 401 por una clave mal puesta, no."""
    return isinstance(e, (urllib.error.URLError, TimeoutError)) and not (
        isinstance(e, urllib.error.HTTPError) and e.code < 500)


def construir_grafo(checkpointer=None):
    grafo = StateGraph(brief.Estado)
    grafo.add_node("recopilar", brief.nodo_recopilar)
    grafo.add_node("buscar_web", nodo_buscar_web, retry_policy=RetryPolicy(max_attempts=3, retry_on=reintentar))
    grafo.add_node("analizar", brief.nodo_analizar)
    grafo.add_node("redactar", brief.nodo_redactar)
    grafo.add_node("verificar", brief.nodo_verificar)
    grafo.add_node("aprobar", brief.aprobar)
    grafo.add_node("publicar", brief.nodo_publicar)
    grafo.add_edge(START, "recopilar")
    grafo.add_edge("recopilar", "buscar_web")
    grafo.add_edge("buscar_web", "analizar")
    grafo.add_edge("analizar", "redactar")
    grafo.add_edge("redactar", "verificar")
    grafo.add_conditional_edges("verificar", brief.ruta_tras_verificar, ["redactar", "aprobar"])
    grafo.add_conditional_edges("aprobar", brief.ruta_tras_aprobar, ["publicar", END])
    grafo.add_edge("publicar", END)
    return grafo.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    brief.construir_grafo = construir_grafo
    sys.exit(generar.main())
