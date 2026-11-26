"""Router de agendamiento. Solo orquesta: las reglas viven en app.dominio.citas."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import obtener_sesion
from app.dominio.citas import (
    ANDEN_FLEX,
    Franja,
    capacidad_dia,
    duracion_minutos,
    hay_traslape,
    slots_disponibles,
)
from app.esquemas.citas import (
    BultoEtiqueta,
    RespuestaCapacidad,
    RespuestaCita,
    RespuestaDuracion,
    RespuestaEtiquetasCita,
    RespuestaSlots,
    ResumenCita,
    SlotLibre,
    SolicitudCita,
    SolicitudDuracion,
    SolicitudSlots,
)
from app.modelos import Cita, LineaOrdenCompra, OrdenCompra, Proveedor
from app.modelos.catalogos import Sucursal
from app.servicios.desglose import asegurar_desglose, bultos_de_cita
from app.servicios.repositorios import (
    RepositorioCitas,
    RepositorioOrdenes,
    restriccion_violada,
)
from app.servicios.sat import ValidadorSAT, obtener_validador

router = APIRouter()

# Reintentos si dos reservas simultáneas calculan el mismo folio del día.
INTENTOS_FOLIO = 3

SesionDep = Annotated[Session, Depends(obtener_sesion)]
ValidadorDep = Annotated[ValidadorSAT, Depends(obtener_validador)]

CITAS_REQUERIDAS_DIA = 35


@router.post("/duracion", response_model=RespuestaDuracion)
def calcular_duracion(solicitud: SolicitudDuracion) -> RespuestaDuracion:
    """Duración que el sistema asigna a la descarga.

    El proveedor puede pedir más tiempo, nunca menos: por eso la calcula el
    backend y no el portal.
    """
    return RespuestaDuracion(
        n_bultos=solicitud.n_bultos,
        duracion_minutos=duracion_minutos(solicitud.n_bultos),
    )


@router.get("/capacidad", response_model=RespuestaCapacidad)
def consultar_capacidad() -> RespuestaCapacidad:
    """Diagnóstico de capacidad de andén: 32 citas contra 35 requeridas."""
    sin_flex = capacidad_dia(
        andenes_recibo=settings.andenes_recibo, horas=settings.horas_operacion
    )
    con_flex = capacidad_dia(
        andenes_recibo=settings.andenes_recibo,
        horas=settings.horas_operacion,
        horas_anden_flex=settings.horas_anden_flex,
    )
    return RespuestaCapacidad(
        andenes_recibo=settings.andenes_recibo,
        horas_operacion=settings.horas_operacion,
        capacidad_sin_anden_flex=sin_flex,
        capacidad_con_anden_flex=con_flex,
        citas_requeridas=CITAS_REQUERIDAS_DIA,
        deficit_sin_flex=max(0, CITAS_REQUERIDAS_DIA - sin_flex),
        alcanza_con_flex=con_flex >= CITAS_REQUERIDAS_DIA,
    )


@router.post("/slots", response_model=RespuestaSlots)
def consultar_slots(solicitud: SolicitudSlots, sesion: SesionDep) -> RespuestaSlots:
    """Disponibilidad real del día, descontando lo agendado y la maniobra."""
    duracion = duracion_minutos(solicitud.n_bultos)
    ocupadas = RepositorioCitas(sesion).franjas_ocupadas(solicitud.fecha)
    libres = slots_disponibles(
        duracion=duracion,
        ocupadas=ocupadas,
        anden_flex=ANDEN_FLEX if solicitud.incluir_anden_flex else None,
    )
    return RespuestaSlots(
        fecha=solicitud.fecha,
        duracion_minutos=duracion,
        capacidad_dia=capacidad_dia(
            andenes_recibo=settings.andenes_recibo,
            horas=settings.horas_operacion,
            horas_anden_flex=settings.horas_anden_flex
            if solicitud.incluir_anden_flex
            else 0,
        ),
        total_slots=len(libres),
        slots=[
            SlotLibre(
                anden=slot.anden or 0,
                hora_inicio=slot.inicio,
                hora_fin=slot.fin,
                es_anden_flex=slot.anden == ANDEN_FLEX,
            )
            for slot in libres
        ],
    )


@router.post("", response_model=RespuestaCita, status_code=status.HTTP_201_CREATED)
def reservar_cita(
    solicitud: SolicitudCita, sesion: SesionDep, validador: ValidadorDep
) -> RespuestaCita:
    """Reserva una cita si el CFDI sirve, el andén está libre y la ventana aplica."""
    repo_citas = RepositorioCitas(sesion)
    repo_ordenes = RepositorioOrdenes(sesion)

    proveedor = repo_ordenes.proveedor_por_clave(solicitud.proveedor)
    if proveedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "proveedor no registrado")
    orden = repo_ordenes.por_folio(solicitud.orden_compra)
    if orden is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "orden de compra no encontrada")

    cfdi_validado = False
    if solicitud.uuid_cfdi:
        resultado = validador.validar(solicitud.uuid_cfdi)
        if resultado.bloquea_cita:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"CFDI no utilizable: {resultado.detalle}"
            )
        cfdi_validado = resultado.estado.name == "VIGENTE"

    duracion = duracion_minutos(solicitud.n_bultos)
    nueva = Franja.desde_duracion(solicitud.hora_inicio, duracion, anden=solicitud.anden)

    # El andén flex solo recibe en su ventana, y nadie pisa una cita existente.
    disponibles = slots_disponibles(
        duracion=duracion,
        ocupadas=repo_citas.franjas_ocupadas(solicitud.fecha),
    )
    if not any(
        s.anden == nueva.anden and s.inicio == nueva.inicio for s in disponibles
    ):
        ocupadas = repo_citas.franjas_ocupadas(solicitud.fecha)
        motivo = (
            "el andén ya tiene una cita en esa franja"
            if hay_traslape(nueva, ocupadas)
            else "la franja no es válida para ese andén (ventana u horario)"
        )
        raise HTTPException(status.HTTP_409_CONFLICT, motivo)

    # El folio se calcula sin candado; si otra reserva simultánea tomó el
    # mismo consecutivo, `ix_cita_folio` lo detecta y se reintenta con el
    # siguiente. Un choque de andén, en cambio, es definitivo (409).
    for intento in range(INTENTOS_FOLIO):
        cita = Cita(
            folio=repo_citas.siguiente_folio(solicitud.fecha),
            proveedor_id=proveedor.id,
            orden_compra_id=orden.id,
            fecha=solicitud.fecha,
            anden=solicitud.anden,
            hora_inicio=nueva.inicio,
            hora_fin=nueva.fin,
            n_bultos_declarados=solicitud.n_bultos,
            duracion_minutos=duracion,
        )
        try:
            repo_citas.guardar(cita)
            break
        except IntegrityError as exc:
            sesion.rollback()
            restriccion = restriccion_violada(exc)
            if restriccion == "ix_cita_folio" and intento + 1 < INTENTOS_FOLIO:
                continue
            if restriccion == "ix_cita_folio":
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    "no se pudo asignar folio por concurrencia; reintente",
                ) from exc
            # Exclusión o unicidad de andén (o motor sin nombre de restricción).
            raise HTTPException(
                status.HTTP_409_CONFLICT, "el andén se ocupó mientras se reservaba"
            ) from exc

    # Cita confirmada => sus etiquetas quedan listas para imprimir (C4) y
    # para el paquete del handheld (C2).
    asegurar_desglose(sesion, cita)
    sesion.commit()

    return RespuestaCita(
        folio=cita.folio,
        proveedor=solicitud.proveedor,
        orden_compra=solicitud.orden_compra,
        fecha=cita.fecha,
        anden=cita.anden,
        hora_inicio=cita.hora_inicio,
        hora_fin=cita.hora_fin,
        duracion_minutos=cita.duracion_minutos,
        estado=cita.estado,
        cfdi_validado=cfdi_validado,
    )


def _resumen(sesion: Session, cita: Cita) -> ResumenCita:
    proveedor = sesion.get(Proveedor, cita.proveedor_id)
    orden = sesion.get(OrdenCompra, cita.orden_compra_id)
    return ResumenCita(
        folio=cita.folio,
        proveedor=proveedor.clave if proveedor else "",
        razon_social=proveedor.razon_social if proveedor else "",
        orden_compra=orden.folio if orden else "",
        fecha=cita.fecha,
        anden=cita.anden,
        hora_inicio=cita.hora_inicio,
        hora_fin=cita.hora_fin,
        n_bultos=cita.n_bultos_declarados,
        estado=cita.estado,
    )


@router.get("", response_model=list[ResumenCita])
def listar_citas(sesion: SesionDep, fecha: date | None = None) -> list[ResumenCita]:
    """Citas (todas o las de un día), la última reservada primero.

    C4 abre por omisión la primera: es la que el proveedor acaba de crear.
    """
    consulta = select(Cita).order_by(Cita.id.desc())
    if fecha is not None:
        consulta = consulta.where(Cita.fecha == fecha)
    return [_resumen(sesion, c) for c in sesion.scalars(consulta.limit(200)).all()]


@router.get("/{folio}/etiquetas", response_model=RespuestaEtiquetasCita)
def etiquetas_de_cita(folio: str, sesion: SesionDep) -> RespuestaEtiquetasCita:
    """Etiquetas de la cita, con la cadena QR firmada tal como se imprime.

    Si la cita es anterior al desglose automático, lo genera aquí.
    """
    cita = RepositorioCitas(sesion).por_folio(folio)
    if cita is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "cita no encontrada")

    bultos = bultos_de_cita(sesion, cita)
    if not bultos:
        bultos = asegurar_desglose(sesion, cita)
        sesion.commit()

    descripciones = dict(
        sesion.execute(
            select(LineaOrdenCompra.sku, LineaOrdenCompra.descripcion).where(
                LineaOrdenCompra.orden_compra_id == cita.orden_compra_id
            )
        ).all()
    )
    nombres = dict(sesion.execute(select(Sucursal.clave, Sucursal.nombre)).all())

    return RespuestaEtiquetasCita(
        cita=_resumen(sesion, cita),
        total=len(bultos),
        bultos=[
            BultoEtiqueta(
                id_bulto=b.id_bulto,
                secuencia=i,
                sku=b.sku,
                descripcion=descripciones.get(b.sku) or "",
                sucursal=b.sucursal,
                nombre_sucursal=nombres.get(b.sucursal, ""),
                cantidad=b.cantidad,
                peso_kg=b.peso_kg,
                volumen_m3=b.volumen_m3,
                estado=b.estado,
                cadena_qr=b.cadena_qr,
            )
            for i, b in enumerate(bultos, start=1)
        ],
    )
