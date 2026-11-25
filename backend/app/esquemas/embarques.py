"""Esquemas de liberación de embarque y Relación de Embarque."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SolicitudLiberacion(BaseModel):
    """Liberación de un embarque desde el tablero."""

    sucursal: str = Field(min_length=3, max_length=16)
    tarimas: list[str] = Field(min_length=1, max_length=12, description="Folios de tarima")
    peso_kg: float = Field(gt=0, le=100000)
    volumen_m3: float = Field(gt=0, le=300)
    antiguedad_horas: float = Field(ge=0, le=1000)
    sello_seguridad: str | None = Field(default=None, max_length=32)
    km_salida: int | None = Field(default=None, ge=0)
    operador: str | None = Field(default=None, max_length=100)
    placas: str | None = Field(default=None, max_length=16)


class RespuestaLiberacion(BaseModel):
    folio: str
    sucursal: str
    clase_unidad: str | None
    motivo_liberacion: str
    liberado: bool
    requiere_acta: bool
    folio_acta: str | None = None
    ocupacion: float | None = None
    detalle: str
    liberado_en: datetime | None = None


class DatosCartaPorte(BaseModel):
    """Lo que el transportista necesita para su CFDI con complemento 3.1.

    Obligatorio desde el 17-jul-2024 para autotransporte federal.
    """

    permiso_sict: str | None = None
    configuracion_vehicular: str | None = None
    placas: str | None = None
    aseguradora: str | None = None
    poliza: str | None = None
    completo: bool = False


class RespuestaRelacionEmbarque(BaseModel):
    """Relación de Embarque: folio, QR maestro, sello, kilometraje y firma."""

    folio: str
    sucursal: str
    clase_unidad: str | None
    tarimas: list[str]
    peso_kg: float
    volumen_m3: float
    ocupacion: float
    qr_maestro: str
    sello_seguridad: str | None
    km_salida: int | None
    operador: str | None
    carta_porte: DatosCartaPorte
    generado_en: datetime


class SolicitudRecepcionSucursal(BaseModel):
    """Conciliación en destino: un escaneo del QR maestro."""

    qr_maestro: str = Field(min_length=1, max_length=200)
    sucursal: str = Field(min_length=3, max_length=16)
    tarimas_recibidas: list[str] = Field(default_factory=list)


class RespuestaRecepcionSucursal(BaseModel):
    folio: str
    conciliado: bool
    tarimas_esperadas: int
    tarimas_recibidas: int
    faltantes: list[str] = []
