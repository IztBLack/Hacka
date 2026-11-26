"""Desglose por bulto de una cita (lógica pura).

El proveedor declara cuántos bultos trae; el sistema reparte las piezas
pendientes de cada línea de la OC entre esos bultos y asigna la sucursal
destino. Cada bulto lleva UN solo SKU (regla de pureza del reto).

En producción el desglose lo captura el proveedor en el portal (paso 2).
En el prototipo se genera aquí, de forma determinista, para que la cita
recién creada tenga etiquetas reales que imprimir y escanear.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["LineaPendiente", "BultoPlaneado", "planear_desglose"]


@dataclass(frozen=True, slots=True)
class LineaPendiente:
    """Piezas de un SKU que aún no tienen bulto asignado."""

    sku: str
    descripcion: str
    piezas: int


@dataclass(frozen=True, slots=True)
class BultoPlaneado:
    secuencia: int
    sku: str
    descripcion: str
    sucursal: str
    piezas: int


def _repartir(total: int, pesos: list[int]) -> list[int]:
    """Reparte `total` en proporción a `pesos` (mayor residuo), mínimo 1 cada uno.

    Nunca asigna a un elemento más que su peso: una línea de 5 piezas no
    puede ir en 6 bultos.
    """
    suma = sum(pesos)
    base = [max(1, min(p, total * p // suma)) for p in pesos]
    restante = total - sum(base)
    orden = sorted(
        range(len(pesos)), key=lambda i: (total * pesos[i]) % suma, reverse=True
    )
    while restante > 0:
        avanzo = False
        for i in orden:
            if restante == 0:
                break
            if base[i] < pesos[i]:
                base[i] += 1
                restante -= 1
                avanzo = True
        if not avanzo:
            break
    return base


def planear_desglose(
    lineas: list[LineaPendiente], n_bultos: int, sucursales: list[str]
) -> list[BultoPlaneado]:
    """Plan de bultos para una cita.

    * Cada línea con piezas pendientes recibe al menos un bulto.
    * Los bultos se reparten en proporción a las piezas de cada línea.
    * Las piezas de una línea se reparten parejo entre sus bultos: la suma
      cuadra exacto con lo pendiente, así el acta de faltante no se descuadra.
    * La sucursal destino rota entre `sucursales`.
    """
    activas = [linea for linea in lineas if linea.piezas > 0]
    if not activas or n_bultos <= 0 or not sucursales:
        return []

    total_piezas = sum(linea.piezas for linea in activas)
    objetivo = max(len(activas), min(n_bultos, total_piezas))
    bultos_por_linea = _repartir(objetivo, [linea.piezas for linea in activas])

    plan: list[BultoPlaneado] = []
    for linea, k in zip(activas, bultos_por_linea, strict=True):
        cociente, residuo = divmod(linea.piezas, k)
        for j in range(k):
            secuencia = len(plan) + 1
            plan.append(
                BultoPlaneado(
                    secuencia=secuencia,
                    sku=linea.sku,
                    descripcion=linea.descripcion,
                    sucursal=sucursales[(secuencia - 1) % len(sucursales)],
                    piezas=cociente + (1 if j < residuo else 0),
                )
            )
    return plan
