"""Sincronización idempotente de escaneos (lógica pura).

El handheld trabaja sin red y acumula escaneos. Cuando vuelve el enlace manda
un lote. Si la conexión se corta a media respuesta, reenvía el mismo lote.
Esa segunda vez NO debe duplicar nada.

Hay dos candados, uno encima del otro:
  1. id_evento: cada escaneo trae un identificador único generado en el
     handheld. Si ya lo vimos, devolvemos el veredicto guardado y no
     evaluamos de nuevo.
  2. id_bulto: lo que ya hace `evaluar_bulto`. Si el mismo QR llega con otro
     id_evento, el resultado es DUPLICADO y no suma.

Nada de este módulo conoce FastAPI ni SQLAlchemy: el adaptador carga el estado
y los eventos vistos, llama a `procesar_lote` y persiste lo que cambió.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from app.dominio.recepcion import (
    EstadoRecepcion,
    ResultadoEscaneo,
    evaluar_bulto,
)

__all__ = [
    "EventoEscaneo",
    "ResultadoEvento",
    "ResumenLote",
    "procesar_lote",
]


@dataclass(frozen=True, slots=True)
class EventoEscaneo:
    """Un escaneo tal como lo guardó el handheld."""

    id_evento: str
    cadena_qr: str
    escaneado_en: str  # AAAA-MM-DDTHH:MM:SSZ, en UTC


@dataclass(frozen=True, slots=True)
class ResultadoEvento:
    """Veredicto de un evento. `repetido` es True si ya se había procesado."""

    id_evento: str
    resultado: ResultadoEscaneo
    repetido: bool


@dataclass(slots=True)
class ResumenLote:
    """Qué pasó con el lote completo."""

    resultados: list[ResultadoEvento] = field(default_factory=list)

    @property
    def nuevos(self) -> int:
        return sum(1 for r in self.resultados if not r.repetido)

    @property
    def repetidos(self) -> int:
        return sum(1 for r in self.resultados if r.repetido)


def procesar_lote(
    eventos: Iterable[EventoEscaneo],
    llave: bytes,
    estado: EstadoRecepcion,
    eventos_vistos: dict[str, ResultadoEscaneo],
) -> ResumenLote:
    """Procesa un lote de escaneos de forma idempotente.

    `eventos_vistos` es el historial persistido (id_evento -> veredicto). Esta
    función lo actualiza con los eventos nuevos, así el adaptador solo tiene
    que guardarlo después.

    Los eventos se procesan en el orden recibido: el handheld los manda en el
    orden en que los escaneó, y de ese orden depende cuál bulto es el que
    pasa el tope en un excedente.
    """
    resumen = ResumenLote()
    for evento in eventos:
        previo = eventos_vistos.get(evento.id_evento)
        if previo is not None:
            resumen.resultados.append(
                ResultadoEvento(evento.id_evento, previo, repetido=True)
            )
            continue

        resultado = evaluar_bulto(evento.cadena_qr, llave, estado)
        eventos_vistos[evento.id_evento] = resultado
        resumen.resultados.append(
            ResultadoEvento(evento.id_evento, resultado, repetido=False)
        )
    return resumen
