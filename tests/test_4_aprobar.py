from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from brief import Estado, aprobar

CONFIG = {"configurable": {"thread_id": "test"}}
ENTRADA = {"borrador": "El Euríbor sube [C1].", "problemas": ["El 0,4 no está en [C1]"]}


def grafo_de_un_nodo():
    """Un grafo con solo el nodo aprobar: START → aprobar → END."""
    grafo = StateGraph(Estado)
    grafo.add_node("aprobar", aprobar)
    grafo.add_edge(START, "aprobar")
    grafo.add_edge("aprobar", END)
    return grafo.compile(checkpointer=InMemorySaver())


def test_para_el_grafo_y_ensena_borrador_y_problemas():
    resultado = grafo_de_un_nodo().invoke(ENTRADA, CONFIG)
    assert resultado["__interrupt__"][0].value == ENTRADA


def test_aprobar():
    grafo = grafo_de_un_nodo()
    grafo.invoke(ENTRADA, CONFIG)
    resultado = grafo.invoke(Command(resume={"accion": "aprobar"}), CONFIG)
    assert resultado["aprobado"] is True and resultado["borrador"] == ENTRADA["borrador"]


def test_editar_cambia_el_borrador():
    grafo = grafo_de_un_nodo()
    grafo.invoke(ENTRADA, CONFIG)
    resultado = grafo.invoke(Command(resume={"accion": "editar", "texto": "Versión corregida."}), CONFIG)
    assert resultado["aprobado"] is True and resultado["borrador"] == "Versión corregida."


def test_rechazar():
    grafo = grafo_de_un_nodo()
    grafo.invoke(ENTRADA, CONFIG)
    assert grafo.invoke(Command(resume={"accion": "rechazar"}), CONFIG)["aprobado"] is False


def test_sin_problemas_en_el_estado_ensena_una_lista_vacia():
    resultado = grafo_de_un_nodo().invoke({"borrador": "Todo bien."}, CONFIG)
    assert resultado["__interrupt__"][0].value == {"borrador": "Todo bien.", "problemas": []}
