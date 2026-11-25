"""Repositorios: el único lugar que habla SQL.

El dominio recibe y devuelve objetos propios; estas clases traducen entre la
base y esos objetos. Así la lógica de negocio se prueba sin levantar Postgres.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dominio.citas import Franja
from app.dominio.recepcion import BultoEsperado, EstadoRecepcion, LineaOC
from app.modelos import (
    Acta,
    Bulto,
    Cita,
    Embarque,
    EventoBulto,
    LineaOrdenCompra,
    OrdenCompra,
    Proveedor,
    Tarima,
)


class RepositorioCitas:
    """Lectura y escritura de la agenda de andenes."""

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def franjas_ocupadas(self, fecha: date) -> list[Franja]:
        """Franjas vivas del día, en el formato que entiende el dominio."""
        filas = self.sesion.scalars(
            select(Cita).where(
                Cita.fecha == fecha,
                Cita.estado.in_(("CONFIRMADA", "EN_DESCARGA")),
            )
        ).all()
        return [
            Franja(inicio=c.hora_inicio, fin=c.hora_fin, anden=c.anden) for c in filas
        ]

    def por_folio(self, folio: str) -> Cita | None:
        return self.sesion.scalar(select(Cita).where(Cita.folio == folio))

    def guardar(self, cita: Cita) -> Cita:
        self.sesion.add(cita)
        self.sesion.commit()
        self.sesion.refresh(cita)
        return cita

    def siguiente_folio(self, fecha: date) -> str:
        """Folio legible del día: CITA-20261125-007."""
        total = self.sesion.scalar(
            select(Cita.id).where(Cita.fecha == fecha).order_by(Cita.id.desc()).limit(1)
        )
        consecutivo = (total or 0) + 1
        return f"CITA-{fecha:%Y%m%d}-{consecutivo:03d}"


class RepositorioOrdenes:
    """Órdenes de compra y su desglose por bulto."""

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def por_folio(self, folio: str) -> OrdenCompra | None:
        return self.sesion.scalar(select(OrdenCompra).where(OrdenCompra.folio == folio))

    def proveedor_por_clave(self, clave: str) -> Proveedor | None:
        return self.sesion.scalar(select(Proveedor).where(Proveedor.clave == clave))

    def estado_recepcion(self, folio_oc: str) -> EstadoRecepcion:
        """Arma el estado que el dominio necesita para evaluar escaneos.

        Es exactamente el paquete que el handheld descarga al confirmar la
        cita para poder validar sin red.
        """
        orden = self.por_folio(folio_oc)
        if orden is None:
            return EstadoRecepcion(lineas={}, esperados={})

        lineas = self.sesion.scalars(
            select(LineaOrdenCompra).where(LineaOrdenCompra.orden_compra_id == orden.id)
        ).all()
        bultos = self.sesion.scalars(
            select(Bulto).where(Bulto.orden_compra_id == orden.id)
        ).all()

        estado = EstadoRecepcion.desde_listas(
            lineas=[
                LineaOC(
                    sku=linea.sku,
                    cantidad_solicitada=linea.cantidad_solicitada,
                    precio_unitario=linea.precio_unitario,
                )
                for linea in lineas
            ],
            esperados=[
                BultoEsperado(id_bulto=b.id_bulto, sku=b.sku, cantidad=b.cantidad)
                for b in bultos
            ],
        )
        # Lo ya recibido se rehidrata para que la idempotencia sobreviva a un
        # reinicio del equipo o del servicio.
        for linea in lineas:
            if linea.cantidad_recibida:
                estado.recibidos[linea.sku] = linea.cantidad_recibida
        return estado


class RepositorioBultos:
    """Bultos y su bitácora de eventos."""

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def por_id_bulto(self, id_bulto: str) -> Bulto | None:
        return self.sesion.scalar(select(Bulto).where(Bulto.id_bulto == id_bulto))

    def evento_existe(self, uuid_evento: str) -> bool:
        """Primera defensa de idempotencia: el UUID ya llegó antes."""
        return (
            self.sesion.scalar(
                select(EventoBulto.id).where(EventoBulto.uuid_evento == uuid_evento)
            )
            is not None
        )

    def registrar_evento(self, evento: EventoBulto) -> EventoBulto:
        self.sesion.add(evento)
        self.sesion.commit()
        self.sesion.refresh(evento)
        return evento


class RepositorioEmbarques:
    """Embarques abiertos, tarimas acumuladas y actas."""

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def abierto_de_sucursal(self, sucursal: str) -> Embarque | None:
        return self.sesion.scalar(
            select(Embarque).where(
                Embarque.sucursal == sucursal, Embarque.estado == "ABIERTO"
            )
        )

    def ocupacion_abierta(self, sucursal: str) -> float | None:
        """Ocupación del embarque abierto: el dato que decide el cross-dock."""
        embarque = self.abierto_de_sucursal(sucursal)
        return None if embarque is None else embarque.ocupacion

    def tarimas_de_sucursal(self, sucursal: str) -> list[Tarima]:
        return list(
            self.sesion.scalars(
                select(Tarima)
                .where(Tarima.sucursal == sucursal, Tarima.embarque_id.is_(None))
                .order_by(Tarima.armada_en)
            ).all()
        )

    def guardar(self, embarque: Embarque) -> Embarque:
        self.sesion.add(embarque)
        self.sesion.commit()
        self.sesion.refresh(embarque)
        return embarque

    def guardar_acta(self, acta: Acta) -> Acta:
        self.sesion.add(acta)
        self.sesion.commit()
        self.sesion.refresh(acta)
        return acta
