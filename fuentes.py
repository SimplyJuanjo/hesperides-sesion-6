"""De dónde salen los datos del brief. Ya está escrito.

    python fuentes.py            descarga todo y dice qué ha llegado
    python fuentes.py --guardar  además lo guarda en datos/copia.json

Todas las fuentes son públicas y sin clave: el portal de datos del BCE, la API de gráficos de Yahoo Finance
(no es oficial y puede cambiar) y los RSS del BCE y del Banco de España. Si una falla, `recopilar` usa lo que
haya de ella en la copia.

Para añadir una fuente, añade una entrada a SERIES o a RSS. Si no es del BCE, de Yahoo ni un RSS, escribe
una función como `serie_yahoo` que devuelva las observaciones de la más antigua a la más reciente.
"""

import argparse
import csv
import io
import json
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

import certifi

AQUI = Path(__file__).resolve().parent
COPIA = AQUI / "datos" / "copia.json"
# A algunos Windows les falta el certificado raíz del BCE; certifi trae la lista completa.
SSL = ssl.create_default_context(cafile=certifi.where())
BCE = "https://data-api.ecb.europa.eu/service/data/"

# Cada serie: su nombre para el lector, la unidad ("%" para tipos y tasas), con cuántos decimales se escribe,
# quién la publica y cómo se pide: "bce" es la clave de la serie en el portal del BCE; "yahoo", el símbolo.
SERIES = {
    "deposito": {"nombre": "Tipo de la facilidad de depósito del BCE (fecha de cada cambio)", "unidad": "%",
                 "decimales": 2, "fuente": "BCE", "bce": "FM/B.U2.EUR.4F.KR.DFR.LEV"},
    "estr": {"nombre": "€STR, el tipo a 1 día entre bancos de la zona euro", "unidad": "%", "decimales": 3,
             "fuente": "BCE", "bce": "EST/B.EU000A2X2A25.WT"},
    "euribor": {"nombre": "Euríbor a 12 meses (media del mes)", "unidad": "%", "decimales": 3, "fuente": "BCE",
                "bce": "FM/M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA"},
    "bono2": {"nombre": "Bono AAA de la zona euro a 2 años", "unidad": "%", "decimales": 2, "fuente": "BCE",
              "bce": "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y"},
    "bono10": {"nombre": "Bono AAA de la zona euro a 10 años", "unidad": "%", "decimales": 2, "fuente": "BCE",
               "bce": "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y"},
    "bono10_es": {"nombre": "Bono español a 10 años (media del mes)", "unidad": "%", "decimales": 2,
                  "fuente": "BCE", "bce": "IRS/M.ES.L.L40.CI.0000.EUR.N.Z"},
    "ipca": {"nombre": "Inflación de la zona euro (IPCA, tasa anual)", "unidad": "%", "decimales": 1,
             "fuente": "BCE", "bce": "HICP/M.U2.N.000000.4D0.ANR"},
    "ipca_es": {"nombre": "Inflación de España (IPCA, tasa anual)", "unidad": "%", "decimales": 1,
                "fuente": "BCE", "bce": "HICP/M.ES.N.000000.4D0.ANR"},
    "eurusd": {"nombre": "Dólares por euro (cambio de referencia del BCE)", "unidad": "dólares", "decimales": 4,
               "fuente": "BCE", "bce": "EXR/D.USD.EUR.SP00.A"},
    "ibex": {"nombre": "IBEX 35 (último precio)", "unidad": "puntos", "decimales": 2, "fuente": "Yahoo Finance",
             "yahoo": "^IBEX"},
    "stoxx": {"nombre": "Euro Stoxx 50 (último precio)", "unidad": "puntos", "decimales": 2,
              "fuente": "Yahoo Finance", "yahoo": "^STOXX50E"},
}

RSS = {
    "bce": {"nombre": "BCE, prensa y discursos", "url": "https://www.ecb.europa.eu/rss/press.html"},
    "bde": {"nombre": "Banco de España, noticias", "url": "https://www.bde.es/wbe/es/inicio/rss/rss-noticias/"},
}
TITULARES_POR_RSS = 4


def descargar(url: str) -> bytes:
    peticion = urllib.request.Request(url, headers={"User-Agent": "hesperides-sesion-6"})
    with urllib.request.urlopen(peticion, timeout=20, context=SSL) as r:
        return r.read()


def serie_bce(clave: str, n: int = 25) -> list[list]:
    """Las últimas n observaciones de una serie del BCE: [[fecha, valor], ...], de la más antigua a la más reciente."""
    texto = descargar(f"{BCE}{clave}?lastNObservations={n}&format=csvdata").decode("utf-8")
    return [[fila["TIME_PERIOD"], float(fila["OBS_VALUE"]) if fila["OBS_VALUE"] else None]
            for fila in csv.DictReader(io.StringIO(texto))]


def serie_yahoo(simbolo: str) -> list[list]:
    """Los cierres diarios del último mes. Un día sin cierre sale con valor None."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(simbolo)}?range=1mo&interval=1d"
    datos = json.loads(descargar(url))["chart"]["result"][0]
    zona = timezone(timedelta(seconds=datos["meta"]["gmtoffset"]))
    cierres = datos["indicators"]["quote"][0]["close"]
    return [[datetime.fromtimestamp(t, zona).date().isoformat(), None if c is None else round(c, 4)]
            for t, c in zip(datos["timestamp"], cierres)]


def url_de(serie: dict) -> str:
    """La página donde una persona puede comprobar la serie."""
    if "bce" in serie:
        conjunto, clave = serie["bce"].split("/")
        return f"https://data.ecb.europa.eu/data/datasets/{conjunto}/{conjunto}.{clave}"
    return f"https://finance.yahoo.com/quote/{quote(serie['yahoo'])}/"


def observaciones(id_serie: str) -> list[list]:
    serie = SERIES[id_serie]
    return serie_bce(serie["bce"]) if "bce" in serie else serie_yahoo(serie["yahoo"])


def titulares_rss(id_rss: str) -> list[dict]:
    """Los titulares más recientes de un RSS: {"fuente", "titulo", "fecha", "url"}."""
    canal = ET.fromstring(descargar(RSS[id_rss]["url"]))
    titulares = []
    for item in canal.iter("item"):
        fecha = item.findtext("pubDate")
        titulares.append({
            "fuente": RSS[id_rss]["nombre"],
            "titulo": " ".join((item.findtext("title") or "").split()),
            "fecha": parsedate_to_datetime(fecha).date().isoformat() if fecha else "",
            "url": (item.findtext("link") or "").strip(),
        })
    return sorted(titulares, key=lambda t: t["fecha"], reverse=True)[:TITULARES_POR_RSS]


def leer_copia() -> dict:
    return json.loads(COPIA.read_text(encoding="utf-8")) if COPIA.exists() else {"series": {}, "titulares": {}}


def recopilar(usar_copia: bool = False) -> dict:
    """Las series y los titulares de todas las fuentes, en vivo o de la copia.

    Devuelve {"series": {id: serie}, "titulares": [...], "avisos": [...]}. Cada serie lleva lo de SERIES más
    "url" y "obs"; cada titular lleva su id, "T1", "T2"... Los avisos dicen qué salió de la copia y por qué.
    """
    copia = leer_copia()
    guardada = copia.get("guardada", "")[:10]
    avisos: list[str] = []

    def de_la_copia(seccion: str, id_: str, nombre: str, error: Exception | None):
        if id_ not in copia[seccion]:
            avisos.append(f"{nombre}: {'no responde y ' if error else ''}no está en la copia; queda fuera.")
            return None
        if error is not None:
            avisos.append(f"{nombre}: no responde ({type(error).__name__}); uso la copia del {guardada}.")
        return copia[seccion][id_]

    series = {}
    for id_, serie in SERIES.items():
        obs = None
        if not usar_copia:
            try:
                obs = observaciones(id_)
            except Exception as e:
                obs = de_la_copia("series", id_, serie["nombre"], e)
        else:
            obs = de_la_copia("series", id_, serie["nombre"], None)
        if obs:
            series[id_] = {**{k: v for k, v in serie.items() if k not in ("bce", "yahoo")}, "url": url_de(serie),
                           "obs": obs}

    titulares = []
    for id_, rss in RSS.items():
        lista = None
        if not usar_copia:
            try:
                lista = titulares_rss(id_)
            except Exception as e:
                lista = de_la_copia("titulares", id_, rss["nombre"], e)
        else:
            lista = de_la_copia("titulares", id_, rss["nombre"], None)
        titulares += lista or []
    if usar_copia:
        avisos.append(f"Todo sale de la copia del {guardada}.")
    for n, t in enumerate(titulares, 1):
        t["id"] = f"T{n}"
    return {"series": series, "titulares": titulares, "avisos": avisos}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--guardar", action="store_true", help="guarda lo descargado en datos/copia.json")
    args = p.parse_args()
    copia = {"guardada": datetime.now(timezone.utc).isoformat(timespec="seconds"), "series": {}, "titulares": {}}
    for id_, serie in SERIES.items():
        try:
            obs = observaciones(id_)
            copia["series"][id_] = obs
            ultima = [o for o in obs if o[1] is not None][-1]
            print(f"  bien   {serie['nombre']}: {ultima[1]} ({ultima[0]})")
        except Exception as e:
            print(f"  falla  {serie['nombre']}: {e}")
    for id_, rss in RSS.items():
        try:
            lista = titulares_rss(id_)
            copia["titulares"][id_] = lista
            print(f"  bien   {rss['nombre']}: {len(lista)} titulares, el último del {lista[0]['fecha']}")
        except Exception as e:
            print(f"  falla  {rss['nombre']}: {e}")
    if args.guardar:
        anterior = leer_copia()
        for seccion in ("series", "titulares"):
            copia[seccion] = {**anterior.get(seccion, {}), **copia[seccion]}
        COPIA.parent.mkdir(exist_ok=True)
        COPIA.write_text(json.dumps(copia, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Guardado en {COPIA.relative_to(AQUI)}")


if __name__ == "__main__":
    main()
