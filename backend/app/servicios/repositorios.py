"""Repositorios de persistencia: solo consultas y escritura, sin lógica de negocio.

Las operaciones hacen `flush` pero nunca `commit`; la transacción la controla quien llama.
"""

from collections.abc import Mapping, Sequence
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db import Base
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

ESTADOS_CITA_OCUPAN_ANDEN = ("CONFIRMADA", "EN_DESCARGA")


class RepositorioBase[T: Base]:
    """CRUD mínimo común. Las subclases fijan `modelo`."""

    modelo: type[T]

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def obtener(self, id_: int) -> T | None:
        return self.sesion.get(self.modelo, id_)

    def listar(self, limite: int = 100, desplazamiento: int = 0) -> Sequence[T]:
        consulta = (
            select(self.modelo)
            .order_by(*inspect(self.modelo).primary_key)
            .limit(limite)
            .offset(desplazamiento)
        )
        return self.sesion.scalars(consulta).all()

    def agregar(self, entidad: T) -> T:
        self.sesion.add(entidad)
        self.sesion.flush()
        return entidad

    def eliminar(self, entidad: T) -> None:
        self.sesion.delete(entidad)
        self.sesion.flush()


class RepositorioProveedor(RepositorioBase[Proveedor]):
    modelo = Proveedor

    def obtener_por_clave(self, clave: str) -> Proveedor | None:
        consulta = select(Proveedor).where(Proveedor.clave == clave)
        return self.sesion.scalars(consulta).first()

    def listar_activos(self) -> Sequence[Proveedor]:
        consulta = (
            select(Proveedor).where(Proveedor.activo.is_(True)).order_by(Proveedor.clave)
        )
        return self.sesion.scalars(consulta).all()


class RepositorioOrdenCompra(RepositorioBase[OrdenCompra]):
    modelo = OrdenCompra

    def obtener_por_folio(self, folio: str) -> OrdenCompra | None:
        consulta = select(OrdenCompra).where(OrdenCompra.folio == folio)
        return self.sesion.scalars(consulta).first()

    def obtener_por_uuid_cfdi(self, uuid_cfdi: str) -> OrdenCompra | None:
        consulta = select(OrdenCompra).where(OrdenCompra.uuid_cfdi == uuid_cfdi)
        return self.sesion.scalars(consulta).first()

    def listar_lineas(self, orden_compra_id: int) -> Sequence[LineaOrdenCompra]:
        consulta = (
            select(LineaOrdenCompra)
            .where(LineaOrdenCompra.orden_compra_id == orden_compra_id)
            .order_by(LineaOrdenCompra.id)
        )
        return self.sesion.scalars(consulta).all()

    def agregar_linea(self, linea: LineaOrdenCompra) -> LineaOrdenCompra:
        self.sesion.add(linea)
        self.sesion.flush()
        return linea


class RepositorioCita(RepositorioBase[Cita]):
    modelo = Cita

    def obtener_por_folio(self, folio: str) -> Cita | None:
        consulta = select(Cita).where(Cita.folio == folio)
        return self.sesion.scalars(consulta).first()

    def citas_del_anden(self, fecha: date, anden: int) -> Sequence[Cita]:
        """Citas que ocupan el andén ese día (base para calcular disponibilidad)."""
        consulta = (
            select(Cita)
            .where(
                Cita.fecha == fecha,
                Cita.anden == anden,
                Cita.estado.in_(ESTADOS_CITA_OCUPAN_ANDEN),
            )
            .order_by(Cita.hora_inicio)
        )
        return self.sesion.scalars(consulta).all()

    def hay_traslape(
        self,
        fecha: date,
        anden: int,
        hora_inicio: time,
        hora_fin: time,
        excluir_id: int | None = None,
    ) -> bool:
        consulta = select(Cita.id).where(
            Cita.fecha == fecha,
            Cita.anden == anden,
            Cita.estado.in_(ESTADOS_CITA_OCUPAN_ANDEN),
            Cita.hora_inicio < hora_fin,
            Cita.hora_fin > hora_inicio,
        )
        if excluir_id is not None:
            consulta = consulta.where(Cita.id != excluir_id)
        return self.sesion.scalars(consulta.limit(1)).first() is not None


class RepositorioBulto(RepositorioBase[Bulto]):
    modelo = Bulto

    def obtener_por_id_bulto(self, id_bulto: str) -> Bulto | None:
        consulta = select(Bulto).where(Bulto.id_bulto == id_bulto)
        return self.sesion.scalars(consulta).first()

    def listar_por_cita(self, cita_id: int) -> Sequence[Bulto]:
        """Bultos de una cita, para armar el paquete offline del operador."""
        consulta = select(Bulto).where(Bulto.cita_id == cita_id).order_by(Bulto.id_bulto)
        return self.sesion.scalars(consulta).all()

    def actualizar_estado(
        self,
        bulto_id: int,
        estado: str,
        ubicacion: str | None = None,
        motivo_rechazo: str | None = None,
    ) -> Bulto | None:
        bulto = self.sesion.get(Bulto, bulto_id)
        if bulto is None:
            return None
        bulto.estado = estado
        if ubicacion is not None:
            bulto.ubicacion = ubicacion
        if motivo_rechazo is not None:
            bulto.motivo_rechazo = motivo_rechazo
        self.sesion.flush()
        return bulto


class RepositorioEventoBulto(RepositorioBase[EventoBulto]):
    modelo = EventoBulto

    def insertar_idempotente(self, valores: Mapping[str, Any]) -> bool:
        """Inserta el evento; devuelve False si `uuid_evento` ya existía (reintento offline)."""
        instruccion = (
            pg_insert(EventoBulto)
            .values(**valores)
            .on_conflict_do_nothing(index_elements=["uuid_evento"])
            .returning(EventoBulto.id)
        )
        return self.sesion.execute(instruccion).scalar_one_or_none() is not None

    def listar_por_bulto(self, bulto_id: int) -> Sequence[EventoBulto]:
        consulta = (
            select(EventoBulto)
            .where(EventoBulto.bulto_id == bulto_id)
            .order_by(EventoBulto.ocurrido_en, EventoBulto.id)
        )
        return self.sesion.scalars(consulta).all()


class RepositorioTarima(RepositorioBase[Tarima]):
    modelo = Tarima

    def obtener_por_folio(self, folio: str) -> Tarima | None:
        consulta = select(Tarima).where(Tarima.folio == folio)
        return self.sesion.scalars(consulta).first()

    def pendientes_consolidacion(self, sucursal: str) -> Sequence[Tarima]:
        """Tarimas sin embarque de la sucursal, las más antiguas primero (usa ix parcial)."""
        consulta = (
            select(Tarima)
            .where(Tarima.sucursal == sucursal, Tarima.embarque_id.is_(None))
            .order_by(Tarima.armada_en)
        )
        return self.sesion.scalars(consulta).all()

    def pendientes_armadas_antes_de(
        self, sucursal: str, limite: datetime
    ) -> Sequence[Tarima]:
        consulta = (
            select(Tarima)
            .where(
                Tarima.sucursal == sucursal,
                Tarima.embarque_id.is_(None),
                Tarima.armada_en < limite,
            )
            .order_by(Tarima.armada_en)
        )
        return self.sesion.scalars(consulta).all()


class RepositorioEmbarque(RepositorioBase[Embarque]):
    modelo = Embarque

    def obtener_por_folio(self, folio: str) -> Embarque | None:
        consulta = select(Embarque).where(Embarque.folio == folio)
        return self.sesion.scalars(consulta).first()

    def obtener_abierto_por_sucursal(self, sucursal: str) -> Embarque | None:
        consulta = select(Embarque).where(
            Embarque.sucursal == sucursal, Embarque.estado == "ABIERTO"
        )
        return self.sesion.scalars(consulta).first()


class RepositorioActa(RepositorioBase[Acta]):
    modelo = Acta

    def obtener_por_folio(self, folio: str) -> Acta | None:
        consulta = select(Acta).where(Acta.folio == folio)
        return self.sesion.scalars(consulta).first()

    def listar_por_cita(self, cita_id: int) -> Sequence[Acta]:
        consulta = select(Acta).where(Acta.cita_id == cita_id).order_by(Acta.id)
        return self.sesion.scalars(consulta).all()

    def listar_por_embarque(self, embarque_id: int) -> Sequence[Acta]:
        consulta = select(Acta).where(Acta.embarque_id == embarque_id).order_by(Acta.id)
        return self.sesion.scalars(consulta).all()

    def listar_no_reportadas(self) -> Sequence[Acta]:
        consulta = select(Acta).where(Acta.reportada.is_(False)).order_by(Acta.id)
        return self.sesion.scalars(consulta).all()
