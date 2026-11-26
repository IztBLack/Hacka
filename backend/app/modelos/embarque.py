"""Embarque a sucursal, con los datos que exige la Carta Porte 3.1."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, MixinFechas


class Embarque(Base, MixinFechas):
    """Unidad asignada a una sucursal, abierta mientras acumula tarimas.

    La Relación de Embarque lleva sello de seguridad, kilometraje y firma del
    operador (la v1 omitía el sello, que es control antirrobo básico) y
    alimenta el complemento Carta Porte 3.1 del transportista.
    """

    __tablename__ = "embarque"
    __table_args__ = (
        Index(
            "uq_embarque_abierto_sucursal",
            "sucursal",
            unique=True,
            postgresql_where=text("estado = 'ABIERTO'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folio: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    sucursal: Mapped[str] = mapped_column(String(16), index=True)

    # TORTON | RABON | CAMIONETA_3_5, según la selección del dominio.
    clase_unidad: Mapped[str | None] = mapped_column(String(16))
    posiciones_unidad: Mapped[int | None] = mapped_column(Integer)
    # ABIERTO | LIBERADO | CARGADO | EN_RUTA | ENTREGADO | CANCELADO
    estado: Mapped[str] = mapped_column(String(16), default="ABIERTO", index=True)

    tarimas_acumuladas: Mapped[int] = mapped_column(Integer, default=0)
    peso_kg: Mapped[float] = mapped_column(Float, default=0.0)
    volumen_m3: Mapped[float] = mapped_column(Float, default=0.0)
    ocupacion: Mapped[float] = mapped_column(Float, default=0.0)

    motivo_liberacion: Mapped[str | None] = mapped_column(String(32))
    liberado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    qr_maestro: Mapped[str | None] = mapped_column(String(160))
    sello_seguridad: Mapped[str | None] = mapped_column(String(32))
    km_salida: Mapped[int | None] = mapped_column(Integer)
    operador: Mapped[str | None] = mapped_column(String(100))
    placas: Mapped[str | None] = mapped_column(String(16))
    permiso_sict: Mapped[str | None] = mapped_column(String(32))
    uuid_carta_porte: Mapped[str | None] = mapped_column(String(36))

    tarimas: Mapped[list[Tarima]] = relationship(  # noqa: F821
        back_populates="embarque"
    )

    def __repr__(self) -> str:
        return f"<Embarque {self.folio} {self.sucursal} {self.estado}>"