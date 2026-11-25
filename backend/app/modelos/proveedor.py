"""Proveedor y su score, que condiciona la prioridad de reserva de cita."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, MixinFechas


class Proveedor(Base, MixinFechas):
    """Uno de los 35 proveedores del CEDIS.

    El score (puntualidad, exactitud de etiquetado y exactitud documental) es
    la palanca de cumplimiento sin costo: con score alto el proveedor elige
    horario primero y accede a la ventana corta de 45 min.
    """

    __tablename__ = "proveedor"
    __table_args__ = (
        CheckConstraint("score BETWEEN 0 AND 100", name="ck_proveedor_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clave: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # PRV-0147
    razon_social: Mapped[str] = mapped_column(String(200))
    rfc: Mapped[str] = mapped_column(String(13), index=True)

    score: Mapped[float] = mapped_column(Float, default=70.0)
    score_puntualidad: Mapped[float] = mapped_column(Float, default=70.0)
    score_etiquetado: Mapped[float] = mapped_column(Float, default=70.0)
    score_documental: Mapped[float] = mapped_column(Float, default=70.0)

    # Carga pre-paletizada + score >= 90 habilitan la cita corta de 45 min.
    pre_paletizado: Mapped[bool] = mapped_column(default=False)
    no_shows: Mapped[int] = mapped_column(Integer, default=0)
    activo: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        return f"<Proveedor {self.clave} score={self.score:.0f}>"