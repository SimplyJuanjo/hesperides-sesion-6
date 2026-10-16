from brief import prompt_brief, texto_cifra, texto_titular

CIFRAS = [
    {"id": "C1", "nombre": "Euríbor a 12 meses", "unidad": "%", "decimales": 3, "fuente": "BCE", "url": "https://x",
     "fecha": "2026-09", "valor": 3.247, "fecha_anterior": "2026-08", "anterior": 2.9536667, "cambio": 0.29},
    {"id": "C2", "nombre": "IBEX 35", "unidad": "puntos", "decimales": 2, "fuente": "Yahoo Finance", "url": "https://y",
     "fecha": "2026-10-15", "valor": 19336.3, "fecha_anterior": "2026-10-13", "anterior": 19177.7, "cambio": 0.83},
]
TITULARES = [{"id": "T1", "fuente": "Banco de España, noticias", "fecha": "2026-10-01", "url": "https://z",
              "titulo": "El euríbor se sitúa en el 3,247% en septiembre, 1,075 puntos más que hace un año"}]
LECTOR = "Tesorería de una pyme con un préstamo a tipo variable ligado al Euríbor."


def test_lleva_el_lector_detras_de_las_instrucciones():
    p = prompt_brief(CIFRAS, TITULARES, LECTOR)
    assert p.index(LECTOR) > 0 and p[:p.index(LECTOR)].strip()


def test_cada_cifra_y_cada_titular_con_su_texto():
    p = prompt_brief(CIFRAS, TITULARES, LECTOR)
    assert texto_cifra(CIFRAS[0]) in p and texto_cifra(CIFRAS[1]) in p and texto_titular(TITULARES[0]) in p


def test_en_orden_lector_cifras_titulares():
    p = prompt_brief(CIFRAS, TITULARES, LECTOR)
    assert p.index(LECTOR) < p.index(texto_cifra(CIFRAS[0])) < p.index(texto_cifra(CIFRAS[1])) \
        < p.index(texto_titular(TITULARES[0]))


def test_sin_problemas_no_cambia():
    assert prompt_brief(CIFRAS, TITULARES, LECTOR) == prompt_brief(CIFRAS, TITULARES, LECTOR, [])


def test_el_borrador_anterior_y_sus_problemas_van_al_final():
    anterior = "- La pendiente de la curva es de 0,4 puntos [C1].\n- El Euríbor sube [C9]."
    problemas = ["0,4: no sale de [C1]. Línea: «- La pendiente de la curva es de 0,4 puntos [C1].»",
                 "La cita [C9] no existe."]
    p = prompt_brief(CIFRAS, TITULARES, LECTOR, problemas, anterior)
    assert p.index(texto_titular(TITULARES[0])) < p.index(anterior) < p.rindex(problemas[0]) < p.rindex(problemas[1])


def test_sin_problemas_no_va_el_borrador_anterior():
    assert "Un borrador que ya estaba bien." not in prompt_brief(CIFRAS, TITULARES, LECTOR, [],
                                                                 "Un borrador que ya estaba bien.")
