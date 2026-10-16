from brief import verificar

CIFRAS = [
    {"id": "C1", "nombre": "Euríbor a 12 meses", "unidad": "%", "decimales": 3, "fuente": "BCE", "url": "https://x",
     "fecha": "2026-09", "valor": 3.247, "fecha_anterior": "2026-08", "anterior": 2.9536667, "cambio": 0.29},
    {"id": "C2", "nombre": "IBEX 35", "unidad": "puntos", "decimales": 2, "fuente": "Yahoo Finance", "url": "https://y",
     "fecha": "2026-10-15", "valor": 19336.3, "fecha_anterior": "2026-10-13", "anterior": 19177.7, "cambio": 0.83},
]
TITULARES = [{"id": "T1", "fuente": "Banco de España, noticias", "fecha": "2026-10-01", "url": "https://z",
              "titulo": "El euríbor se sitúa en el 3,247% en septiembre, 1,075 puntos más que hace un año"}]


def test_un_borrador_bien_citado_no_tiene_problemas():
    borrador = "## Tipos al alza\n\n- El Euríbor a 12 meses sube 0,29 puntos, hasta el 3,247 % [C1].\n- Para vigilar: el BCE."
    assert verificar(borrador, CIFRAS, TITULARES) == []


def test_dos_citas_en_la_misma_linea():
    assert verificar("El Euríbor, en el 3,247 % [C1], sube 1,075 puntos en un año [T1].", CIFRAS, TITULARES) == []


def test_una_cita_con_espacios_tambien_es_cita():
    assert verificar("El Euríbor a 12 meses está en el 3,247 % [ C1 ].", CIFRAS, TITULARES) == []


def test_una_cita_que_no_existe():
    assert any("[C9]" in p for p in verificar("El Euríbor sube [C9].", CIFRAS, TITULARES))


def test_un_numero_inventado():
    problemas = verificar("El Euríbor a 12 meses sube al 3,3 % [C1].", CIFRAS, TITULARES)
    assert len(problemas) == 1 and "3,3" in problemas[0]


def test_una_cuenta_del_modelo_es_un_numero_inventado():
    problemas = verificar("El Euríbor sube 0,293 puntos [C1].", CIFRAS, TITULARES)
    assert len(problemas) == 1 and "0,293" in problemas[0]


def test_un_numero_de_otra_cifra_no_vale():
    assert len(verificar("El IBEX 35 cierra en 19.336,30 puntos [C1].", CIFRAS, TITULARES)) >= 1


def test_cada_linea_se_mira_por_separado():
    borrador = "El Euríbor está en el 3,247 % [C1].\nEl IBEX 35 sube un 3,247 %."
    assert len(verificar(borrador, CIFRAS, TITULARES)) == 1


def test_coma_y_punto_decimal_son_el_mismo_numero():
    assert verificar("El Euríbor a 12 meses está en el 3.247 % [C1].", CIFRAS, TITULARES) == []


def test_los_miles_se_pueden_escribir_con_punto_o_con_espacio():
    assert verificar("El IBEX 35 cierra en 19.336,30 puntos [C2].", CIFRAS, TITULARES) == []
    assert verificar("El IBEX 35 cierra en 19 336,30 puntos [C2].", CIFRAS, TITULARES) == []


def test_el_numero_de_una_lista_no_cuenta():
    assert verificar("1. El Euríbor a 12 meses está en el 3,247 % [C1].", CIFRAS, TITULARES) == []
    assert verificar("- 1️⃣ El Euríbor a 12 meses está en el 3,247 % [C1].", CIFRAS, TITULARES) == []
    assert verificar("- 10️⃣ El Euríbor a 12 meses está en el 3,247 % [C1].", CIFRAS, TITULARES) == []


def test_numeros_sin_ninguna_cita():
    assert verificar("El Euríbor sube al 3,247 %.", CIFRAS, TITULARES) != []


def test_lineas_sin_numeros_no_necesitan_cita():
    assert verificar("## Para vigilar\n\nLa próxima reunión del BCE.", CIFRAS, TITULARES) == []
