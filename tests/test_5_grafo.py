"""El grafo entero, sin internet: los datos salen de datos/copia.json y el LLM es uno falso."""

from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

import brief
import fuentes
import modelos
from brief import MAX_INTENTOS, construir_grafo, ruta_tras_verificar

CONFIG = {"configurable": {"thread_id": "test"}}
INVENTADO = "- La pendiente de la curva es de 0,4 puntos [C1]."


def borrador_bien() -> str:
    c = brief.analizar(fuentes.recopilar(usar_copia=True)["series"])[0]
    return f"- {c['nombre']}: {brief.numero(c['valor'], c['decimales'])} [C1]."


def llm_falso(monkeypatch, respuestas: list[str]) -> list[str]:
    """Sustituye al LLM: contesta las respuestas en orden y repite la última. Devuelve los prompts que recibe."""
    prompts: list[str] = []

    def redactar(prompt: str) -> str:
        prompts.append(prompt)
        return respuestas[min(len(prompts), len(respuestas)) - 1]

    monkeypatch.setattr(modelos, "redactar", redactar)
    return prompts


def test_ruta_sin_problemas_va_a_aprobar():
    assert ruta_tras_verificar({"problemas": [], "intentos": 1}) == "aprobar"


def test_ruta_con_problemas_vuelve_a_redactar():
    assert ruta_tras_verificar({"problemas": ["El 0,4 no está en [C1]"], "intentos": 1}) == "redactar"


def test_ruta_no_vuelve_a_redactar_mas_de_la_cuenta():
    assert ruta_tras_verificar({"problemas": ["El 0,4 no está en [C1]"], "intentos": MAX_INTENTOS}) == "aprobar"


def test_tiene_los_seis_nodos():
    nodos = set(construir_grafo(InMemorySaver()).get_graph().nodes)
    assert {"recopilar", "analizar", "redactar", "verificar", "aprobar", "publicar"} <= nodos


def test_corrige_el_borrador_y_publica(monkeypatch, tmp_path):
    monkeypatch.setattr(brief, "SALIDA", tmp_path)
    bien = borrador_bien()
    prompts = llm_falso(monkeypatch, [INVENTADO, bien])
    grafo = construir_grafo(InMemorySaver())
    pausa = grafo.invoke({"usar_copia": True}, CONFIG)
    assert pausa["__interrupt__"][0].value == {"borrador": bien, "problemas": []}
    assert pausa["intentos"] == 2 and "0,4" in prompts[1]
    final = grafo.invoke(Command(resume={"accion": "aprobar"}), CONFIG)
    assert bien in Path(final["archivo"]).read_text(encoding="utf-8")


def test_no_pasa_de_max_intentos(monkeypatch, tmp_path):
    monkeypatch.setattr(brief, "SALIDA", tmp_path)
    prompts = llm_falso(monkeypatch, [INVENTADO])
    pausa = construir_grafo(InMemorySaver()).invoke({"usar_copia": True}, CONFIG)
    assert len(prompts) == MAX_INTENTOS and pausa["__interrupt__"][0].value["problemas"]


def test_rechazado_no_se_publica(monkeypatch, tmp_path):
    monkeypatch.setattr(brief, "SALIDA", tmp_path)
    llm_falso(monkeypatch, [borrador_bien()])
    grafo = construir_grafo(InMemorySaver())
    grafo.invoke({"usar_copia": True}, CONFIG)
    final = grafo.invoke(Command(resume={"accion": "rechazar"}), CONFIG)
    assert "archivo" not in final and not list(tmp_path.iterdir())
