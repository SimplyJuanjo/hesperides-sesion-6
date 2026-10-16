"""El LLM que redacta el brief. Ya está escrito.

Las claves salen de las variables de entorno o del archivo `.env` de esta carpeta: copia `.env.ejemplo` como
`.env` y rellénalo. `.env` no se sube a git.

Si el proveedor elegido llega a su límite o no contesta, `redactar` sigue con el siguiente que tenga clave, sin
esperar. Con una sola clave, espera lo que pida el proveedor, hasta un minuto.
"""

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

import certifi

AQUI = Path(__file__).resolve().parent
SSL = ssl.create_default_context(cafile=certifi.where())

# Proveedores gratuitos con la misma API que OpenAI: (dirección, variable de la clave, modelo, ajustes).
# gpt-oss razona siempre; con "low" gasta menos. En Gemini 3, Google pide no bajar la temperatura de 1.
LLMS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b",
             {"temperature": 0, "reasoning_effort": "low", "include_reasoning": False}),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "gemini-3.5-flash-lite", {}),
}
# Incluye lo que el modelo razona antes de contestar. Groq descuenta entrada + MAX_TOKENS de sus 8.000 tokens por minuto.
MAX_TOKENS = 1500


class NoContesta(RuntimeError):
    """El proveedor ha llegado a su límite (429, 413), está caído (5xx) o no responde a tiempo."""

    def __init__(self, mensaje: str, espera: float = 0):
        super().__init__(mensaje)
        self.espera = espera


def leer_env() -> None:
    ruta = AQUI / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            nombre, valor = linea.split("=", 1)
            if valor.strip():
                os.environ.setdefault(nombre.strip(), valor.strip().strip('"'))


leer_env()


def clave(variable: str) -> str | None:
    return os.environ.get(variable) or None


def proveedores() -> list[str]:
    """Los proveedores con clave: primero el de LLM_PROVEEDOR, si está, y después los demás en el orden de LLMS."""
    con_clave = [nombre for nombre, (_, variable, _, _) in LLMS.items() if clave(variable)]
    elegido = os.environ.get("LLM_PROVEEDOR")
    return sorted(con_clave, key=lambda nombre: nombre != elegido)


def modelo_de(proveedor: str) -> str:
    return os.environ.get("LLM_MODELO") if proveedor == proveedores()[0] and os.environ.get("LLM_MODELO") \
        else LLMS[proveedor][2]


def llamar_llm(proveedor: str, prompt: str) -> str:
    url, variable, _, ajustes = LLMS[proveedor]
    modelo = modelo_de(proveedor)
    cuerpo = {"model": modelo, "messages": [{"role": "user", "content": prompt}], "max_tokens": MAX_TOKENS, **ajustes}
    eleccion = enviar(f"{url}/chat/completions", cuerpo, {"Authorization": f"Bearer {clave(variable)}"})["choices"][0]
    texto = (eleccion["message"].get("content") or "").strip()
    if not texto and eleccion.get("finish_reason") == "length":
        raise RuntimeError(f"{modelo} gastó los {MAX_TOKENS} tokens razonando y no llegó a contestar. "
                           "Sube MAX_TOKENS en modelos.py.")
    return texto


def redactar(prompt: str) -> str:
    """Manda el prompt al primer proveedor con clave y devuelve su respuesta. Si no contesta, prueba el siguiente."""
    lista = proveedores()
    if not lista:
        raise RuntimeError("No hay clave para ningún LLM. Mira .env.ejemplo y ejecuta python preparar.py")
    for i, proveedor in enumerate(lista):
        for _ in range(3):
            try:
                return llamar_llm(proveedor, prompt)
            except NoContesta as e:
                if i < len(lista) - 1:
                    print(f"  {proveedor} no contesta ({e}). Sigo con {lista[i + 1]}.")
                    break
                # Una espera de más de un minuto es el cupo del día, no el del minuto: no merece la pena esperar.
                if not 0 < e.espera <= 60:
                    raise
                print(f"  {proveedor} pide esperar {e.espera:.0f} s: límite de peticiones por minuto.")
                time.sleep(e.espera)
    raise RuntimeError(f"{lista[-1]} sigue sin contestar después de esperar tres veces.")


# ---------- HTTP con la biblioteca estándar ----------

def enviar(url: str, cuerpo: dict, cabeceras: dict) -> dict:
    """POST con JSON. Los límites y las caídas salen como NoContesta; los demás errores, como RuntimeError."""
    servidor = url.split("/")[2]
    peticion = urllib.request.Request(url, data=json.dumps(cuerpo).encode("utf-8"), method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "hesperides-sesion-6", **cabeceras})
    try:
        with urllib.request.urlopen(peticion, timeout=120, context=SSL) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", errors="replace")[:300]
        if e.code in (413, 429) or e.code >= 500:
            try:
                espera = float(e.headers.get("retry-after") or 10)
            except ValueError:
                espera = 10
            raise NoContesta(f"{servidor} respondió {e.code}", espera if e.code == 429 else 0) from None
        raise RuntimeError(f"{servidor} respondió {e.code}: {detalle}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise NoContesta(f"{servidor} no responde: {e}") from None
