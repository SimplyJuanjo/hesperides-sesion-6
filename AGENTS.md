# AGENTS.md

## Qué es esto

Un grafo de LangGraph que escribe un brief de mercados de la zona euro con datos públicos: Python recopila y calcula, un LLM redacta, Python verifica las cifras y las citas y una persona aprueba antes de publicar. Es para aprender: quien lo usa tiene que entender cada línea.

## Reglas

- Usa solo LangGraph y la biblioteca estándar de Python.
- Deja como están `tests/`, `datos/`, `modelos.py`, `generar.py` y las funciones de `brief.py` que ya vienen escritas.
- Las cuentas las hace Python en un nodo, nunca el LLM. Al modelo solo se le llama con `modelos.redactar`.
- Una fuente nueva es una entrada nueva en `SERIES` o `RSS` de `fuentes.py`.
- Las claves viven en `.env`. No las escribas en el código ni las muestres por pantalla.

## Cómo trabajar

- Un peldaño cada vez: implementa solo la función que te pidan y ejecuta su test, por ejemplo `pytest tests/test_1_analizar.py`.
- Antes de escribir código, di en dos frases qué vas a hacer y qué claves del estado lee y escribe cada nodo, y espera.
- Después, explica cada línea en una frase, para alguien que no ha usado LangGraph.
