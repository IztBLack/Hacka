"""Pruebas de consolidación: regla del 90%, flota heterogénea y antigüedad."""

from __future__ import annotations

import pytest

from app.dominio.consolidacion import (
    CATALOGO_UNIDADES,
    HORAS_ANTIGUEDAD_LIMITE,
    PESO_MAX_TARIMA_KG,
    VOLUMEN_TARIMA_M3,
    ClaseUnidad,
    MotivoLiberacion,
    puede_liberar,
    seleccionar_unidad,
    unidad_minima_que_acomoda,
)


def _peso(tarimas: int, por_tarima: float = 700.0) -> float:
    """Peso realista: la tarima rara vez va al tope de 1,000 kg."""
    return tarimas * por_tarima


def _volumen(tarimas: int) -> float:
    return round(tarimas * VOLUMEN_TARIMA_M3, 4)


# --- Catálogo --------------------------------------------------------------


def test_la_tarima_mide_lo_que_dice_el_reto() -> None:
    """1.12 x 1.15 x 1.85 m = 2.3828 m3, hasta 1,000 kg."""
    assert pytest.approx(2.3828, abs=0.0001) == VOLUMEN_TARIMA_M3
    assert PESO_MAX_TARIMA_KG == 1000.0


@pytest.mark.parametrize(
    "clase,posiciones,minimo,peso_max",
    [
        (ClaseUnidad.TORTON, 12, 11, 12_000.0),
        (ClaseUnidad.RABON, 6, 6, 6_000.0),
        (ClaseUnidad.CAMIONETA_3_5, 3, 3, 3_000.0),
    ],
)
def test_catalogo_de_unidades(
    clase: ClaseUnidad, posiciones: int, minimo: int, peso_max: float
) -> None:
    unidad = next(u for u in CATALOGO_UNIDADES if u.clase is clase)

    assert unidad.posiciones == posiciones
    assert unidad.minimo_90 == minimo
    assert unidad.peso_max_kg == peso_max


def test_el_torton_son_28_6_metros_cubicos_no_45() -> None:
    """Con los 45 m3 de la v1 el semáforo nunca se disparaba por volumen."""
    torton = next(u for u in CATALOGO_UNIDADES if u.clase is ClaseUnidad.TORTON)

    assert torton.volumen_max_m3 == pytest.approx(28.6, abs=0.02)


def test_el_catalogo_esta_ordenado_de_la_unidad_mas_chica_a_la_mas_grande() -> None:
    """El orden es parte de la regla: se elige la más chica que cumpla."""
    posiciones = [u.posiciones for u in CATALOGO_UNIDADES]

    assert posiciones == sorted(posiciones)


# --- Selección de unidad ---------------------------------------------------


@pytest.mark.parametrize(
    "tarimas,clase_esperada",
    [
        (3, ClaseUnidad.CAMIONETA_3_5),  # 3 de 3 = 100%
        (6, ClaseUnidad.RABON),  # 6 de 6 = 100%
        (11, ClaseUnidad.TORTON),  # 11 de 12 = 91.7%
        (12, ClaseUnidad.TORTON),  # lleno
    ],
    ids=["camioneta", "rabon", "torton-al-limite", "torton-lleno"],
)
def test_se_elige_la_unidad_mas_chica_que_cumple_el_90(
    tarimas: int, clase_esperada: ClaseUnidad
) -> None:
    unidad = seleccionar_unidad(tarimas, _peso(tarimas), _volumen(tarimas))

    assert unidad is not None
    assert unidad.clase is clase_esperada


@pytest.mark.parametrize(
    "tarimas",
    [0, 1, 2, 4, 5, 7, 8, 9, 10, 13],
    ids=[str(n) for n in (0, 1, 2, 4, 5, 7, 8, 9, 10, 13)],
)
def test_sin_90_por_ciento_no_hay_unidad(tarimas: int) -> None:
    """10 tarimas no liberan tortón (83.3%) y 13 ya no caben en uno."""
    assert seleccionar_unidad(tarimas, _peso(tarimas), _volumen(tarimas)) is None


def test_once_tarimas_liberan_torton_pero_diez_no() -> None:
    once = seleccionar_unidad(11, _peso(11), _volumen(11))
    diez = seleccionar_unidad(10, _peso(10), _volumen(10))

    assert once is not None and once.clase is ClaseUnidad.TORTON
    assert diez is None


def test_el_peso_puede_impedir_la_salida_aunque_sobren_posiciones() -> None:
    """11 tarimas pesadas (12,100 kg) rebasan el tope del tortón."""
    assert seleccionar_unidad(11, 12_100.0, _volumen(11)) is None


def test_el_volumen_puede_impedir_la_salida() -> None:
    assert seleccionar_unidad(11, _peso(11), 30.0) is None


def test_unidad_minima_que_acomoda_no_exige_el_90() -> None:
    unidad = unidad_minima_que_acomoda(5, _peso(5), _volumen(5))

    assert unidad is not None
    assert unidad.clase is ClaseUnidad.RABON  # 5 de 6 posiciones = 83%


def test_nada_acomoda_mas_de_doce_tarimas() -> None:
    assert unidad_minima_que_acomoda(13, _peso(13), _volumen(13)) is None


# --- Liberación ------------------------------------------------------------


def test_once_tarimas_liberan_por_regla_del_90_sin_acta() -> None:
    decision = puede_liberar(11, _peso(11), _volumen(11), antiguedad_horas=6)

    assert decision.liberar is True
    assert decision.motivo is MotivoLiberacion.REGLA_90
    assert decision.unidad is not None and decision.unidad.clase is ClaseUnidad.TORTON
    assert decision.requiere_acta is False


def test_diez_tarimas_frescas_siguen_acumulando() -> None:
    decision = puede_liberar(10, _peso(10), _volumen(10), antiguedad_horas=10)

    assert decision.liberar is False
    assert decision.motivo is MotivoLiberacion.ACUMULANDO
    assert decision.unidad is None
    assert decision.requiere_acta is False


def test_cinco_tarimas_con_cuarenta_horas_liberan_por_excepcion() -> None:
    """La sucursal de la cola larga no espera 4 días: sale en rabón con acta."""
    decision = puede_liberar(5, _peso(5), _volumen(5), antiguedad_horas=40)

    assert decision.liberar is True
    assert decision.motivo is MotivoLiberacion.EXCEPCION_ANTIGUEDAD
    assert decision.unidad is not None and decision.unidad.clase is ClaseUnidad.RABON
    assert decision.requiere_acta is True  # visible y auditable, no silenciosa


@pytest.mark.parametrize(
    "horas,motivo_esperado",
    [
        (35.9, MotivoLiberacion.ACUMULANDO),
        (36.0, MotivoLiberacion.EXCEPCION_ANTIGUEDAD),  # el límite exacto ya libera
        (36.1, MotivoLiberacion.EXCEPCION_ANTIGUEDAD),
    ],
    ids=["antes-del-limite", "limite-exacto", "pasado-el-limite"],
)
def test_el_limite_de_36_horas_es_inclusivo(
    horas: float, motivo_esperado: MotivoLiberacion
) -> None:
    decision = puede_liberar(5, _peso(5), _volumen(5), antiguedad_horas=horas)

    assert decision.motivo is motivo_esperado
    assert HORAS_ANTIGUEDAD_LIMITE == 36.0


def test_la_regla_del_90_tiene_precedencia_sobre_la_excepcion() -> None:
    """Con 11 tarimas y 50 h se libera por el 90%, sin acta de excepción."""
    decision = puede_liberar(11, _peso(11), _volumen(11), antiguedad_horas=50)

    assert decision.motivo is MotivoLiberacion.REGLA_90
    assert decision.requiere_acta is False


def test_una_sola_tarima_con_antiguedad_sale_en_camioneta() -> None:
    decision = puede_liberar(1, _peso(1), _volumen(1), antiguedad_horas=48)

    assert decision.liberar is True
    assert decision.motivo is MotivoLiberacion.EXCEPCION_ANTIGUEDAD
    assert decision.unidad is not None
    assert decision.unidad.clase is ClaseUnidad.CAMIONETA_3_5


def test_carga_que_no_cabe_en_ninguna_unidad_no_se_libera_ni_con_antiguedad() -> None:
    """11 tarimas de 1,100 kg rebasan el tortón: hay que partir el embarque."""
    decision = puede_liberar(11, 12_100.0, _volumen(11), antiguedad_horas=72)

    assert decision.liberar is False
    assert decision.motivo is MotivoLiberacion.ACUMULANDO
    assert "partir el embarque" in decision.detalle


def test_sucursal_sin_tarimas_no_libera() -> None:
    decision = puede_liberar(0, 0.0, 0.0, antiguedad_horas=100)

    assert decision.liberar is False
    assert decision.motivo is MotivoLiberacion.ACUMULANDO


@pytest.mark.parametrize(
    "tarimas,peso,volumen,horas",
    [
        (-1, 0.0, 0.0, 0.0),
        (1, -5.0, 0.0, 0.0),
        (1, 0.0, -1.0, 0.0),
        (1, 0.0, 0.0, -2.0),
    ],
    ids=["tarimas", "peso", "volumen", "antiguedad"],
)
def test_valores_negativos_son_error(
    tarimas: int, peso: float, volumen: float, horas: float
) -> None:
    with pytest.raises(ValueError):
        puede_liberar(tarimas, peso, volumen, antiguedad_horas=horas)


def test_la_sucursal_de_la_cola_larga_no_espera_mas_de_dos_dias() -> None:
    """Simulación: 2.6 tarimas/día. Con rabón sale en 3 días naturales.

    Es la prueba de que la flota heterogénea mata la inanición del 90%.
    """
    acumuladas = 0.0
    dia = 0
    while dia < 10:
        dia += 1
        acumuladas += 2.6
        tarimas = int(acumuladas)
        decision = puede_liberar(
            tarimas, _peso(tarimas), _volumen(tarimas), antiguedad_horas=dia * 24
        )
        if decision.liberar:
            break

    assert decision.liberar is True
    assert dia <= 3
    assert decision.unidad is not None
    assert decision.unidad.clase is ClaseUnidad.RABON
