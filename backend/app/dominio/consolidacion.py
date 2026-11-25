"""Consolidación y liberación de embarques (lógica pura).

La regla del reto es "no sale la unidad hasta cubrir al menos 90%". Aplicada a
una sola clase de unidad, esa regla mata a las sucursales chicas: con 2.6
tarimas/día tardarían 4.2 días en llenar un tortón.

La v2 la cumple cambiando de unidad en lugar de hacer esperar a la sucursal, y
cuando ni así se llega al 90% libera por antigüedad con un acta visible y
auditable (nunca en silencio).

Límites reales corregidos respecto a la v1:
  * tarima 1.12 x 1.15 x 1.85 m = 2.3828 m3, hasta 1,000 kg;
  * tortón 12 posiciones, 12,000 kg (12 x 1,000) y 28.6 m3 (12 x 2.3828).
La v1 usaba 14,000 kg y 45 m3, con lo que el semáforo del 90% no se disparaba
nunca por peso ni por volumen y la regla quedaba desactivada de facto.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import ceil

__all__ = [
    "ClaseUnidad",
    "MotivoLiberacion",
    "Unidad",
    "DecisionLiberacion",
    "CATALOGO_UNIDADES",
    "LARGO_TARIMA_M",
    "ANCHO_TARIMA_M",
    "ALTO_TARIMA_M",
    "VOLUMEN_TARIMA_M3",
    "PESO_MAX_TARIMA_KG",
    "OCUPACION_MINIMA",
    "HORAS_ANTIGUEDAD_LIMITE",
    "seleccionar_unidad",
    "unidad_minima_que_acomoda",
    "puede_liberar",
    "ocupacion",
]

# Dimensiones de la tarima estándar del reto.
LARGO_TARIMA_M = 1.12
ANCHO_TARIMA_M = 1.15
ALTO_TARIMA_M = 1.85
VOLUMEN_TARIMA_M3 = round(LARGO_TARIMA_M * ANCHO_TARIMA_M * ALTO_TARIMA_M, 4)  # 2.3828
PESO_MAX_TARIMA_KG = 1000.0

OCUPACION_MINIMA = 0.90
HORAS_ANTIGUEDAD_LIMITE = 36.0  # tope duro de permanencia en rack


class ClaseUnidad(StrEnum):
    """Flota heterogénea: la unidad se elige, no se espera a llenar el tortón."""

    CAMIONETA_3_5 = "CAMIONETA_3_5"
    RABON = "RABON"
    TORTON = "TORTON"


class MotivoLiberacion(StrEnum):
    """Por qué se liberó (o no) un embarque."""

    REGLA_90 = "REGLA_90"
    EXCEPCION_ANTIGUEDAD = "EXCEPCION_ANTIGUEDAD"
    ACUMULANDO = "ACUMULANDO"


@dataclass(frozen=True, slots=True)
class Unidad:
    """Clase de unidad de transporte con sus tres límites reales."""

    clase: ClaseUnidad
    posiciones: int
    peso_max_kg: float
    volumen_max_m3: float
    costo_viaje: float

    @property
    def minimo_90(self) -> int:
        """Tarimas necesarias para cumplir el 90% de ocupación.

        tortón ceil(10.8) = 11 · rabón ceil(5.4) = 6 · camioneta ceil(2.7) = 3.
        """
        return ceil(OCUPACION_MINIMA * self.posiciones)

    def acomoda(self, tarimas: int, peso_kg: float, volumen_m3: float) -> bool:
        """True si la carga cabe en la unidad por posiciones, peso y volumen."""
        return (
            0 < tarimas <= self.posiciones
            and peso_kg <= self.peso_max_kg
            and volumen_m3 <= self.volumen_max_m3
        )

    def cumple_90(self, tarimas: int, peso_kg: float, volumen_m3: float) -> bool:
        """True si además de caber alcanza el 90% por posiciones de tarima.

        El límite que manda es posiciones (11 de 12); peso y volumen son
        restricciones secundarias que pueden impedir la salida, no provocarla.
        """
        return self.acomoda(tarimas, peso_kg, volumen_m3) and tarimas >= self.minimo_90


def _volumen_maximo(posiciones: int) -> float:
    """Volumen de caja seca necesario para `posiciones` tarimas, en m3.

    Se redondea hacia arriba al centímetro cúbico para que la unidad nunca
    quede por debajo de su propia capacidad nominal:
    12 posiciones -> 28.6 m3, 6 -> 14.3 m3, 3 -> 7.15 m3.
    """
    return ceil(posiciones * VOLUMEN_TARIMA_M3 * 100) / 100


# Ordenado de la unidad más chica a la más grande: el orden es parte de la regla.
CATALOGO_UNIDADES: tuple[Unidad, ...] = (
    Unidad(
        clase=ClaseUnidad.CAMIONETA_3_5,
        posiciones=3,
        peso_max_kg=3 * PESO_MAX_TARIMA_KG,
        volumen_max_m3=_volumen_maximo(3),  # 7.15 m3
        costo_viaje=1250.0,
    ),
    Unidad(
        clase=ClaseUnidad.RABON,
        posiciones=6,
        peso_max_kg=6 * PESO_MAX_TARIMA_KG,
        volumen_max_m3=_volumen_maximo(6),  # 14.3 m3
        costo_viaje=2000.0,
    ),
    Unidad(
        clase=ClaseUnidad.TORTON,
        posiciones=12,
        peso_max_kg=12 * PESO_MAX_TARIMA_KG,  # 12,000 kg
        volumen_max_m3=_volumen_maximo(12),  # 28.6 m3
        costo_viaje=2800.0,
    ),
)


@dataclass(frozen=True, slots=True)
class DecisionLiberacion:
    """Resultado del semáforo de consolidación de una sucursal."""

    liberar: bool
    motivo: MotivoLiberacion
    unidad: Unidad | None
    requiere_acta: bool
    detalle: str


def ocupacion(tarimas: int, unidad: Unidad) -> float:
    """Fracción de posiciones ocupadas (0.0 a 1.0+)."""
    return tarimas / unidad.posiciones


def seleccionar_unidad(
    tarimas_acumuladas: int, peso_kg: float, volumen_m3: float
) -> Unidad | None:
    """La unidad MÁS CHICA que cumple el 90%, o None si ninguna cumple.

    3 tarimas -> camioneta · 6 -> rabón · 11 o 12 -> tortón.
    5 o 10 tarimas -> None: no alcanzan el 90% de ninguna clase y el embarque
    sigue acumulando (salvo excepción por antigüedad).
    """
    if tarimas_acumuladas <= 0:
        return None
    for unidad in CATALOGO_UNIDADES:  # ya viene de la más chica a la más grande
        if unidad.cumple_90(tarimas_acumuladas, peso_kg, volumen_m3):
            return unidad
    return None


def unidad_minima_que_acomoda(
    tarimas_acumuladas: int, peso_kg: float, volumen_m3: float
) -> Unidad | None:
    """La unidad más chica donde cabe la carga, sin exigir el 90%.

    Es la que se usa en la excepción por antigüedad: si hay que sacar 5 tarimas
    con 40 h de espera, viajan en rabón al 83% y el acta lo deja asentado.
    """
    if tarimas_acumuladas <= 0:
        return None
    for unidad in CATALOGO_UNIDADES:
        if unidad.acomoda(tarimas_acumuladas, peso_kg, volumen_m3):
            return unidad
    return None


def puede_liberar(
    tarimas_acumuladas: int,
    peso_kg: float,
    volumen_m3: float,
    antiguedad_horas: float,
    horas_limite: float = HORAS_ANTIGUEDAD_LIMITE,
) -> DecisionLiberacion:
    """Semáforo de liberación, en el orden de precedencia de la propuesta.

    1. Ocupación >= 90% en la unidad más chica que acomode -> liberar.
    2. Antigüedad de la tarima más vieja >= 36 h -> liberar con acta de excepción.
    3. En cualquier otro caso -> seguir acumulando.
    """
    if tarimas_acumuladas < 0 or peso_kg < 0 or volumen_m3 < 0:
        raise ValueError("acumulados negativos: revisar el inventario de origen")
    if antiguedad_horas < 0:
        raise ValueError("la antigüedad no puede ser negativa")

    if tarimas_acumuladas == 0:
        return DecisionLiberacion(
            liberar=False,
            motivo=MotivoLiberacion.ACUMULANDO,
            unidad=None,
            requiere_acta=False,
            detalle="sin tarimas acumuladas para esta sucursal",
        )

    unidad = seleccionar_unidad(tarimas_acumuladas, peso_kg, volumen_m3)
    if unidad is not None:
        porcentaje = ocupacion(tarimas_acumuladas, unidad) * 100
        return DecisionLiberacion(
            liberar=True,
            motivo=MotivoLiberacion.REGLA_90,
            unidad=unidad,
            requiere_acta=False,
            detalle=(
                f"{tarimas_acumuladas} tarimas en {unidad.clase} "
                f"({porcentaje:.1f}% de {unidad.posiciones} posiciones)"
            ),
        )

    if antiguedad_horas >= horas_limite:
        unidad_excepcion = unidad_minima_que_acomoda(
            tarimas_acumuladas, peso_kg, volumen_m3
        )
        if unidad_excepcion is None:
            # La carga no cabe en ninguna clase: no es excepción, es partir el
            # embarque. Se mantiene acumulando y se avisa en el detalle.
            return DecisionLiberacion(
                liberar=False,
                motivo=MotivoLiberacion.ACUMULANDO,
                unidad=None,
                requiere_acta=False,
                detalle=(
                    f"{tarimas_acumuladas} tarimas / {peso_kg:.0f} kg / "
                    f"{volumen_m3:.2f} m3 exceden cualquier unidad: "
                    "requiere partir el embarque"
                ),
            )
        porcentaje = ocupacion(tarimas_acumuladas, unidad_excepcion) * 100
        return DecisionLiberacion(
            liberar=True,
            motivo=MotivoLiberacion.EXCEPCION_ANTIGUEDAD,
            unidad=unidad_excepcion,
            requiere_acta=True,  # la excepción se reporta a gerencia
            detalle=(
                f"tarima más vieja con {antiguedad_horas:.0f} h "
                f"(límite {horas_limite:.0f} h): sale en {unidad_excepcion.clase} "
                f"al {porcentaje:.1f}% con acta de excepción"
            ),
        )

    faltan = CATALOGO_UNIDADES[0].minimo_90 - tarimas_acumuladas
    detalle = (
        f"{tarimas_acumuladas} tarimas, {antiguedad_horas:.0f} h de antigüedad: "
        "ninguna clase alcanza el 90%"
    )
    if faltan > 0:
        detalle += f"; faltan {faltan} tarimas para la unidad más chica"
    return DecisionLiberacion(
        liberar=False,
        motivo=MotivoLiberacion.ACUMULANDO,
        unidad=None,
        requiere_acta=False,
        detalle=detalle,
    )
