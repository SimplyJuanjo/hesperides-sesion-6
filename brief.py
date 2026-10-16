"""Un brief de mercados de la zona euro escrito por un grafo de LangGraph, que no se publica sin que lo apruebe
una persona.

    START → recopilar → analizar → redactar → verificar ─┬─→ aprobar ─┬─→ publicar → END
                                       ↑                 │            └─→ END (rechazado)
                                       └─── problemas ───┘

Los cinco peldaños de la clase están sin hacer. Los tests de `tests/` dicen qué tiene que ser verdad para
cada uno. Lo de abajo del todo ya está escrito.

Convención: cada nodo recibe el estado entero y devuelve un diccionario solo con las claves que cambia.
LangGraph mezcla ese diccionario con el estado antes de pasar al siguiente nodo.
"""

import re
from datetime import date
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

import fuentes
import modelos

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "salida"

# Para quién se escribe. Cámbialo por tu lector.
LECTOR = """Tesorería de una pyme española con un préstamo a tipo variable ligado al Euríbor y algo de caja \
en depósitos. Lo lee el lunes por la mañana, con prisa: quiere saber qué ha pasado con los tipos, la \
inflación y la bolsa, y qué vigilar esta semana."""

# Borradores como mucho: el primero y dos correcciones.
MAX_INTENTOS = 3


class Estado(TypedDict, total=False):
    usar_copia: bool        # entrada: True para no salir a internet a por los datos
    series: dict            # recopilar: {id: {"nombre", "unidad", "decimales", "fuente", "url", "obs"}}
    titulares: list[dict]   # recopilar: [{"id": "T1", "fuente", "titulo", "fecha", "url"}, ...]
    avisos: list[str]       # recopilar: qué salió de la copia y por qué
    cifras: list[dict]      # analizar: una por serie, con su id "C1", "C2"...
    borrador: str           # redactar
    intentos: int           # redactar: cuántos borradores van
    problemas: list[str]    # verificar: vacía si todo cuadra
    aprobado: bool          # aprobar
    archivo: str            # publicar: dónde quedó el brief


# ---------- Peldaño 1: analizar, con Python y sin LLM ----------

def analizar(series: dict[str, dict]) -> list[dict]:
    """Una cifra por serie, en el orden de `series`, con ids "C1", "C2"... seguidos.

    Cada serie trae "obs": [[fecha, valor], ...] de la más antigua a la más reciente, y un valor puede ser
    None (un día sin dato). La cifra copia de la serie "nombre", "unidad", "decimales", "fuente" y "url", y
    añade:
    - "fecha" y "valor": la última observación con valor;
    - "fecha_anterior" y "anterior": la penúltima con valor;
    - "cambio": si la unidad es "%", la diferencia en puntos (valor - anterior); si no, la variación en
      porcentaje, 100 * (valor / anterior - 1). Redondeado a 2 decimales.
    Una serie con menos de dos observaciones con valor no da cifra.
    """
    raise NotImplementedError


# ---------- Peldaño 2: el prompt ----------

def prompt_brief(cifras: list[dict], titulares: list[dict], lector: str, problemas: list[str] | None = None,
                 anterior: str = "") -> str:
    """El texto que se manda al modelo: instrucciones, el lector, las cifras y los titulares, en ese orden.

    Cada cifra va en su línea con `texto_cifra(c)` y cada titular con `texto_titular(t)`; los dos empiezan
    por su id entre corchetes, [C1] o [T1]. Las instrucciones piden escribir en español para ese lector, usar
    solo esas cifras y titulares, poner detrás de cada dato su id entre corchetes y copiar los números tal
    cual, sin hacer cuentas.

    Si hay `problemas` (los que `verificar` encontró), al final van el borrador `anterior` y los problemas,
    uno por línea, y se pide corregir solo eso.
    """
    raise NotImplementedError


# ---------- Peldaño 3: verificar con Python ----------

def verificar(borrador: str, cifras: list[dict], titulares: list[dict]) -> list[str]:
    """Lista de problemas del borrador: frases que nombran el id o los números que fallan y la línea donde
    están. Vacía si todo cuadra.

    Se mira línea a línea, porque cada línea es un punto o un párrafo:
    - Cada id entre corchetes, [C3] o [T2], tiene que existir.
    - Cada número de la línea tiene que estar en el texto de alguna de las cifras o titulares que cita esa
      misma línea (`texto_cifra`, `texto_titular`). Se comparan con `numeros_de`, así que 3,25 y 3.25 son el
      mismo número. Los que no estén van juntos en un solo problema por línea.
    - Una línea con números y sin ningún id también es un problema.
    """
    raise NotImplementedError


# ---------- Peldaño 4: una persona aprueba ----------

def aprobar(estado: Estado) -> dict:
    """Para el grafo y espera a una persona: llama a `interrupt` con {"borrador", "problemas"} del estado.

    Lo que devuelve `interrupt` es la respuesta de la persona: {"accion": "aprobar"},
    {"accion": "editar", "texto": "..."} o {"accion": "rechazar"}. El nodo devuelve {"aprobado": True} al
    aprobar, {"aprobado": True, "borrador": texto} al editar y {"aprobado": False} al rechazar.
    """
    raise NotImplementedError


# ---------- Peldaño 5: el grafo ----------

def ruta_tras_verificar(estado: Estado) -> str:
    """Adónde va el grafo después de verificar: "aprobar" si no hay problemas o si ya van MAX_INTENTOS
    borradores; si no, "redactar" otra vez."""
    raise NotImplementedError


def construir_grafo(checkpointer=None):
    """El grafo compilado, con el `checkpointer` que se le pase: sin él, `interrupt` no puede parar el grafo.

    Seis nodos con estos nombres: "recopilar" (nodo_recopilar), "analizar" (nodo_analizar), "redactar"
    (nodo_redactar), "verificar" (nodo_verificar), "aprobar" (aprobar) y "publicar" (nodo_publicar).
    Aristas: START → recopilar → analizar → redactar → verificar. Después de verificar decide
    `ruta_tras_verificar`; después de aprobar, `ruta_tras_aprobar`. De publicar, a END.
    """
    raise NotImplementedError


# ---------- Ya escritos: los demás nodos ----------

def nodo_recopilar(estado: Estado) -> dict:
    datos = fuentes.recopilar(usar_copia=estado.get("usar_copia", False))
    return {"series": datos["series"], "titulares": datos["titulares"], "avisos": datos["avisos"]}


def nodo_analizar(estado: Estado) -> dict:
    return {"cifras": analizar(estado["series"])}


def nodo_redactar(estado: Estado) -> dict:
    prompt = prompt_brief(estado["cifras"], estado["titulares"], LECTOR, estado.get("problemas"),
                          estado.get("borrador", ""))
    return {"borrador": modelos.redactar(prompt), "intentos": estado.get("intentos", 0) + 1}


def nodo_verificar(estado: Estado) -> dict:
    return {"problemas": verificar(estado["borrador"], estado["cifras"], estado["titulares"])}


def ruta_tras_aprobar(estado: Estado) -> str:
    return "publicar" if estado.get("aprobado") else END


def nodo_publicar(estado: Estado) -> dict:
    """Escribe el brief en salida/brief-AAAA-MM-DD.md, con las fuentes de cada cita al final."""
    hoy = date.today().isoformat()
    citados = ids_de(estado["borrador"])
    lineas = [f"# Brief de mercados de la zona euro, {fecha_larga(hoy)}", "", estado["borrador"].strip(), "",
              "## Fuentes", ""]
    lineas += [f"- [{c['id']}] {c['nombre']} ({c['fuente']}), {fecha_larga(c['fecha'])}: {c['url']}"
               for c in estado["cifras"] if c["id"] in citados]
    lineas += [f"- [{t['id']}] {t['fuente']}, {fecha_larga(t['fecha'])}: {t['titulo']}. {t['url']}"
               for t in estado["titulares"] if t["id"] in citados]
    if estado.get("problemas"):
        lineas += ["", "Publicado con problemas sin resolver de la verificación:", ""]
        lineas += [f"- {p}" for p in estado["problemas"]]
    lineas += ["", f"Cifras calculadas con Python, texto redactado por un LLM y aprobado por una persona el "
                   f"{fecha_larga(hoy)}."]
    SALIDA.mkdir(exist_ok=True)
    archivo = SALIDA / f"brief-{hoy}.md"
    archivo.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return {"archivo": str(archivo)}


# ---------- Ya escritas: ayudas ----------

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def fecha_larga(fecha: str) -> str:
    """«2026-10-15» → «15 de octubre de 2026»; «2026-09» → «septiembre de 2026»."""
    partes = fecha.split("-")
    if len(partes) == 3:
        return f"{int(partes[2])} de {MESES[int(partes[1]) - 1]} de {partes[0]}"
    if len(partes) == 2:
        return f"{MESES[int(partes[1]) - 1]} de {partes[0]}"
    return fecha


def numero(valor: float, decimales: int) -> str:
    """Como se escribe en español: 19336.3 con 2 decimales → «19.336,30»."""
    return f"{valor:,.{decimales}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def texto_cifra(c: dict) -> str:
    """«[C3] Euríbor a 12 meses (media del mes), BCE: 3,247 % en septiembre de 2026. Anterior: 2,954 % en
    agosto de 2026. Cambio: +0,29 puntos.»"""
    unidad = " %" if c["unidad"] == "%" else f" {c['unidad']}"
    cuando = "en" if len(c["fecha"]) == 7 else "el"
    cambio = f"{'+' if c['cambio'] >= 0 else '-'}{numero(abs(c['cambio']), 2)}"
    cambio += " puntos" if c["unidad"] == "%" else " %"
    return (f"[{c['id']}] {c['nombre']}, {c['fuente']}: {numero(c['valor'], c['decimales'])}{unidad} {cuando} "
            f"{fecha_larga(c['fecha'])}. Anterior: {numero(c['anterior'], c['decimales'])}{unidad} {cuando} "
            f"{fecha_larga(c['fecha_anterior'])}. Cambio: {cambio}.")


def texto_titular(t: dict) -> str:
    """«[T1] Banco de España, noticias, 1 de octubre de 2026: El euríbor se sitúa en el 3,247% en septiembre»."""
    return f"[{t['id']}] {t['fuente']}, {fecha_larga(t['fecha'])}: {t['titulo']}"


def ids_de(texto: str) -> list[str]:
    """Los ids citados, sin repetir y en orden: «sube [C3][T1] y baja [C3]» → ["C3", "T1"]."""
    return list(dict.fromkeys(re.findall(r"\[([CT]\d+)\]", texto)))


def numeros_de(texto: str) -> list[str]:
    """Los números del texto escritos de una sola forma, para poder compararlos.

    Con un solo separador, es el decimal: «3,25» y «3.25» salen «3,25». Con los dos, el último es el decimal
    y el otro separa los miles: «19.336,30», «19,336.30» y «19 336,30» salen «19336,3». Sin ceros que sobren:
    «2,50» sale «2,5». No cuentan los ids de las citas, [C1] o [T2], ni el número de una lista numerada
    al principio de la línea («1. »), ni los números en emoji («1️⃣»).
    """
    texto = re.sub(r"\[[CT]\d+\]", " ", texto)
    texto = re.sub(r"\d\ufe0f?\u20e3", " ", texto)
    texto = re.sub(r"^\s*(?:[-*]\s*)?\d+[.)]\s", " ", texto, flags=re.MULTILINE)
    texto = re.sub(r"(?<=\d)[ \u00a0\u202f](?=\d{3}(?!\d))", "", texto)
    numeros = []
    for n in re.findall(r"\d+(?:[.,]\d+)*", texto):
        separadores = [s for s in n if s in ".,"]
        if len(set(separadores)) == 2:
            decimal = separadores[-1]
            entero, _, parte = n.rpartition(decimal)
            entero = entero.replace("." if decimal == "," else ",", "")
        elif len(separadores) == 1:
            entero, _, parte = n.replace(",", ".").partition(".")
        else:
            entero, parte = n.replace(".", "").replace(",", ""), ""
        entero, parte = entero.lstrip("0") or "0", parte.rstrip("0")
        numeros.append(f"{entero},{parte}" if parte else entero)
    return numeros
