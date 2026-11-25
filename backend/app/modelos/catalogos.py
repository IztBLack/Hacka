"""Catálogos maestros del CEDIS: sucursales, andenes, ubicaciones y usuarios."""

from datetime import time
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Time, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, MixinFechas


class Sucursal(Base, MixinFechas):
    """Sucursal destino; cada una tiene un rack home fijo (1..32)."""

    __tablename__ = "sucursal"
    __table_args__ = (
        CheckConstraint("rack_home BETWEEN 1 AND 32", name="ck_sucursal_rack_home"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(16), unique=True)  # ej. SUC-14
    nombre: Mapped[str] = mapped_column(String(120))
    rack_home: Mapped[int] = mapped_column(unique=True)
    km_ruta: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    activa: Mapped[bool] = mapped_column(default=True, server_default=text("true"))


class Anden(Base, MixinFechas):
    """Andén físico. `numero` es el valor que usa `Cita.anden`."""

    __tablename__ = "anden"
    __table_args__ = (
        CheckConstraint("numero BETWEEN 1 AND 7", name="ck_anden_numero"),
        CheckConstraint("tipo IN ('recibo', 'embarque', 'flex')", name="ck_anden_tipo"),
        CheckConstraint(
            "recibo_desde IS NULL OR recibo_hasta IS NULL OR recibo_desde < recibo_hasta",
            name="ck_anden_ventana_recibo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(unique=True)
    tipo: Mapped[str] = mapped_column(String(10))
    recibo_desde: Mapped[time | None] = mapped_column(Time, nullable=True)
    recibo_hasta: Mapped[time | None] = mapped_column(Time, nullable=True)


class Ubicacion(Base, MixinFechas):
    """Posición física: rack home por sucursal, zona flex o andén de salida."""

    __tablename__ = "ubicacion"
    __table_args__ = (
        CheckConstraint(
            "zona IN ('rack_home', 'flex', 'anden_salida')", name="ck_ubicacion_zona"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String(32), unique=True)  # ej. SUC14-N2-P05
    sucursal_id: Mapped[int | None] = mapped_column(
        ForeignKey("sucursal.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    zona: Mapped[str] = mapped_column(String(16))
    ocupada: Mapped[bool] = mapped_column(default=False, server_default=text("false"))


class Usuario(Base, MixinFechas):
    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint(
            "rol IN ('operador', 'jefe_recibo', 'jefe_embarques', 'comprador', 'admin')",
            name="ck_usuario_rol",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(255), unique=True)
    rol: Mapped[str] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
