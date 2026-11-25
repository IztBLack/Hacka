"""Motor, sesión y Base declarativa de SQLAlchemy 2.0.

Se usa la API sincrónica a propósito: el nodo edge es un solo servidor con
PostgreSQL local y los endpoints se declaran con `def`, así FastAPI los corre
en su pool de hilos. Mezclar sesión sincrónica con `async def` sería bloquear
el event loop, que es el error clásico.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import settings


def _kwargs_motor(url: str) -> dict:
    """SQLite (pruebas) necesita banderas que PostgreSQL no acepta."""
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20}


motor = create_engine(
    settings.url_base_datos, echo=settings.depurar, **_kwargs_motor(settings.url_base_datos)
)

FabricaSesion = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base declarativa común a todos los modelos."""


def ahora_utc() -> datetime:
    """Marca de tiempo en UTC: el CEDIS y la nube tienen que coincidir."""
    return datetime.now(timezone.utc)


class MixinFechas:
    """Columnas de auditoría que llevan todas las tablas."""

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=ahora_utc, nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=ahora_utc, onupdate=ahora_utc, nullable=False
    )


def obtener_sesion() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: una sesión por request, con rollback si truena."""
    with FabricaSesion() as sesion:
        try:
            yield sesion
        except Exception:
            sesion.rollback()
            raise
