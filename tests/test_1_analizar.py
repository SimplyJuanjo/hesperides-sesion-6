import copy

from brief import analizar

SERIES = {
    "euribor": {"nombre": "Euríbor a 12 meses", "unidad": "%", "decimales": 3, "fuente": "BCE",
                "url": "https://data.ecb.europa.eu/euribor",
                "obs": [["2026-07", 2.855087], ["2026-08", 2.9536667], ["2026-09", 3.247]]},
    "ibex": {"nombre": "IBEX 35", "unidad": "puntos", "decimales": 2, "fuente": "Yahoo Finance",
             "url": "https://finance.yahoo.com/quote/%5EIBEX/",
             "obs": [["2026-10-13", 19177.7], ["2026-10-14", None], ["2026-10-15", 19336.3]]},
}


def test_una_cifra_por_serie_con_ids_seguidos():
    assert [c["id"] for c in analizar(SERIES)] == ["C1", "C2"]


def test_la_ultima_y_la_penultima_observacion():
    c = analizar(SERIES)[0]
    assert (c["fecha"], c["valor"], c["fecha_anterior"], c["anterior"]) == ("2026-09", 3.247, "2026-08", 2.9536667)


def test_un_tipo_cambia_en_puntos():
    assert analizar(SERIES)[0]["cambio"] == 0.29


def test_un_indice_cambia_en_porcentaje():
    assert analizar(SERIES)[1]["cambio"] == 0.83


def test_los_dias_sin_dato_no_cuentan():
    c = analizar(SERIES)[1]
    assert (c["fecha_anterior"], c["anterior"]) == ("2026-10-13", 19177.7)


def test_copia_lo_que_hace_falta_para_citar():
    c = analizar(SERIES)[1]
    claves = ("nombre", "unidad", "decimales", "fuente", "url")
    assert {k: c[k] for k in claves} == {k: SERIES["ibex"][k] for k in claves}


def test_una_serie_sin_dos_datos_no_da_cifra():
    nueva = {"nombre": "Nueva", "unidad": "%", "decimales": 2, "fuente": "X", "url": "https://x",
             "obs": [["2026-10-15", 1.0], ["2026-10-16", None]]}
    cifras = analizar({"nueva": nueva, **SERIES})
    assert [(c["id"], c["nombre"]) for c in cifras] == [("C1", "Euríbor a 12 meses"), ("C2", "IBEX 35")]


def test_no_toca_las_series():
    antes = copy.deepcopy(SERIES)
    analizar(SERIES)
    assert SERIES == antes
