"""Repositorios de persistencia: el único lugar que habla SQL.

Conviven dos familias, porque los consumidores son distintos y ninguna sobra:

* las clases en singular (`RepositorioCita`, `RepositorioBulto`, ...) son el
  CRUD genérico sobre cada tabla. Hacen `flush` pero nunca `commit`: la
  transacción la controla quien llama (semillas, pruebas de persistencia);
* las clases en plural (`RepositorioCitas`, `RepositorioOrdenes`,
  `RepositorioBultos`, `RepositorioEmbarques`) son la fachada que consumen los
  routers de `app.api`. Hablan el vocabulario del dominio (devuelven `Franja`,
  `EstadoRecepcion`) y sí cierran la transacción con `commit`, porque cada
  request es una unidad de trabajo completa.

Las segundas heredan de las primeras y delegan: no hay dos consultas para lo
mismo, solo dos nombres para dos contratos.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import Select, func, insert, inspect, select
from sqlalchemy.dialects.postgresql import insert as insert_postgresql
from sqlalchemy.dialects.sqlite import insert as insert_sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base
from app.dominio.citas import Franja
from app.dominio.estados import EstadoBulto
from app.dominio.recepcion import BultoEsperado, Desenlace, EstadoRecepcion, LineaOC
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

# Un bulto en cualquiera de estos estados ya pasó por el andén y fue aceptado.
ESTADOS_BULTO_ACEPTADO = frozenset(
    e.value
    for e in (
        EstadoBulto.RECIBIDO,
        EstadoBulto.UBICADO,
        EstadoBulto.ASIGNADO_EMBARQUE,
        EstadoBulto.CARGADO,
        EstadoBulto.EMBARCADO,
        EstadoBulto.RECIBIDO_SUCURSAL,
    )
)

# `INSERT ... ON CONFLICT DO NOTHING ... RETURNING` existe en PostgreSQL (nodo
# edge) y en SQLite 3.35+ (pruebas), pero son construcciones de dialecto
# distintas. Otro motor cae al camino genérico de `insertar_idempotente`.
_INSERT_CON_UPSERT = {
    "postgresql": insert_postgresql,
    "sqlite": insert_sqlite,
}


def restriccion_violada(exc: IntegrityError) -> str | None:
    """Nombre de la restricción que disparó la `IntegrityError`.

    En PostgreSQL (psycopg 3) viene en `diag.constraint_name`. Así los routers
    distinguen un reenvío legítimo de una FK o un CHECK rotos, en vez de
    tratar cualquier violación como "duplicado".
    """
    diag = getattr(exc.orig, "diag", None)
    return getattr(diag, "constraint_name", None)


def _citas_que_ocupan_anden(fecha: date) -> Select[tuple[Cita]]:
    """Citas vivas de un día: las que de verdad bloquean un andén."""
    return select(Cita).where(
        Cita.fecha == fecha,
        Cita.estado.in_(ESTADOS_CITA_OCUPAN_ANDEN),
    )


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

    def _confirmar[E: Base](self, entidad: E) -> E:
        """Guarda y cierra la transacción, recargando lo que puso la base.

        Es lo que necesitan los routers: terminada la petición, el `id` y los
        valores por omisión ya tienen que ser legibles. Las clases en singular
        no lo usan: ahí el `commit` es de quien llama.
        """
        self.sesion.add(entidad)
        self.sesion.commit()
        self.sesion.refresh(entidad)
        return entidad


# --- Catálogo y órdenes de compra ------------------------------------------


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


# --- Citas ------------------------------------------------------------------


class RepositorioCita(RepositorioBase[Cita]):
    modelo = Cita

    def obtener_por_folio(self, folio: str) -> Cita | None:
        consulta = select(Cita).where(Cita.folio == folio)
        return self.sesion.scalars(consulta).first()

    def citas_del_dia(self, fecha: date) -> Sequence[Cita]:
        """Todas las citas que ocupan algún andén ese día."""
        consulta = _citas_que_ocupan_anden(fecha).order_by(Cita.anden, Cita.hora_inicio)
        return self.sesion.scalars(consulta).all()

    def citas_del_anden(self, fecha: date, anden: int) -> Sequence[Cita]:
        """Citas que ocupan el andén ese día (base para calcular disponibilidad)."""
        consulta = (
            _citas_que_ocupan_anden(fecha)
            .where(Cita.anden == anden)
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


class RepositorioCitas(RepositorioCita):
    """Agenda de andenes en el vocabulario del router de citas."""

    def franjas_ocupadas(self, fecha: date) -> list[Franja]:
        """Franjas vivas del día, en el formato que entiende el dominio."""
        return [
            Franja(inicio=c.hora_inicio, fin=c.hora_fin, anden=c.anden)
            for c in self.citas_del_dia(fecha)
        ]

    def por_folio(self, folio: str) -> Cita | None:
        return self.obtener_por_folio(folio)

    def guardar(self, cita: Cita) -> Cita:
        return self._confirmar(cita)

    def siguiente_folio(self, fecha: date) -> str:
        """Folio legible del día: CITA-20261125-007 (consecutivo POR DÍA).

        Dos reservas simultáneas pueden calcular el mismo consecutivo; el
        índice único `ix_cita_folio` lo detecta y el router reintenta.
        """
        del_dia = self.sesion.scalar(
            select(func.count(Cita.id)).where(Cita.fecha == fecha)
        )
        consecutivo = (del_dia or 0) + 1
        return f"CITA-{fecha:%Y%m%d}-{consecutivo:03d}"


class RepositorioOrdenes(RepositorioOrdenCompra):
    """Órdenes de compra y su desglose por bulto, como los pide el andén."""

    def por_folio(self, folio: str) -> OrdenCompra | None:
        return self.obtener_por_folio(folio)

    def proveedor_por_clave(self, clave: str) -> Proveedor | None:
        return RepositorioProveedor(self.sesion).obtener_por_clave(clave)

    def estado_recepcion(self, folio_oc: str, bloquear: bool = False) -> EstadoRecepcion:
        """Arma el estado que el dominio necesita para evaluar escaneos.

        Es exactamente el paquete que el handheld descarga al confirmar la
        cita para poder validar sin red.

        Con `bloquear=True` toma `SELECT ... FOR UPDATE` sobre las líneas de la
        OC: dos handhelds sincronizando la misma OC se serializan y el tope de
        excedente no se puede rebasar por carrera. El candado vive hasta el
        commit de quien llama.
        """
        orden = self.obtener_por_folio(folio_oc)
        if orden is None:
            return EstadoRecepcion(lineas={}, esperados={})

        consulta_lineas = (
            select(LineaOrdenCompra)
            .where(LineaOrdenCompra.orden_compra_id == orden.id)
            .order_by(LineaOrdenCompra.id)
        )
        if bloquear:
            consulta_lineas = consulta_lineas.with_for_update()
        lineas = self.sesion.scalars(consulta_lineas).all()
        bultos = RepositorioBulto(self.sesion).listar_por_orden(orden.id)

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

        # Y lo ya escaneado también: sin esto cada request arranca en blanco y
        # el cierre reporta 0 aceptados. El desenlace de un rechazo sale de la
        # bitácora; el de un bulto que avanzó, es ACEPTADO por definición.
        consulta_rechazos = (
            select(EventoBulto.bulto_id, EventoBulto.desenlace)
            .join(Bulto, Bulto.id == EventoBulto.bulto_id)
            .where(
                Bulto.orden_compra_id == orden.id,
                EventoBulto.estado == EstadoBulto.RECHAZADO.value,
            )
        )
        # `.all()`: `dict(Result)` no sirve, Result expone `.keys()` y dict lo
        # trataría como mapeo.
        desenlace_por_bulto = dict(self.sesion.execute(consulta_rechazos).all())
        for b in bultos:
            if b.estado in ESTADOS_BULTO_ACEPTADO:
                estado.escaneados[b.id_bulto] = Desenlace.ACEPTADO
            elif b.estado == EstadoBulto.RECHAZADO.value:
                previo = desenlace_por_bulto.get(b.id)
                estado.escaneados[b.id_bulto] = (
                    Desenlace(previo)
                    if previo in Desenlace.__members__
                    else Desenlace.RECHAZADO_SIN_REGISTRO
                )
        return estado

    def sumar_recibido(self, orden_compra_id: int, sku: str, cantidad: int) -> None:
        """Persiste lo aceptado en la línea de la OC (en la transacción en curso)."""
        linea = self.sesion.scalars(
            select(LineaOrdenCompra).where(
                LineaOrdenCompra.orden_compra_id == orden_compra_id,
                LineaOrdenCompra.sku == sku,
            )
        ).first()
        if linea is not None:
            linea.cantidad_recibida = (linea.cantidad_recibida or 0) + cantidad


# --- Bultos y su bitácora ---------------------------------------------------


class RepositorioBulto(RepositorioBase[Bulto]):
    modelo = Bulto

    def obtener_por_id_bulto(self, id_bulto: str) -> Bulto | None:
        consulta = select(Bulto).where(Bulto.id_bulto == id_bulto)
        return self.sesion.scalars(consulta).first()

    def listar_por_cita(self, cita_id: int) -> Sequence[Bulto]:
        """Bultos de una cita, para armar el paquete offline del operador."""
        consulta = select(Bulto).where(Bulto.cita_id == cita_id).order_by(Bulto.id_bulto)
        return self.sesion.scalars(consulta).all()

    def listar_por_orden(self, orden_compra_id: int) -> Sequence[Bulto]:
        """Bultos declarados en el desglose de una OC."""
        consulta = (
            select(Bulto)
            .where(Bulto.orden_compra_id == orden_compra_id)
            .order_by(Bulto.id_bulto)
        )
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

    def existe(self, uuid_evento: str) -> bool:
        """Primera defensa de idempotencia: el UUID ya llegó antes."""
        consulta = select(EventoBulto.id).where(EventoBulto.uuid_evento == uuid_evento)
        return self.sesion.scalar(consulta) is not None

    def insertar_idempotente(self, valores: Mapping[str, Any]) -> bool:
        """Inserta el evento; devuelve False si `uuid_evento` ya existía.

        El `ON CONFLICT DO NOTHING` es específico del dialecto, así que se elige
        el constructor según el motor conectado; donde no exista se comprueba y
        luego se inserta (sin la garantía atómica, pero sin romper).
        """
        constructor = _INSERT_CON_UPSERT.get(self.sesion.get_bind().dialect.name)
        if constructor is None:
            if self.existe(str(valores["uuid_evento"])):
                return False
            self.sesion.execute(insert(EventoBulto).values(**valores))
            return True

        instruccion = (
            constructor(EventoBulto)
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


class RepositorioBultos(RepositorioBulto):
    """Bultos y su bitácora de eventos, como los usan etiquetas y recepción."""

    def por_id_bulto(self, id_bulto: str) -> Bulto | None:
        return self.obtener_por_id_bulto(id_bulto)

    def evento_existe(self, uuid_evento: str) -> bool:
        return RepositorioEventoBulto(self.sesion).existe(uuid_evento)

    def registrar_evento(self, evento: EventoBulto) -> EventoBulto:
        return self._confirmar(evento)


# --- Consolidación y embarques ----------------------------------------------


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


class RepositorioEmbarques(RepositorioEmbarque):
    """Embarques abiertos, tarimas acumuladas y actas, como los pide la API."""

    def abierto_de_sucursal(self, sucursal: str) -> Embarque | None:
        return self.obtener_abierto_por_sucursal(sucursal)

    def ocupacion_abierta(self, sucursal: str) -> float | None:
        """Ocupación del embarque abierto: el dato que decide el cross-dock."""
        embarque = self.obtener_abierto_por_sucursal(sucursal)
        return None if embarque is None else embarque.ocupacion

    def tarimas_de_sucursal(self, sucursal: str) -> list[Tarima]:
        return list(RepositorioTarima(self.sesion).pendientes_consolidacion(sucursal))

    def guardar(self, embarque: Embarque) -> Embarque:
        return self._confirmar(embarque)

    def guardar_acta(self, acta: Acta) -> Acta:
        return self._confirmar(acta)
