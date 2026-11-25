"""Router del tablero de consolidación. El semáforo lo decide el dominio."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import ahora_utc, obtener_sesion
from app.dominio.consolidacion import (
    CATALOGO_UNIDADES,
    OCUPACION_MINIMA,
    PESO_MAX_TARIMA_KG,
    VOLUMEN_TARIMA_M3,
    Unidad,
    ocupacion,
    puede_liberar,
)
from app.esquemas.consolidacion import (
    RespuestaCatalogo,
    RespuestaEvaluacion,
    RespuestaTablero,
    SemaforoSucursal,
    SolicitudEvaluacion,
    UnidadSalida,
)
from app.modelos import Tarima

router = APIRouter()

SesionDep = Annotated[Session, Depends(obtener_sesion)]


def _unidad_salida(unidad: Unidad) -> UnidadSalida:
    return UnidadSalida(
        clase=unidad.clase.value,
        posiciones=unidad.posiciones,
        minimo_90=unidad.minimo_90,
        peso_max_kg=unidad.peso_max_kg,
        volumen_max_m3=unidad.volumen_max_m3,
        costo_viaje=unidad.costo_viaje,
    )


@router.get("/catalogo", response_model=RespuestaCatalogo)
def consultar_catalogo() -> RespuestaCatalogo:
    """Flota y parámetros de tarima, con los límites corregidos de la v2."""
    return RespuestaCatalogo(
        unidades=[_unidad_salida(u) for u in CATALOGO_UNIDADES],
        volumen_tarima_m3=VOLUMEN_TARIMA_M3,
        peso_max_tarima_kg=PESO_MAX_TARIMA_KG,
        ocupacion_minima=OCUPACION_MINIMA,
        horas_antiguedad_limite=settings.horas_antiguedad_limite,
    )


@router.post("/evaluar", response_model=RespuestaEvaluacion)
def evaluar_sucursal(solicitud: SolicitudEvaluacion) -> RespuestaEvaluacion:
    """Pasa el acumulado de una sucursal por el semáforo de liberación."""
    decision = puede_liberar(
        tarimas_acumuladas=solicitud.tarimas_acumuladas,
        peso_kg=solicitud.peso_kg,
        volumen_m3=solicitud.volumen_m3,
        antiguedad_horas=solicitud.antiguedad_horas,
        horas_limite=settings.horas_antiguedad_limite,
    )
    return RespuestaEvaluacion(
        sucursal=solicitud.sucursal,
        liberar=decision.liberar,
        motivo=decision.motivo.value,
        requiere_acta=decision.requiere_acta,
        detalle=decision.detalle,
        unidad=_unidad_salida(decision.unidad) if decision.unidad else None,
        ocupacion=(
            round(ocupacion(solicitud.tarimas_acumuladas, decision.unidad), 4)
            if decision.unidad
            else None
        ),
    )


@router.get("/tablero", response_model=RespuestaTablero)
def consultar_tablero(sesion: SesionDep) -> RespuestaTablero:
    """Semáforo por sucursal con lo que hay en rack y zona flex.

    Es la vista que el jefe de embarques consulta de pie, de lejos: una fila
    por sucursal y la alerta de antigüedad visible.
    """
    tarimas = sesion.scalars(
        select(Tarima).where(Tarima.embarque_id.is_(None)).order_by(Tarima.sucursal)
    ).all()

    ahora = ahora_utc()
    por_sucursal: dict[str, list[Tarima]] = {}
    for tarima in tarimas:
        por_sucursal.setdefault(tarima.sucursal, []).append(tarima)

    filas: list[SemaforoSucursal] = []
    for sucursal, lote in sorted(por_sucursal.items()):
        antiguedad = max(t.antiguedad_horas(ahora) for t in lote)
        decision = puede_liberar(
            tarimas_acumuladas=len(lote),
            peso_kg=sum(t.peso_kg for t in lote),
            volumen_m3=sum(t.volumen_m3 for t in lote),
            antiguedad_horas=antiguedad,
            horas_limite=settings.horas_antiguedad_limite,
        )
        filas.append(
            SemaforoSucursal(
                sucursal=sucursal,
                tarimas_acumuladas=len(lote),
                antiguedad_horas=round(antiguedad, 1),
                liberar=decision.liberar,
                motivo=decision.motivo.value,
                clase_unidad=decision.unidad.clase.value if decision.unidad else None,
                ocupacion=(
                    round(ocupacion(len(lote), decision.unidad), 4)
                    if decision.unidad
                    else None
                ),
                alerta_antiguedad=antiguedad >= settings.horas_antiguedad_limite,
            )
        )

    return RespuestaTablero(
        total_sucursales=len(filas),
        liberables=sum(1 for f in filas if f.liberar),
        en_alerta_antiguedad=sum(1 for f in filas if f.alerta_antiguedad),
        filas=filas,
    )
