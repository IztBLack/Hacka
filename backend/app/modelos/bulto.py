"""Bulto: la unidad de trazabilidad del CEDIS. Un bulto, un solo SKU."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, MixinFechas
from app.dominio.estados import EstadoBulto


class Bulto(Base, MixinFechas):
    """Un bulto etiquetado por el portal del proveedor.

    La regla de pureza del reto (un SKU por bulto) está en el modelo: hay un
    solo `sku` y una sola `cantidad`, no una tabla de contenido.
    """

    __tablename__ = "bulto"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_bulto_cantidad_positiva"),
        CheckConstraint("peso_kg > 0", name="ck_bulto_peso_positivo"),
        Index("ix_bulto_cita_estado", "cita_id", "estado"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_bulto: Mapped[str] = mapped_column(String(24), unique=True, index=True)  # B00412
    orden_compra_id: Mapped[int] = mapped_column(ForeignKey("orden_compra.id"), index=True)
    cita_id: Mapped[int | None] = mapped_column(ForeignKey("cita.id"), index=True)
    tarima_id: Mapped[int | None] = mapped_column(ForeignKey("tarima.id"), index=True)

    sucursal: Mapped[str] = mapped_column(String(16), index=True)  # SUC-14
    sku: Mapped[str] = mapped_column(String(32), index=True)
    cantidad: Mapped[int] = mapped_column(Integer)
    peso_kg: Mapped[float] = mapped_column(Float)
    volumen_m3: Mapped[float] = mapped_column(Float)

    estado: Mapped[str] = mapped_column(
        String(24), default=EstadoBulto.ETIQUETADO.value, index=True
    )
    # Cadena completa del QR, firma incluida: sirve de evidencia de lo impreso.
    cadena_qr: Mapped[str] = mapped_column(String(160))
    # CROSS_DOCK o RACK, con la ubicación que dirigió el sistema.
    tipo_destino: Mapped[str | None] = mapped_column(String(16))
    ubicacion: Mapped[str | None] = mapped_column(String(32), index=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(String(200))
    folio_reimpresion: Mapped[str | None] = mapped_column(String(32))

    cita: Mapped[Cita | None] = relationship(back_populates="bultos")  # noqa: F821
    eventos: Mapped[list[EventoBulto]] = relationship(  # noqa: F821
        back_populates="bulto", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Bulto {self.id_bulto} {self.sku} {self.estado}>"