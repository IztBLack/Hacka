"""Tarima: 1.12 x 1.15 x 1.85 m, hasta 1,000 kg. Es la unidad de consolidación."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, MixinFechas, ahora_utc


class Tarima(Base, MixinFechas):
    """Tarima armada para una sucursal.

    `armada_en` no es un dato decorativo: de ahí sale la antigüedad que
    dispara la excepción de liberación a las 36 h.
    """

    __tablename__ = "tarima"
    __table_args__ = (
        CheckConstraint("peso_kg <= 1000", name="ck_tarima_peso_maximo"),
        Index(
            "ix_tarima_consolidacion",
            "sucursal",
            "armada_en",
            postgresql_where=text("embarque_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folio: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    sucursal: Mapped[str] = mapped_column(String(16), index=True)
    embarque_id: Mapped[int | None] = mapped_column(ForeignKey("embarque.id"), index=True)

    peso_kg: Mapped[float] = mapped_column(Float, default=0.0)
    volumen_m3: Mapped[float] = mapped_column(Float, default=0.0)
    n_bultos: Mapped[int] = mapped_column(Integer, default=0)

    armada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=ahora_utc, index=True
    )
    ubicacion: Mapped[str | None] = mapped_column(String(32), index=True)
    # EN_RACK | EN_FLEX | EN_ANDEN | CARGADA
    estado: Mapped[str] = mapped_column(String(16), default="EN_RACK", index=True)
    posicion_unidad: Mapped[int | None] = mapped_column(Integer)

    embarque: Mapped["Embarque | None"] = relationship(  # noqa: F821
        back_populates="tarimas"
    )

    def antiguedad_horas(self, ahora: datetime | None = None) -> float:
        """Horas desde que se armó la tarima (dato que consume el dominio)."""
        referencia = ahora or ahora_utc()
        return (referencia - self.armada_en).total_seconds() / 3600

    def __repr__(self) -> str:
        return f"<Tarima {self.folio} {self.sucursal} {self.estado}>"