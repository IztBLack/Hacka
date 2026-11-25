"""Motor de citas de andén (lógica pura).

Diagnóstico de la propuesta v2: con 4 andenes de recibo el CEDIS está
sobrevendido en 3 citas/día. El andén 5 flex (un andén de embarque operando
como recibo de 8:00 a 13:00) cierra el déficit sin comprar nada.

    Capacidad = (4 andenes x 10 h + 1 andén x 5 h) / 1.25 h = 36 citas/día
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import time, timedelta
from math import ceil, floor
from typing import Sequence

__all__ = [
    "Franja",
    "APERTURA",
    "CIERRE",
    "CIERRE_ANDEN_FLEX",
    "ANDENES_RECIBO",
    "ANDEN_FLEX",
    "MINUTOS_MANIOBRA",
    "DURACION_MINIMA",
    "BLOQUE_MINUTOS",
    "duracion_minutos",
    "hay_traslape",
    "capacidad_dia",
    "slots_disponibles",
]

APERTURA = time(8, 0)
CIERRE = time(18, 0)
CIERRE_ANDEN_FLEX = time(13, 0)  # a la 13:00 el andén 5 vuelve a embarque
ANDENES_RECIBO: tuple[int, ...] = (1, 2, 3, 4)
ANDEN_FLEX = 5
MINUTOS_MANIOBRA = 15  # entrada, posicionamiento y retiro de la unidad
DURACION_MINIMA = 60  # ninguna descarga se agenda en menos de 1 h
BLOQUE_MINUTOS = 30  # la agenda se publica en bloques de media hora
MINUTOS_FIJOS = 12  # tiempo fijo de la maniobra documental
MINUTOS_POR_BULTO = 0.9


def _a_minutos(momento: time) -> int:
    """Minutos desde medianoche: comparar enteros es menos frágil que horas."""
    return momento.hour * 60 + momento.minute


def _a_hora(minutos: int) -> time:
    if not 0 <= minutos <= 24 * 60:
        raise ValueError(f"minuto fuera del día: {minutos}")
    if minutos == 24 * 60:
        return time(23, 59)
    return time(minutos // 60, minutos % 60)


@dataclass(frozen=True, slots=True)
class Franja:
    """Intervalo de ocupación de un andén dentro de un mismo día."""

    inicio: time
    fin: time
    anden: int | None = None

    def __post_init__(self) -> None:
        if _a_minutos(self.fin) <= _a_minutos(self.inicio):
            raise ValueError("la franja debe terminar después de iniciar")

    @classmethod
    def desde_duracion(
        cls, inicio: time, minutos: int, anden: int | None = None
    ) -> "Franja":
        """Construye la franja a partir de su duración en minutos."""
        if minutos <= 0:
            raise ValueError("la duración debe ser positiva")
        return cls(inicio=inicio, fin=_a_hora(_a_minutos(inicio) + minutos), anden=anden)

    @property
    def minuto_inicio(self) -> int:
        return _a_minutos(self.inicio)

    @property
    def minuto_fin(self) -> int:
        return _a_minutos(self.fin)

    @property
    def duracion(self) -> timedelta:
        return timedelta(minutes=self.minuto_fin - self.minuto_inicio)

    def con_maniobra(self, minutos_maniobra: int = MINUTOS_MANIOBRA) -> "Franja":
        """La misma franja extendida por el tiempo de maniobra posterior.

        El andén no queda libre en el instante en que el camión termina de
        descargar: hay que sacarlo y posicionar el siguiente.
        """
        nuevo_fin = min(self.minuto_fin + minutos_maniobra, 24 * 60)
        return replace(self, fin=_a_hora(nuevo_fin))


def duracion_minutos(n_bultos: int) -> int:
    """Duración de la cita calculada por el sistema, nunca declarada por el proveedor.

        t = max(60, ceil(12 + 0.9 x n_bultos))  redondeado al bloque de 30 min

    148 bultos -> 12 + 133.2 = 145.2 -> 146 -> 150 min.
    El proveedor solo puede pedir más tiempo, nunca menos.
    """
    if n_bultos < 0:
        raise ValueError("el número de bultos no puede ser negativo")
    estimado = ceil(MINUTOS_FIJOS + MINUTOS_POR_BULTO * n_bultos)
    minutos = max(DURACION_MINIMA, estimado)
    # Redondeo hacia arriba al bloque de 30 min para que la agenda sea publicable.
    return ceil(minutos / BLOQUE_MINUTOS) * BLOQUE_MINUTOS


def hay_traslape(nueva: Franja, existentes: Sequence[Franja]) -> bool:
    """True si `nueva` choca con alguna franja del mismo andén.

    El contacto exacto no es traslape: una cita que termina 10:00 y otra que
    inicia 10:00 pueden convivir. La maniobra se modela aparte, con
    `Franja.con_maniobra`, para no mezclar dos reglas en una sola función.
    """
    for existente in existentes:
        distinto_anden = (
            nueva.anden is not None
            and existente.anden is not None
            and nueva.anden != existente.anden
        )
        if distinto_anden:
            continue  # otro andén es otro recurso: no compiten
        if (
            nueva.minuto_inicio < existente.minuto_fin
            and existente.minuto_inicio < nueva.minuto_fin
        ):
            return True
    return False


def capacidad_dia(
    andenes_recibo: int = len(ANDENES_RECIBO),
    horas: float = 10,
    minutos_maniobra: int = MINUTOS_MANIOBRA,
    duracion_media: int = DURACION_MINIMA,
    horas_anden_flex: float = 0,
) -> int:
    """Citas que caben en un día.

    Sin andén flex: 4 x 10 h / 1.25 h = 32 citas (la demanda es 35: déficit de 3).
    Con andén flex de 5 h: (4 x 10 h + 5 h) / 1.25 h = 36 citas.
    """
    if andenes_recibo < 0 or horas < 0 or horas_anden_flex < 0:
        raise ValueError("andenes y horas no pueden ser negativos")
    if duracion_media <= 0 or minutos_maniobra < 0:
        raise ValueError("duración media o maniobra inválidas")
    minutos_disponibles = (andenes_recibo * horas + horas_anden_flex) * 60
    return floor(minutos_disponibles / (duracion_media + minutos_maniobra))


def slots_disponibles(
    duracion: int,
    ocupadas: Sequence[Franja] = (),
    andenes: Sequence[int] = ANDENES_RECIBO,
    anden_flex: int | None = ANDEN_FLEX,
    paso_minutos: int = BLOQUE_MINUTOS,
    minutos_maniobra: int = MINUTOS_MANIOBRA,
    apertura: time = APERTURA,
    cierre: time = CIERRE,
    cierre_flex: time = CIERRE_ANDEN_FLEX,
) -> list[Franja]:
    """Franjas donde cabe una cita de `duracion` minutos.

    Reglas que respeta:
      * horario de recibo 8:00-18:00;
      * un andén atiende una sola cita a la vez, más su maniobra;
      * el andén 5 flex solo recibe de 8:00 a 13:00.
    """
    if duracion <= 0:
        raise ValueError("la duración debe ser positiva")
    if paso_minutos <= 0:
        raise ValueError("el paso de la agenda debe ser positivo")

    # Cada franja ya tomada bloquea también su maniobra posterior.
    bloqueadas = [f.con_maniobra(minutos_maniobra) for f in ocupadas]
    todos: list[int] = list(andenes)
    if anden_flex is not None:
        todos.append(anden_flex)

    candidatos: list[Franja] = []
    for anden in todos:
        limite = cierre_flex if anden == anden_flex else cierre
        minuto_tope = _a_minutos(limite)
        minuto = _a_minutos(apertura)
        while minuto + duracion <= minuto_tope:
            franja = Franja.desde_duracion(_a_hora(minuto), duracion, anden=anden)
            # Se compara con la maniobra incluida: el siguiente camión tampoco
            # puede entrar pisando la salida de este.
            if not hay_traslape(franja.con_maniobra(minutos_maniobra), bloqueadas):
                candidatos.append(franja)
            minuto += paso_minutos

    candidatos.sort(key=lambda f: (f.minuto_inicio, f.anden or 0))
    return candidatos
