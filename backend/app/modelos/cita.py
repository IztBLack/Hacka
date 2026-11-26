"""Cita de andén. La duración la calcula el sistema, no el proveedor."""

from __future__ import annotations

from datetime import date, time

from sqlalchemy import Date, ForeignKey, Integer, String, Time, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, MixinFechas


class Cita(Base, MixinFechas):
    """Reserva de un andén de recibo para una OC en una fecha y franja.

    El andén 5 es el flex: solo recibe de 8:00 a 13:00 y después vuelve a
    operar como andén de embarque.
    """

    __tablename__ = "cita"
    __table_args__ = (
        UniqueConstraint("fecha", "anden", "hora_inicio", name="uq_anden_inicio"),
        ExcludeConstraint(
            ("anden", "="),
            (text("tsrange(fecha + hora_inicio, fecha + hora_fin)"), "&&"),
            name="ex_cita_sin_traslape_anden",
            using="gist",
            where=text("estado IN ('CONFIRMADA', 'EN_DESCARGA')"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folio: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedor.id"), index=True)
    orden_compra_id: Mapped[int] = mapped_column(ForeignKey("orden_compra.id"), index=True)

    fecha: Mapped[date] = mapped_column(Date, index=True)
    anden: Mapped[int] = mapped_column(Integer, index=True)
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fin: Mapped[time] = mapped_column(Time)

    n_bultos_declarados: Mapped[int] = mapped_column(Integer, default=0)
    duracion_minutos: Mapped[int] = mapped_column(Integer)
    # CONFIRMADA | EN_DESCARGA | CERRADA | NO_SHOW | CANCELADA
    estado: Mapped[str] = mapped_column(String(16), default="CONFIRMADA", index=True)
    minutos_tolerancia: Mapped[int] = mapped_column(Integer, default=15)
    pase_caseta: Mapped[str | None] = mapped_column(String(64))

    bultos: Mapped[list[Bulto]] = relationship(back_populates="cita")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Cita {self.folio} anden={self.anden} {self.hora_inicio}-{self.hora_fin}>"
