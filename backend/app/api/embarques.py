"""Router de embarques: liberación, Relación de Embarque y conciliación en destino."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import ahora_utc, obtener_sesion
from app.dominio.consolidacion import ocupacion, puede_liberar
from app.esquemas.embarques import (
    DatosCartaPorte,
    RespuestaLiberacion,
    RespuestaRecepcionSucursal,
    RespuestaRelacionEmbarque,
    SolicitudLiberacion,
    SolicitudRecepcionSucursal,
)
from app.modelos import Acta, Embarque, TipoActa
from app.servicios.impresion import generar_html_relacion_embarque
from app.servicios.repositorios import RepositorioEmbarques

router = APIRouter()

SesionDep = Annotated[Session, Depends(obtener_sesion)]


@router.post("/liberar", response_model=RespuestaLiberacion)
def liberar_embarque(
    solicitud: SolicitudLiberacion, sesion: SesionDep
) -> RespuestaLiberacion:
    """Libera un embarque si el dominio lo autoriza.

    Si sale por antigüedad, se genera el Acta de Excepción y queda marcada
    para reporte a gerencia: la excepción es visible y auditable, no silenciosa.
    """
    repo = RepositorioEmbarques(sesion)
    decision = puede_liberar(
        tarimas_acumuladas=len(solicitud.tarimas),
        peso_kg=solicitud.peso_kg,
        volumen_m3=solicitud.volumen_m3,
        antiguedad_horas=solicitud.antiguedad_horas,
        horas_limite=settings.horas_antiguedad_limite,
    )

    if not decision.liberar or decision.unidad is None:
        return RespuestaLiberacion(
            folio="",
            sucursal=solicitud.sucursal,
            clase_unidad=None,
            motivo_liberacion=decision.motivo.value,
            liberado=False,
            requiere_acta=False,
            detalle=decision.detalle,
        )

    momento = ahora_utc()
    folio = f"EMB-{solicitud.sucursal}-{momento:%Y%m%d%H%M%S}"
    porcentaje = ocupacion(len(solicitud.tarimas), decision.unidad)

    embarque = repo.guardar(
        Embarque(
            folio=folio,
            sucursal=solicitud.sucursal,
            clase_unidad=decision.unidad.clase.value,
            posiciones_unidad=decision.unidad.posiciones,
            estado="LIBERADO",
            tarimas_acumuladas=len(solicitud.tarimas),
            peso_kg=solicitud.peso_kg,
            volumen_m3=solicitud.volumen_m3,
            ocupacion=round(porcentaje, 4),
            motivo_liberacion=decision.motivo.value,
            liberado_en=momento,
            qr_maestro=f"EMB|{folio}|{solicitud.sucursal}|{len(solicitud.tarimas)}",
            sello_seguridad=solicitud.sello_seguridad,
            km_salida=solicitud.km_salida,
            operador=solicitud.operador,
            placas=solicitud.placas,
        )
    )

    folio_acta = None
    if decision.requiere_acta:
        folio_acta = f"ACTA-EXC-{folio}"
        repo.guardar_acta(
            Acta(
                folio=folio_acta,
                tipo=TipoActa.EXCEPCION_ANTIGUEDAD.value,
                embarque_id=embarque.id,
                cuerpo={
                    "sucursal": solicitud.sucursal,
                    "tarimas": solicitud.tarimas,
                    "antiguedad_horas": solicitud.antiguedad_horas,
                    "ocupacion": round(porcentaje, 4),
                    "detalle": decision.detalle,
                },
            )
        )

    return RespuestaLiberacion(
        folio=embarque.folio,
        sucursal=embarque.sucursal,
        clase_unidad=embarque.clase_unidad,
        motivo_liberacion=decision.motivo.value,
        liberado=True,
        requiere_acta=decision.requiere_acta,
        folio_acta=folio_acta,
        ocupacion=embarque.ocupacion,
        detalle=decision.detalle,
        liberado_en=embarque.liberado_en,
    )


def _embarque_o_404(sesion: Session, folio: str) -> Embarque:
    embarque = sesion.scalar(select(Embarque).where(Embarque.folio == folio))
    if embarque is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "embarque no encontrado")
    return embarque


@router.get("/{folio}/relacion", response_model=RespuestaRelacionEmbarque)
def consultar_relacion(folio: str, sesion: SesionDep) -> RespuestaRelacionEmbarque:
    """Datos de la Relación de Embarque, incluidos los de Carta Porte 3.1."""
    embarque = _embarque_o_404(sesion, folio)
    tarimas = [t.folio for t in embarque.tarimas]
    carta_porte = DatosCartaPorte(
        permiso_sict=embarque.permiso_sict,
        configuracion_vehicular=embarque.clase_unidad,
        placas=embarque.placas,
        completo=bool(embarque.permiso_sict and embarque.placas),
    )
    return RespuestaRelacionEmbarque(
        folio=embarque.folio,
        sucursal=embarque.sucursal,
        clase_unidad=embarque.clase_unidad,
        tarimas=tarimas,
        peso_kg=embarque.peso_kg,
        volumen_m3=embarque.volumen_m3,
        ocupacion=embarque.ocupacion,
        qr_maestro=embarque.qr_maestro or "",
        sello_seguridad=embarque.sello_seguridad,
        km_salida=embarque.km_salida,
        operador=embarque.operador,
        carta_porte=carta_porte,
        generado_en=ahora_utc(),
    )


@router.get("/{folio}/relacion.html", response_class=HTMLResponse)
def imprimir_relacion(folio: str, sesion: SesionDep) -> str:
    """HTML de la Relación de Embarque (lo que Playwright convierte a PDF)."""
    embarque = _embarque_o_404(sesion, folio)
    return generar_html_relacion_embarque(
        folio=embarque.folio,
        sucursal=embarque.sucursal,
        clase_unidad=embarque.clase_unidad or "",
        tarimas=[t.folio for t in embarque.tarimas],
        peso_kg=embarque.peso_kg,
        volumen_m3=embarque.volumen_m3,
        ocupacion=embarque.ocupacion,
        qr_maestro=embarque.qr_maestro or "",
        sello_seguridad=embarque.sello_seguridad,
        km_salida=embarque.km_salida,
        operador=embarque.operador,
    )


@router.post("/recepcion-sucursal", response_model=RespuestaRecepcionSucursal)
def recibir_en_sucursal(
    solicitud: SolicitudRecepcionSucursal, sesion: SesionDep
) -> RespuestaRecepcionSucursal:
    """Conciliación en destino con un escaneo del QR maestro."""
    partes = solicitud.qr_maestro.split("|")
    if len(partes) < 3 or partes[0] != "EMB":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "QR maestro inválido")

    embarque = _embarque_o_404(sesion, partes[1])
    if embarque.sucursal != solicitud.sucursal:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"el embarque es de {embarque.sucursal}, no de {solicitud.sucursal}",
        )

    esperadas = {t.folio for t in embarque.tarimas}
    recibidas = set(solicitud.tarimas_recibidas)
    faltantes = sorted(esperadas - recibidas)

    if not faltantes and esperadas:
        embarque.estado = "ENTREGADO"
        sesion.commit()

    return RespuestaRecepcionSucursal(
        folio=embarque.folio,
        conciliado=not faltantes and bool(esperadas),
        tarimas_esperadas=len(esperadas),
        tarimas_recibidas=len(recibidas & esperadas),
        faltantes=faltantes,
    )
