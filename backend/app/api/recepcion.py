"""Router de recepción en andén.

El handheld es offline-first: valida contra su copia local y sincroniza aquí.
Este router recibe eventos ya evaluados en el equipo y los vuelve a evaluar en
el servidor (no se confía en el cliente), apoyado en el UUID del evento para
no duplicar nada al vaciar la cola.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import ahora_utc, obtener_sesion
from app.dominio.estados import EstadoBulto, transicion_valida
from app.dominio.recepcion import (
    BultoEsperado,
    Desenlace,
    EstadoRecepcion,
    LineaOC,
    calcular_faltantes,
    evaluar_bulto,
)
from app.esquemas.recepcion import (
    DestinoSalida,
    LineaFaltanteSalida,
    RespuestaCierreCita,
    RespuestaEscaneo,
    RespuestaSimulacion,
    SolicitudEscaneo,
    SolicitudSimulacion,
)
from app.modelos import Acta, EventoBulto, TipoActa
from app.servicios.repositorios import (
    RepositorioBultos,
    RepositorioCitas,
    RepositorioEmbarques,
    RepositorioOrdenes,
)

router = APIRouter()

SesionDep = Annotated[Session, Depends(obtener_sesion)]

# Qué estado deja cada desenlace en el bulto.
ESTADO_POR_DESENLACE = {
    Desenlace.ACEPTADO: EstadoBulto.RECIBIDO,
    Desenlace.RECHAZADO_EXCEDENTE: EstadoBulto.RECHAZADO,
    Desenlace.RECHAZADO_SKU_NO_SOLICITADO: EstadoBulto.RECHAZADO,
    Desenlace.RECHAZADO_FIRMA_INVALIDA: EstadoBulto.RECHAZADO,
    Desenlace.RECHAZADO_SIN_REGISTRO: EstadoBulto.RECHAZADO,
}

TIPO_ACTA_POR_DESENLACE = {
    Desenlace.RECHAZADO_EXCEDENTE: TipoActa.EXCEDENTE,
    Desenlace.RECHAZADO_SKU_NO_SOLICITADO: TipoActa.SKU_NO_SOLICITADO,
    Desenlace.RECHAZADO_FIRMA_INVALIDA: TipoActa.FIRMA_INVALIDA,
    Desenlace.RECHAZADO_SIN_REGISTRO: TipoActa.SIN_REGISTRO,
}


def _a_salida(resultado, acumulado: int | None = None) -> RespuestaEscaneo:
    """Traduce el resultado del dominio al contrato de la API."""
    destino = None
    if resultado.destino is not None:
        destino = DestinoSalida(
            tipo=resultado.destino.tipo.value,
            ubicacion=resultado.destino.ubicacion,
            motivo=resultado.destino.motivo,
        )
    return RespuestaEscaneo(
        desenlace=resultado.desenlace.value,
        id_bulto=resultado.id_bulto,
        motivo=resultado.motivo,
        sku=resultado.sku,
        cantidad=resultado.cantidad,
        destino=destino,
        acumulado_sku=acumulado,
    )


@router.post("/escaneo", response_model=RespuestaEscaneo)
def registrar_escaneo(solicitud: SolicitudEscaneo, sesion: SesionDep) -> RespuestaEscaneo:
    """Sincroniza un escaneo del andén.

    Tres capas de idempotencia: el UUID del evento, la clave única
    (bulto, estado) en la base y el acumulado del dominio.
    """
    repo_citas = RepositorioCitas(sesion)
    repo_bultos = RepositorioBultos(sesion)
    repo_ordenes = RepositorioOrdenes(sesion)
    repo_embarques = RepositorioEmbarques(sesion)

    cita = repo_citas.por_folio(solicitud.cita)
    if cita is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "cita no encontrada")
    if repo_bultos.evento_existe(solicitud.uuid_evento):
        return RespuestaEscaneo(
            desenlace=Desenlace.DUPLICADO.value,
            id_bulto="",
            motivo="evento ya sincronizado (mismo UUID): la cola no reprocesa",
        )

    estado = repo_ordenes.estado_recepcion(_folio_oc(sesion, cita.orden_compra_id))

    # Lectura previa del id impreso, solo para traer el contexto de acomodo
    # (sucursal y ubicación). Todavía no es un dato confiable: si la firma
    # falla, el escaneo se rechaza antes de que ese contexto importe.
    partes = solicitud.cadena_qr.split("|")
    bulto = repo_bultos.por_id_bulto(partes[1]) if len(partes) > 1 else None
    ocupacion = (
        repo_embarques.ocupacion_abierta(bulto.sucursal) if bulto is not None else None
    )

    resultado = evaluar_bulto(
        cadena_qr=solicitud.cadena_qr,
        llave=settings.llave_qr_bytes,
        estado=estado,
        ocupacion_embarque_abierto=ocupacion,
        ubicacion_rack=bulto.ubicacion if bulto is not None else None,
    )

    if bulto is not None:
        nuevo_estado = ESTADO_POR_DESENLACE.get(resultado.desenlace)
        if nuevo_estado is not None:
            # Se avanza por la máquina de estados, un paso a la vez.
            if transicion_valida(EstadoBulto(bulto.estado), EstadoBulto.ESCANEADO_ANDEN):
                bulto.estado = EstadoBulto.ESCANEADO_ANDEN.value
            if not transicion_valida(EstadoBulto(bulto.estado), nuevo_estado):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"transición ilegal: {bulto.estado} -> {nuevo_estado.value}",
                )
            bulto.estado = nuevo_estado.value
            if resultado.destino is not None:
                bulto.tipo_destino = resultado.destino.tipo.value
                bulto.ubicacion = resultado.destino.ubicacion
            if resultado.rechazado:
                bulto.motivo_rechazo = resultado.motivo

        try:
            repo_bultos.registrar_evento(
                EventoBulto(
                    uuid_evento=solicitud.uuid_evento,
                    bulto_id=bulto.id,
                    estado=bulto.estado,
                    desenlace=resultado.desenlace.value,
                    motivo=resultado.motivo,
                    ocurrido_en=solicitud.ocurrido_en or ahora_utc(),
                    sincronizado_en=ahora_utc(),
                    dispositivo=solicitud.dispositivo,
                    operador=solicitud.operador,
                )
            )
        except IntegrityError:
            # La clave única (bulto, estado) ya tenía este evento: es un reenvío.
            sesion.rollback()
            return RespuestaEscaneo(
                desenlace=Desenlace.DUPLICADO.value,
                id_bulto=resultado.id_bulto,
                motivo="el bulto ya registró este estado",
            )

    tipo_acta = TIPO_ACTA_POR_DESENLACE.get(resultado.desenlace)
    if tipo_acta is not None:
        RepositorioEmbarques(sesion).guardar_acta(
            Acta(
                folio=f"ACTA-{tipo_acta.value}-{resultado.id_bulto}-{ahora_utc():%H%M%S}",
                tipo=tipo_acta.value,
                cita_id=cita.id,
                orden_compra_id=cita.orden_compra_id,
                bulto_id=bulto.id if bulto is not None else None,
                cuerpo={
                    "id_bulto": resultado.id_bulto,
                    "sku": resultado.sku,
                    "cantidad": resultado.cantidad,
                    "motivo": resultado.motivo,
                },
            )
        )

    acumulado = estado.cantidad_recibida(resultado.sku) if resultado.sku else None
    return _a_salida(resultado, acumulado)


def _folio_oc(sesion: Session, orden_compra_id: int) -> str:
    """Folio de la OC de una cita."""
    from app.modelos import OrdenCompra

    orden = sesion.get(OrdenCompra, orden_compra_id)
    if orden is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "orden de compra no encontrada")
    return orden.folio


@router.post("/cierre/{folio_cita}", response_model=RespuestaCierreCita)
def cerrar_cita(folio_cita: str, sesion: SesionDep) -> RespuestaCierreCita:
    """Cierra la cita y genera el Acta de Faltante si hay delta.

    Es el flujo que la v1 no tenía: el faltante se detecta al cerrar, no
    semanas después cuando Compras revisa la factura.
    """
    repo_citas = RepositorioCitas(sesion)
    cita = repo_citas.por_folio(folio_cita)
    if cita is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "cita no encontrada")

    estado = RepositorioOrdenes(sesion).estado_recepcion(
        _folio_oc(sesion, cita.orden_compra_id)
    )
    acta_dominio = calcular_faltantes(estado)

    folio_acta = None
    if acta_dominio.hay_faltantes:
        folio_acta = f"ACTA-FALTANTE-{cita.folio}"
        RepositorioEmbarques(sesion).guardar_acta(
            Acta(
                folio=folio_acta,
                tipo=TipoActa.FALTANTE.value,
                cita_id=cita.id,
                orden_compra_id=cita.orden_compra_id,
                importe=acta_dominio.importe_nota_credito,
                cuerpo={
                    "lineas": [
                        {
                            "sku": linea.sku,
                            "solicitada": linea.cantidad_solicitada,
                            "recibida": linea.cantidad_recibida,
                            "faltante": linea.cantidad_faltante,
                            "importe": linea.importe,
                        }
                        for linea in acta_dominio.lineas
                    ]
                },
            )
        )

    cita.estado = "CERRADA"
    sesion.commit()

    aceptados = sum(1 for d in estado.escaneados.values() if d is Desenlace.ACEPTADO)
    rechazados = sum(
        1 for d in estado.escaneados.values() if d.name.startswith("RECHAZADO")
    )
    return RespuestaCierreCita(
        cita=cita.folio,
        bultos_aceptados=aceptados,
        bultos_rechazados=rechazados,
        hay_faltantes=acta_dominio.hay_faltantes,
        folio_acta=folio_acta,
        importe_nota_credito=acta_dominio.importe_nota_credito,
        faltantes=[
            LineaFaltanteSalida(
                sku=linea.sku,
                cantidad_solicitada=linea.cantidad_solicitada,
                cantidad_recibida=linea.cantidad_recibida,
                cantidad_faltante=linea.cantidad_faltante,
                importe=linea.importe,
            )
            for linea in acta_dominio.lineas
        ],
    )


@router.post("/simulacion", response_model=RespuestaSimulacion)
def simular_recepcion(solicitud: SolicitudSimulacion) -> RespuestaSimulacion:
    """Simulador del handheld: no toca la base, solo el dominio.

    Es el módulo 3 del prototipo: muestra los tres desenlaces (aceptación,
    rechazo por excedente o SKU, rechazo por firma) y la idempotencia.
    """
    estado = EstadoRecepcion.desde_listas(
        lineas=[
            LineaOC(
                sku=linea.sku,
                cantidad_solicitada=linea.cantidad_solicitada,
                precio_unitario=linea.precio_unitario,
            )
            for linea in solicitud.lineas
        ],
        esperados=[
            BultoEsperado(id_bulto=b.id_bulto, sku=b.sku, cantidad=b.cantidad)
            for b in solicitud.esperados
        ],
    )

    resultados = [
        _a_salida(
            evaluar_bulto(
                cadena_qr=cadena,
                llave=settings.llave_qr_bytes,
                estado=estado,
                ocupacion_embarque_abierto=solicitud.ocupacion_embarque_abierto,
                ubicacion_rack=solicitud.ubicacion_rack,
            )
        )
        for cadena in solicitud.escaneos
    ]
    acta = calcular_faltantes(estado)

    return RespuestaSimulacion(
        resultados=resultados,
        recibidos_por_sku=dict(estado.recibidos),
        faltantes=[
            LineaFaltanteSalida(
                sku=linea.sku,
                cantidad_solicitada=linea.cantidad_solicitada,
                cantidad_recibida=linea.cantidad_recibida,
                cantidad_faltante=linea.cantidad_faltante,
                importe=linea.importe,
            )
            for linea in acta.lineas
        ],
        importe_nota_credito=acta.importe_nota_credito,
    )
