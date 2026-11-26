"""Historial de etiquetas por bulto (reimpresiones y rotación de llaves `kid`)."""

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, MixinFechas


class Etiqueta(Base, MixinFechas):
    __tablename__ = "etiqueta"
    __table_args__ = (
        UniqueConstraint("bulto_id", "secuencia", name="uq_etiqueta_bulto_secuencia"),
        CheckConstraint("secuencia >= 1", name="ck_etiqueta_secuencia_positiva"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bulto_id: Mapped[int] = mapped_column(ForeignKey("bulto.id", ondelete="CASCADE"))
    secuencia: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    kid: Mapped[str] = mapped_column(String(32))
    firma: Mapped[str] = mapped_column(String(64))
    motivo_reimpresion: Mapped[str | None] = mapped_column(String(200), nullable=True)
