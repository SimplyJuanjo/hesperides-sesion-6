# Extras: más allá del brief

Opcional: nada de esto hace falta para la clase. Son ideas para mejorar vuestra newsletter y otras piezas de LangGraph que no usa el brief. Los tres scripts necesitan los cinco peldaños de `brief.py` en verde y se lanzan desde la raíz del repositorio. Probados el 21 de octubre de 2026 con LangGraph 1.2.16.

## Tres ejemplos que funcionan

- **`python extras/quant.py`**: un nodo `quant` entre `analizar` y `redactar` con la volatilidad realizada del IBEX y del Euro Stoxx (20 sesiones, anualizada) y la caída del IBEX desde su máximo del mes. Llegan al modelo como cifras C12, C13 y C14, y `verificar` las protege como a las demás. Es el patrón de la pendiente: lo quant va en un nodo de Python.
- **`python extras/web.py`**: un nodo `buscar_web` que trae noticias con [Tavily](https://docs.tavily.com/documentation/api-reference/endpoint/search), un buscador hecho para LLM. Entran como titulares T9, T10… La clave es gratis en <https://app.tavily.com> y va en `.env` como `TAVILY_API_KEY`. El nodo lleva `retry_policy`: si la red falla, LangGraph lo reintenta solo. Cambia `BUSQUEDA` por lo que lea tu lector.
- **`python extras/aprobar_luego.py`**: parar hoy y aprobar mañana. Usa `SqliteSaver` en vez de `InMemorySaver`, así que el estado queda en `brief.sqlite`, se puede aprobar desde otra terminal con `--seguir HILO`, y `--historia HILO` enseña cada checkpoint guardado. Antes: `pip install -r extras/requirements.txt`.

Los tres admiten `--copia` y `--dibujar`, como `generar.py`.

## Otras piezas de LangGraph

- Varios nodos en paralelo con `Send`: una sección del brief por nodo, o una búsqueda por fuente, y un nodo que las junta. [Graph API](https://docs.langchain.com/oss/python/langgraph/use-graph-api)
- `cache_policy` en un nodo, para no repetir una descarga, y `timeout`, para no esperar a una fuente colgada. [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- Subgrafos: el bucle redactar → verificar como un grafo dentro del grafo. [Subgrafos](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
- Streaming: ver el borrador mientras se escribe, o mensajes propios desde un nodo. [Streaming](https://docs.langchain.com/oss/python/langgraph/streaming)
- Viaje en el tiempo: volver a un checkpoint, cambiar el estado y seguir desde ahí. [Time travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel)
- Ejecución duradera: si el proceso se cae a mitad, sigue donde iba. [Durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution)
- Memoria a largo plazo: que el brief recuerde qué le gustó al lector la semana pasada. [Memoria](https://docs.langchain.com/oss/python/langgraph/add-memory)
- La API funcional, con `@entrypoint` y `@task`, el mismo flujo sin dibujar el grafo. [Functional API](https://docs.langchain.com/oss/python/langgraph/functional-api)
- Studio: el grafo en el navegador, con el estado de cada paso. [Studio](https://docs.langchain.com/oss/python/langgraph/studio) y [servidor local](https://docs.langchain.com/oss/python/langgraph/local-server)
- Flujos y agentes, los patrones de *Building effective agents* escritos en LangGraph. [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- MCP: usar herramientas de otros servidores desde un nodo. [MCP](https://docs.langchain.com/oss/python/langchain/mcp)

## Ideas para vuestra newsletter

- Mandarla: un nodo después de `publicar` que la envíe por correo (`smtplib`), Telegram (su API de bots, con `urllib`) o un webhook de Slack. Las claves, en `.env`.
- Sacarla en HTML, con una tabla de cifras y un gráfico hecho con Python.
- Un revisor con otro modelo, después de `verificar`: que lea cada línea con lo que cita y marque lo que no dice lo mismo, como una fecha mal leída. No sustituye a la persona: le deja avisos en la pausa.
- Más historia: sube `n` en `serie_bce` y `range` en `serie_yahoo` para ventanas de un año, z-scores o correlaciones.
- Programarla cada lunes a las 7:00, con el Programador de tareas, cron o GitHub Actions. Con `aprobar_luego.py`, la persona aprueba cuando la lea.
- El calendario del BCE como fuente, para que «qué vigilar» diga cuándo es la próxima reunión.
- Un agente solo donde no sabéis los pasos, por ejemplo uno que investigue un titular con búsquedas web. El resto sigue siendo grafo.
