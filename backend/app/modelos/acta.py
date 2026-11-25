"""Actas: el rastro auditable de toda excepción del CEDIS."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base, MixinFechas

# JSONB en PostgreSQL, JSON en SQLite para que las pruebas corran igual.
TipoJSON = JSON().with_variant(JSONB(), "postgresql")


class TipoActa(StrEnum):
    """Cada excepción del reto tiene su acta; ninguna queda en silencio."""

    FALTANTE = "FALTANTE"
    EXCEDENTE = "EXCEDENTE"
    SKU_NO_SOLICITADO = "SKU_NO_SOLICITADO"
    FIRMA_INVALIDA = "FIRMA_INVALIDA"
    SIN_REGISTRO = "SIN_REGISTRO"
    BULTO_DANADO = "BULTO_DANADO"
    CORRECCION_SUCURSAL = "CORRECCION_SUCURSAL"
    REIMPRESION = "REIMPRESION"
    EXCEPCION_ANTIGUEDAD = "EXCEPCION_ANTIGUEDAD"
    RECEPCION = "RECEPCION"


class Acta(Base, MixinFechas):
    """Documento generado por el sistema, no capturado a mano.

    `cuerpo` guarda el detalle estructurado (líneas de faltante, importes,
    evidencia fotográfica, decisión de liberación) para reimprimir el PDF sin
    recalcular nada.
    """

    __tablename__ = "acta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folio: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(32), index=True)

    cita_id: Mapped[int | None] = mapped_column(ForeignKey("cita.id"), index=True)
    orden_compra_id: Mapped[int | None] = mapped_column(
        ForeignKey("orden_compra.id"), index=True
    )
    embarque_id: Mapped[int | None] = mapped_column(ForeignKey("embarque.id"), index=True)
    bulto_id: Mapped[int | None] = mapped_column(ForeignKey("bulto.id"), index=True)

    importe: Mapped[float] = mapped_column(Float, default=0.0)
    cuerpo: Mapped[dict[str, Any]] = mapped_column(TipoJSON, default=dict)
    # Las excepciones de antigüedad se reportan a gerencia: aquí se marca.
    reportada: Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:
        return f"<Acta {self.folio} {self.tipo}>"
