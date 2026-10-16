"""Deja todo listo antes de clase. Ejecútalo las veces que haga falta.

    python preparar.py

1. Comprueba Python y los paquetes de requirements.txt.
2. Con cada clave de LLM que encuentre en .env, prueba el servicio.
3. Prueba cada fuente de datos. Si alguna falla, generar.py usará su copia, así que no es grave.
"""

import importlib
import importlib.util
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def linea(bien: bool, texto: str) -> None:
    print(f"  {'bien ' if bien else 'falta'}  {texto}")


def paquetes() -> bool:
    print("Instalación")
    linea(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]} (hace falta 3.10 o más)")
    faltan = [p for p in ("langgraph", "pytest", "certifi") if importlib.util.find_spec(p) is None]
    linea(not faltan, "paquetes: " + (f"faltan {', '.join(faltan)}. pip install -r requirements.txt" if faltan
                                      else "langgraph, pytest y certifi"))
    return sys.version_info >= (3, 10) and not faltan


def llms(modelos) -> None:
    print("\nEl LLM que redacta")
    alguno = False
    for nombre, (_, variable, modelo, _) in modelos.LLMS.items():
        if not modelos.clave(variable):
            linea(False, f"{nombre}: no hay {variable} en .env")
            continue
        try:
            inicio = time.time()
            texto = modelos.llamar_llm(nombre, "Contesta solo con la palabra: listo")
            linea(True, f"{nombre} ({modelo}) contesta «{texto[:30]}» en {time.time() - inicio:.1f} s")
            alguno = True
        except Exception as e:
            linea(False, f"{nombre} ({modelo}): {e}")
    if not alguno:
        print("  Hace falta al menos una clave de LLM. Mira .env.ejemplo.")
    elif len(modelos.proveedores()) == 1:
        print("  Con una sola clave funciona. Con las dos, si una llega a su límite, generar.py sigue con la otra.")


def datos(fuentes) -> None:
    print("\nLas fuentes de datos")
    for id_, serie in fuentes.SERIES.items():
        try:
            ultima = [o for o in fuentes.observaciones(id_) if o[1] is not None][-1]
            linea(True, f"{serie['nombre']}: {ultima[1]} ({ultima[0]})")
        except Exception as e:
            linea(False, f"{serie['nombre']}: {e}")
    for id_, rss in fuentes.RSS.items():
        try:
            lista = fuentes.titulares_rss(id_)
            linea(True, f"{rss['nombre']}: {len(lista)} titulares, el último del {lista[0]['fecha']}")
        except Exception as e:
            linea(False, f"{rss['nombre']}: {e}")
    print(f"  Lo que falle saldrá de la copia del {fuentes.leer_copia().get('guardada', '?')[:10]}.")


def main() -> None:
    if not paquetes():
        sys.exit("\nArregla la instalación y vuelve a ejecutar python preparar.py")
    # modelos y fuentes importan certifi: solo se pueden importar después de comprobar que está instalado.
    modelos = importlib.import_module("modelos")
    fuentes = importlib.import_module("fuentes")
    if not (AQUI / ".env").exists():
        print("\nNo hay .env: copia .env.ejemplo como .env y pon tus claves.")
    llms(modelos)
    datos(fuentes)


if __name__ == "__main__":
    main()
