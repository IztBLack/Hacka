"""Orden de compra y sus líneas. El folio único es el UUID del CFDI 4.0."""

from __future__ import annotations

from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, MixinFechas


class OrdenCompra(Base, MixinFechas):
    """Una OC confirmada por el portal de proveedores.

    `uuid_cfdi` es el identificador único real, no un consecutivo interno: se
    valida contra el servicio de consulta del SAT para detectar factura
    cancelada o apócrifa antes de que el camión entre al patio.
    """

    __tablename__ = "orden_compra"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folio: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # OC-88213
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedor.id"), index=True)

    uuid_cfdi: Mapped[str | None] = mapped_column(String(36), unique=True, index=True)
    cfdi_validado: Mapped[bool] = mapped_column(default=False)
    cfdi_vigente: Mapped[bool | None] = mapped_column(default=None)

    fecha_emision: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(24), default="ABIERTA")
    importe_total: Mapped[float] = mapped_column(Float, default=0.0)

    lineas: Mapped[list[LineaOrdenCompra]] = relationship(
        back_populates="orden_compra", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<OrdenCompra {self.folio} {self.estado}>"


class LineaOrdenCompra(Base):
    """Un SKU solicitado dentro de la OC.

    `cantidad_solicitada` es el tope que el andén no deja rebasar; el delta
    contra lo recibido alimenta el Acta de Faltante y la nota de crédito.
    """

    __tablename__ = "linea_orden_compra"
    __table_args__ = (
        UniqueConstraint("orden_compra_id", "sku", name="uq_oc_sku"),
        CheckConstraint("cantidad_solicitada > 0", name="ck_linea_oc_cantidad_positiva"),
        Index("ix_linea_orden_compra_oc_sku", "orden_compra_id", "sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    orden_compra_id: Mapped[int] = mapped_column(
        ForeignKey("orden_compra.id"), index=True
    )
    sku: Mapped[str] = mapped_column(String(32), index=True)
    descripcion: Mapped[str] = mapped_column(String(200), default="")
    cantidad_solicitada: Mapped[int] = mapped_column(Integer)
    cantidad_recibida: Mapped[int] = mapped_column(Integer, default=0)
    precio_unitario: Mapped[float] = mapped_column(Float, default=0.0)

    orden_compra: Mapped[OrdenCompra] = relationship(back_populates="lineas")

    def __repr__(self) -> str:
        return f"<LineaOC {self.sku} {self.cantidad_recibida}/{self.cantidad_solicitada}>"
