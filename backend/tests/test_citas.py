"""Pruebas del motor de citas: duración calculada, traslapes y capacidad."""

from __future__ import annotations

from datetime import time

import pytest

from app.dominio.citas import (
    ANDEN_FLEX,
    CIERRE_ANDEN_FLEX,
    Franja,
    capacidad_dia,
    duracion_minutos,
    hay_traslape,
    slots_disponibles,
)

CITAS_REQUERIDAS_DIA = 35  # demanda real del CEDIS


@pytest.mark.parametrize(
    "bultos,esperado",
    [
        (0, 60),  # el piso de 60 min manda
        (1, 60),
        (53, 60),  # 12 + 47.7 = 59.7 -> 60: justo en el piso
        (54, 90),  # 12 + 48.6 = 60.6 -> 61 -> bloque de 90
        (148, 150),  # 12 + 133.2 = 145.2 -> 146 -> bloque de 150
        (160, 180),  # 12 + 144 = 156 -> bloque de 180
        (200, 210),  # 12 + 180 = 192 -> bloque de 210
    ],
    ids=["cero", "uno", "piso-exacto", "primer-salto", "camion-de-148", "160", "200"],
)
def test_duracion_se_calcula_y_se_redondea_a_bloques_de_30(
    bultos: int, esperado: int
) -> None:
    assert duracion_minutos(bultos) == esperado


def test_duracion_siempre_cae_en_bloque_de_30_minutos() -> None:
    assert all(duracion_minutos(n) % 30 == 0 for n in range(0, 400))


def test_duracion_es_monotona() -> None:
    """Más bultos nunca pueden dar una cita más corta."""
    valores = [duracion_minutos(n) for n in range(0, 400)]
    assert all(b >= a for a, b in zip(valores, valores[1:]))


def test_bultos_negativos_son_error() -> None:
    with pytest.raises(ValueError):
        duracion_minutos(-1)


# --- Traslapes -------------------------------------------------------------


def test_contacto_exacto_en_el_limite_no_es_traslape() -> None:
    """Una cita termina 10:00 y la siguiente inicia 10:00: conviven."""
    ocupada = Franja(time(8, 0), time(10, 0), anden=1)
    nueva = Franja(time(10, 0), time(11, 30), anden=1)

    assert hay_traslape(nueva, [ocupada]) is False


def test_un_minuto_antes_del_limite_si_es_traslape() -> None:
    ocupada = Franja(time(8, 0), time(10, 0), anden=1)
    nueva = Franja(time(9, 59), time(11, 30), anden=1)

    assert hay_traslape(nueva, [ocupada]) is True


def test_contacto_exacto_por_el_otro_extremo_no_es_traslape() -> None:
    ocupada = Franja(time(10, 0), time(12, 0), anden=1)
    nueva = Franja(time(8, 0), time(10, 0), anden=1)

    assert hay_traslape(nueva, [ocupada]) is False


@pytest.mark.parametrize(
    "inicio,fin,esperado",
    [
        (time(8, 30), time(9, 30), True),  # contenida
        (time(7, 0), time(13, 0), True),  # contiene a la ocupada
        (time(8, 0), time(10, 0), True),  # idéntica
        (time(7, 0), time(8, 0), False),  # pega por la izquierda
        (time(10, 0), time(11, 0), False),  # pega por la derecha
        (time(6, 0), time(7, 0), False),  # lejos
    ],
    ids=["contenida", "contiene", "identica", "pega-izq", "pega-der", "lejos"],
)
def test_combinaciones_de_traslape_en_el_mismo_anden(
    inicio: time, fin: time, esperado: bool
) -> None:
    ocupada = Franja(time(8, 0), time(10, 0), anden=1)

    assert hay_traslape(Franja(inicio, fin, anden=1), [ocupada]) is esperado


def test_otro_anden_no_es_traslape() -> None:
    """Cuatro andenes son cuatro recursos: la misma hora no choca."""
    ocupada = Franja(time(8, 0), time(10, 0), anden=1)
    nueva = Franja(time(8, 0), time(10, 0), anden=2)

    assert hay_traslape(nueva, [ocupada]) is False


def test_franja_sin_anden_choca_con_cualquiera() -> None:
    """Sin andén asignado la franja representa a todo el recibo."""
    ocupada = Franja(time(8, 0), time(10, 0), anden=3)
    nueva = Franja(time(9, 0), time(11, 0))

    assert hay_traslape(nueva, [ocupada]) is True


def test_franja_invertida_no_se_construye() -> None:
    with pytest.raises(ValueError):
        Franja(time(10, 0), time(8, 0))


def test_maniobra_extiende_la_ocupacion_del_anden() -> None:
    franja = Franja(time(8, 0), time(10, 30), anden=1)

    assert franja.con_maniobra().fin == time(10, 45)


# --- Capacidad -------------------------------------------------------------


def test_sin_anden_flex_el_recibo_esta_sobrevendido() -> None:
    """4 andenes x 10 h / 1.25 h = 32 citas contra 35 requeridas."""
    capacidad = capacidad_dia()

    assert capacidad == 32
    assert capacidad < CITAS_REQUERIDAS_DIA
    assert CITAS_REQUERIDAS_DIA - capacidad == 3  # el déficit del diagnóstico


def test_con_anden_flex_de_cinco_horas_la_capacidad_alcanza() -> None:
    """(4 x 10 h + 5 h) / 1.25 h = 36 citas >= 35 requeridas."""
    capacidad = capacidad_dia(horas_anden_flex=5)

    assert capacidad == 36
    assert capacidad >= CITAS_REQUERIDAS_DIA


def test_con_duracion_media_realista_de_78_minutos_la_capacidad_cae() -> None:
    """Con 1.3 h de media (no el mínimo de 1 h) el flex ya no basta."""
    capacidad = capacidad_dia(duracion_media=78, horas_anden_flex=5)

    assert capacidad == 29
    assert capacidad < CITAS_REQUERIDAS_DIA


def test_sin_maniobra_la_capacidad_queda_inflada_como_en_la_v1() -> None:
    """Ignorar la maniobra es exactamente el error de lectura de la v1."""
    assert capacidad_dia(minutos_maniobra=0) == 40


def test_parametros_negativos_son_error() -> None:
    with pytest.raises(ValueError):
        capacidad_dia(andenes_recibo=-1)


# --- Slots -----------------------------------------------------------------


def test_todos_los_slots_caben_en_el_horario_de_recibo() -> None:
    slots = slots_disponibles(150)

    assert slots
    assert all(slot.inicio >= time(8, 0) for slot in slots)
    assert all(slot.fin <= time(18, 0) for slot in slots)


def test_el_anden_flex_solo_recibe_hasta_la_una() -> None:
    slots_flex = [s for s in slots_disponibles(150) if s.anden == ANDEN_FLEX]

    assert slots_flex
    assert all(slot.fin <= CIERRE_ANDEN_FLEX for slot in slots_flex)
    assert max(slot.inicio for slot in slots_flex) == time(10, 30)


def test_cita_larga_no_cabe_en_el_anden_flex() -> None:
    """Una descarga de 5.5 h no termina antes de la 13:00."""
    slots = slots_disponibles(330)

    assert all(slot.anden != ANDEN_FLEX for slot in slots)
    assert any(slot.anden == 1 for slot in slots)


def test_una_cita_ocupada_bloquea_su_anden_incluida_la_maniobra() -> None:
    ocupada = Franja(time(8, 0), time(10, 30), anden=1)

    slots = slots_disponibles(150, ocupadas=[ocupada])
    en_anden_1 = [s for s in slots if s.anden == 1]

    # 10:30 + 15 min de maniobra = 10:45, así que el siguiente bloque es 11:00.
    assert min(s.inicio for s in en_anden_1) == time(11, 0)
    # Los demás andenes siguen libres desde la apertura.
    assert any(s.anden == 2 and s.inicio == time(8, 0) for s in slots)


def test_ningun_slot_propuesto_choca_con_lo_ya_agendado() -> None:
    ocupadas = [
        Franja(time(8, 0), time(10, 30), anden=1),
        Franja(time(9, 0), time(11, 0), anden=2),
        Franja(time(8, 0), time(9, 0), anden=ANDEN_FLEX),
    ]

    for slot in slots_disponibles(60, ocupadas=ocupadas):
        assert not hay_traslape(slot, ocupadas)


def test_duracion_invalida_en_slots_es_error() -> None:
    with pytest.raises(ValueError):
        slots_disponibles(0)
