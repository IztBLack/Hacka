"""Router de etiquetas: generación firmada, verificación y reimpresión."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import ahora_utc, obtener_sesion
from app.dominio.qr import ErrorQR, PayloadBulto, firmar, verificar
from app.esquemas.etiquetas import (
    RespuestaEtiqueta,
    RespuestaLote,
    RespuestaReimpresion,
    RespuestaVerificacion,
    SolicitudEtiqueta,
    SolicitudLote,
    SolicitudReimpresion,
    SolicitudVerificacion,
)
from app.servicios.impresion import generar_zpl_etiqueta
from app.servicios.repositorios import RepositorioBultos

router = APIRouter()

SesionDep = Annotated[Session, Depends(obtener_sesion)]


def _payload_de(solicitud: SolicitudEtiqueta) -> PayloadBulto:
    return PayloadBulto(
        id_bulto=solicitud.id_bulto,
        orden_compra=solicitud.orden_compra,
        proveedor=solicitud.proveedor,
        sucursal=solicitud.sucursal,
        sku=solicitud.sku,
        cantidad=solicitud.cantidad,
        peso_kg=solicitud.peso_kg,
        volumen_m3=solicitud.volumen_m3,
    )


def _etiqueta(solicitud: SolicitudEtiqueta) -> RespuestaEtiqueta:
    cadena = firmar(_payload_de(solicitud), settings.llave_qr_bytes)
    return RespuestaEtiqueta(
        id_bulto=solicitud.id_bulto,
        cadena_qr=cadena,
        longitud_cadena=len(cadena),
    )


@router.post("", response_model=RespuestaEtiqueta, status_code=status.HTTP_201_CREATED)
def generar_etiqueta(solicitud: SolicitudEtiqueta) -> RespuestaEtiqueta:
    """Genera la cadena firmada de un bulto."""
    try:
        return _etiqueta(solicitud)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.post("/lote", response_model=RespuestaLote, status_code=status.HTTP_201_CREATED)
def generar_lote(solicitud: SolicitudLote) -> RespuestaLote:
    """Lote de etiquetas de una OC, como lo pide el portal del proveedor."""
    try:
        etiquetas = [_etiqueta(b) for b in solicitud.bultos]
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return RespuestaLote(total=len(etiquetas), etiquetas=etiquetas)


@router.post("/verificar", response_model=RespuestaVerificacion)
def verificar_etiqueta(solicitud: SolicitudVerificacion) -> RespuestaVerificacion:
    """Verifica la firma. Es lo que hace el handheld antes de aceptar un bulto."""
    try:
        payload = verificar(solicitud.cadena_qr, settings.llave_qr_bytes)
    except ErrorQR as exc:
        return RespuestaVerificacion(valida=False, motivo=str(exc))
    return RespuestaVerificacion(
        valida=True,
        id_bulto=payload.id_bulto,
        orden_compra=payload.orden_compra,
        proveedor=payload.proveedor,
        sucursal=payload.sucursal,
        sku=payload.sku,
        cantidad=payload.cantidad,
        peso_kg=payload.peso_kg,
        volumen_m3=payload.volumen_m3,
    )


@router.post("/reimprimir", response_model=RespuestaReimpresion)
def reimprimir_etiqueta(
    solicitud: SolicitudReimpresion, sesion: SesionDep
) -> RespuestaReimpresion:
    """Reimpresión controlada: folio trazable ligado al bulto original.

    Sin esto, un bulto con etiqueta mojada o rota paraliza la descarga.
    """
    repo = RepositorioBultos(sesion)
    bulto = repo.por_id_bulto(solicitud.id_bulto)
    if bulto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bulto no registrado")

    payload = verificar(bulto.cadena_qr, settings.llave_qr_bytes)
    folio = f"RE-{solicitud.id_bulto}-{ahora_utc():%Y%m%d%H%M%S}"
    bulto.folio_reimpresion = folio
    sesion.commit()

    return RespuestaReimpresion(
        folio_reimpresion=folio,
        id_bulto=bulto.id_bulto,
        cadena_qr=bulto.cadena_qr,
        zpl=generar_zpl_etiqueta(payload, bulto.cadena_qr, folio_reimpresion=folio),
    )


@router.post("/zpl", response_class=PlainTextResponse)
def generar_zpl(solicitud: SolicitudEtiqueta) -> str:
    """ZPL II listo para mandar a la Zebra ZT411 por Ethernet."""
    payload = _payload_de(solicitud)
    cadena = firmar(payload, settings.llave_qr_bytes)
    return generar_zpl_etiqueta(payload, cadena)


@router.get("/bultos/{id_bulto}", response_model=RespuestaVerificacion)
def consultar_bulto(id_bulto: str, sesion: SesionDep) -> RespuestaVerificacion:
    """Consulta de la etiqueta emitida para un bulto."""
    bulto = RepositorioBultos(sesion).por_id_bulto(id_bulto)
    if bulto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bulto no registrado")
    return verificar_etiqueta(SolicitudVerificacion(cadena_qr=bulto.cadena_qr))
