"""Esquemas de generación y verificación de etiquetas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SolicitudEtiqueta(BaseModel):
    """Un bulto a etiquetar. Un bulto, un solo SKU (regla de pureza)."""

    id_bulto: str = Field(min_length=3, max_length=24, examples=["B00412"])
    orden_compra: str = Field(min_length=3, max_length=32, examples=["OC-88213"])
    proveedor: str = Field(min_length=3, max_length=16, examples=["PRV-0147"])
    sucursal: str = Field(min_length=3, max_length=16, examples=["SUC-14"])
    sku: str = Field(min_length=1, max_length=32, examples=["SKU-993201"])
    cantidad: int = Field(gt=0, le=100000)
    peso_kg: float = Field(gt=0, le=1000)
    volumen_m3: float = Field(gt=0, le=30)


class SolicitudLote(BaseModel):
    """Lote de etiquetas de una misma OC, como las pide el portal."""

    bultos: list[SolicitudEtiqueta] = Field(min_length=1, max_length=1000)


class RespuestaEtiqueta(BaseModel):
    """La cadena del QR más los parámetros de impresión de la etiqueta 4x6."""

    id_bulto: str
    cadena_qr: str
    longitud_cadena: int
    version_qr: int = 7
    nivel_correccion: str = "M"
    modulo_mm: float = 0.5
    medida_pulgadas: str = "4x6"


class RespuestaLote(BaseModel):
    total: int
    etiquetas: list[RespuestaEtiqueta]


class SolicitudVerificacion(BaseModel):
    """Lo que manda el handheld (o el simulador) al verificar una etiqueta."""

    cadena_qr: str = Field(min_length=1, max_length=200)


class RespuestaVerificacion(BaseModel):
    valida: bool
    motivo: str | None = None
    id_bulto: str | None = None
    orden_compra: str | None = None
    proveedor: str | None = None
    sucursal: str | None = None
    sku: str | None = None
    cantidad: int | None = None
    peso_kg: float | None = None
    volumen_m3: float | None = None


class SolicitudReimpresion(BaseModel):
    """Reimpresión controlada en recibo: etiqueta ilegible, mojada o rota."""

    id_bulto: str = Field(min_length=3, max_length=24)
    motivo: str = Field(min_length=5, max_length=200)
    operador: str = Field(min_length=3, max_length=64)


class RespuestaReimpresion(BaseModel):
    folio_reimpresion: str
    id_bulto: str
    cadena_qr: str
    zpl: str
