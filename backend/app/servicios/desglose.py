"""Materializa el desglose de una cita: bultos con su QR firmado en la base.

Lo usa el router de citas al reservar (y, para citas creadas antes de que
existiera, al pedir sus etiquetas). Es idempotente: si la cita ya tiene
bultos no crea nada.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.dominio.desglose import LineaPendiente, planear_desglose
from app.dominio.estados import EstadoBulto
from app.dominio.qr import PayloadBulto, firmar
from app.modelos import Bulto, Cita, LineaOrdenCompra, OrdenCompra, Proveedor
from app.modelos.catalogos import Sucursal

# Factores del prototipo para peso y volumen por pieza (una "pieza" es una
# caja master). En producción vienen del maestro de artículos.
KG_POR_PIEZA = 3.4
M3_POR_PIEZA = 0.009
PESO_MAXIMO_KG = 999.0


def _id_bulto(cita_id: int, secuencia: int) -> str:
    """B + cita (5 dígitos) + secuencia (4): único global y legible al pie."""
    return f"B{cita_id:05d}{secuencia:04d}"


def bultos_de_cita(sesion: Session, cita: Cita) -> list[Bulto]:
    consulta = select(Bulto).where(Bulto.cita_id == cita.id).order_by(Bulto.id_bulto)
    return list(sesion.scalars(consulta).all())


def asegurar_desglose(sesion: Session, cita: Cita) -> list[Bulto]:
    """Bultos de la cita; si no tiene, los genera con las piezas pendientes.

    Pendiente = lo solicitado en la OC menos lo que ya va en bultos de otras
    citas de la misma OC. Hace `flush`, no `commit`: confirma quien llama.
    """
    existentes = bultos_de_cita(sesion, cita)
    if existentes:
        return existentes

    orden = sesion.get(OrdenCompra, cita.orden_compra_id)
    proveedor = sesion.get(Proveedor, cita.proveedor_id)
    if orden is None or proveedor is None:
        return []

    ya_en_bultos = dict(
        sesion.execute(
            select(Bulto.sku, func.sum(Bulto.cantidad))
            .where(Bulto.orden_compra_id == orden.id)
            .group_by(Bulto.sku)
        ).all()
    )
    lineas = sesion.scalars(
        select(LineaOrdenCompra)
        .where(LineaOrdenCompra.orden_compra_id == orden.id)
        .order_by(LineaOrdenCompra.id)
    ).all()
    pendientes = [
        LineaPendiente(
            sku=linea.sku,
            descripcion=linea.descripcion or "",
            piezas=linea.cantidad_solicitada - int(ya_en_bultos.get(linea.sku, 0) or 0),
        )
        for linea in lineas
    ]
    sucursales = list(
        sesion.scalars(
            select(Sucursal.clave).where(Sucursal.activa.is_(True)).order_by(Sucursal.clave)
        ).all()
    )

    plan = planear_desglose(pendientes, cita.n_bultos_declarados, sucursales)
    nuevos: list[Bulto] = []
    for b in plan:
        peso = min(PESO_MAXIMO_KG, round(b.piezas * KG_POR_PIEZA, 1))
        volumen = max(0.01, round(b.piezas * M3_POR_PIEZA, 2))
        id_bulto = _id_bulto(cita.id, b.secuencia)
        cadena = firmar(
            PayloadBulto(
                id_bulto=id_bulto,
                orden_compra=orden.folio,
                proveedor=proveedor.clave,
                sucursal=b.sucursal,
                sku=b.sku,
                cantidad=b.piezas,
                peso_kg=peso,
                volumen_m3=volumen,
            ),
            settings.llave_qr_bytes,
        )
        nuevos.append(
            Bulto(
                id_bulto=id_bulto,
                orden_compra_id=orden.id,
                cita_id=cita.id,
                sucursal=b.sucursal,
                sku=b.sku,
                cantidad=b.piezas,
                peso_kg=peso,
                volumen_m3=volumen,
                estado=EstadoBulto.ETIQUETADO.value,
                cadena_qr=cadena,
            )
        )
    sesion.add_all(nuevos)
    sesion.flush()
    return nuevos
