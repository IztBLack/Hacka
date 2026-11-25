"""Máquina de estados del bulto (lógica pura).

Sin esta máquina no hay trazabilidad auditable: la clave única
(id_bulto, estado) garantiza que ningún bulto retroceda ni se duplique.

    ETIQUETADO -> EN_TRANSITO -> ESCANEADO_ANDEN -> RECIBIDO -> UBICADO
                                                 -> RECHAZADO      |
                                                                   v
    RECIBIDO_SUCURSAL <- EMBARCADO <- CARGADO <- ASIGNADO_EMBARQUE <-+

Además del camino del diagrama se permite RECIBIDO -> ASIGNADO_EMBARQUE:
es el cross-dock, el bulto va del andén de recibo al de salida sin tocar rack.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Iterable

__all__ = [
    "EstadoBulto",
    "TransicionInvalida",
    "TRANSICIONES",
    "transicion_valida",
    "aplicar_transicion",
    "es_terminal",
    "ruta_valida",
    "siguientes_estados",
]


class EstadoBulto(StrEnum):
    """Estados posibles de un bulto en su ciclo de vida completo."""

    ETIQUETADO = "ETIQUETADO"
    EN_TRANSITO = "EN_TRANSITO"
    ESCANEADO_ANDEN = "ESCANEADO_ANDEN"
    RECIBIDO = "RECIBIDO"
    RECHAZADO = "RECHAZADO"
    UBICADO = "UBICADO"
    ASIGNADO_EMBARQUE = "ASIGNADO_EMBARQUE"
    CARGADO = "CARGADO"
    EMBARCADO = "EMBARCADO"
    RECIBIDO_SUCURSAL = "RECIBIDO_SUCURSAL"


# Único lugar donde vive la regla: ninguna otra capa inventa transiciones.
TRANSICIONES: dict[EstadoBulto, frozenset[EstadoBulto]] = {
    EstadoBulto.ETIQUETADO: frozenset({EstadoBulto.EN_TRANSITO}),
    EstadoBulto.EN_TRANSITO: frozenset({EstadoBulto.ESCANEADO_ANDEN}),
    EstadoBulto.ESCANEADO_ANDEN: frozenset({EstadoBulto.RECIBIDO, EstadoBulto.RECHAZADO}),
    # UBICADO = acomodo en rack; ASIGNADO_EMBARQUE = cross-dock directo.
    EstadoBulto.RECIBIDO: frozenset({EstadoBulto.UBICADO, EstadoBulto.ASIGNADO_EMBARQUE}),
    EstadoBulto.UBICADO: frozenset({EstadoBulto.ASIGNADO_EMBARQUE}),
    EstadoBulto.ASIGNADO_EMBARQUE: frozenset({EstadoBulto.CARGADO}),
    EstadoBulto.CARGADO: frozenset({EstadoBulto.EMBARCADO}),
    EstadoBulto.EMBARCADO: frozenset({EstadoBulto.RECIBIDO_SUCURSAL}),
    # Estados terminales: de aquí no se sale.
    EstadoBulto.RECHAZADO: frozenset(),
    EstadoBulto.RECIBIDO_SUCURSAL: frozenset(),
}


class TransicionInvalida(Exception):
    """Se intentó un salto de estado no permitido por la máquina."""

    def __init__(self, desde: EstadoBulto, hacia: EstadoBulto) -> None:
        super().__init__(f"transición ilegal: {desde} -> {hacia}")
        self.desde = desde
        self.hacia = hacia


def siguientes_estados(desde: EstadoBulto) -> frozenset[EstadoBulto]:
    """Estados alcanzables en un paso desde `desde`."""
    return TRANSICIONES[EstadoBulto(desde)]


def transicion_valida(desde: EstadoBulto, hacia: EstadoBulto) -> bool:
    """True solo si la transición está declarada en TRANSICIONES.

    Rechaza saltos (ETIQUETADO -> EMBARCADO), retrocesos (UBICADO -> RECIBIDO)
    y la repetición del mismo estado, que sería un doble registro.
    """
    try:
        origen = EstadoBulto(desde)
        destino = EstadoBulto(hacia)
    except ValueError:
        return False
    return destino in TRANSICIONES[origen]


def aplicar_transicion(desde: EstadoBulto, hacia: EstadoBulto) -> EstadoBulto:
    """Devuelve el nuevo estado o lanza `TransicionInvalida`."""
    if not transicion_valida(desde, hacia):
        raise TransicionInvalida(EstadoBulto(desde), EstadoBulto(hacia))
    return EstadoBulto(hacia)


def es_terminal(estado: EstadoBulto) -> bool:
    """True si el bulto ya no puede cambiar de estado."""
    return not TRANSICIONES[EstadoBulto(estado)]


def ruta_valida(secuencia: Iterable[EstadoBulto]) -> bool:
    """Valida una traza completa de estados.

    Se usa al reconstruir la bitácora de un bulto desde los eventos que el
    handheld sincroniza en desorden tras una caída de red.
    """
    estados = [EstadoBulto(e) for e in secuencia]
    if not estados:
        return False
    return all(
        transicion_valida(anterior, siguiente)
        for anterior, siguiente in zip(estados, estados[1:])
    )
