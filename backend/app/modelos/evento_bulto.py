"""Bitácora de eventos del bulto: la pieza que hace idempotente la sincronización."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, ahora_utc


class EventoBulto(Base):
    """Un cambio de estado reportado por un handheld.

    Dos defensas contra el doble conteo:
      * `uuid_evento` único, generado en el equipo (UUID v4): si WorkManager
        reenvía la cola tras una reconexión, el insert choca y se descarta;
      * clave única (bulto_id, estado): un bulto no puede registrar dos veces
        el mismo estado, así que ningún escaneo repetido suma inventario.
    """

    __tablename__ = "evento_bulto"
    __table_args__ = (
        UniqueConstraint("bulto_id", "estado", name="uq_bulto_estado"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid_evento: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    bulto_id: Mapped[int] = mapped_column(ForeignKey("bulto.id"), index=True)

    estado: Mapped[str] = mapped_column(String(24))
    desenlace: Mapped[str | None] = mapped_column(String(32))
    motivo: Mapped[str | None] = mapped_column(String(200))

    # Momento del escaneo en el andén (no el de la sincronización).
    ocurrido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=ahora_utc, index=True
    )
    sincronizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispositivo: Mapped[str | None] = mapped_column(String(32))
    operador: Mapped[str | None] = mapped_column(String(64))

    bulto: Mapped["Bulto"] = relationship(back_populates="eventos")  # noqa: F821

    def __repr__(self) -> str:
        return f"<EventoBulto {self.uuid_evento} {self.estado}>"
