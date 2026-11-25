"""Esquemas de recepción en andén."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LineaOCEntrada(BaseModel):
    """Una línea de la OC tal como la descarga el handheld al confirmar la cita."""

    sku: str = Field(min_length=1, max_length=32)
    cantidad_solicitada: int = Field(gt=0)
    precio_unitario: float = Field(default=0.0, ge=0)


class BultoEsperadoEntrada(BaseModel):
    """Un bulto declarado por el proveedor en el desglose de la factura."""

    id_bulto: str = Field(min_length=3, max_length=24)
    sku: str = Field(min_length=1, max_length=32)
    cantidad: int = Field(gt=0)


class SolicitudEscaneo(BaseModel):
    """Evento de escaneo. El UUID lo genera el equipo: es la llave de idempotencia."""

    cadena_qr: str = Field(min_length=1, max_length=200)
    uuid_evento: str = Field(min_length=36, max_length=36)
    cita: str = Field(min_length=3, max_length=32)
    dispositivo: str | None = Field(default=None, max_length=32)
    operador: str | None = Field(default=None, max_length=64)
    ocurrido_en: datetime | None = None


class DestinoSalida(BaseModel):
    tipo: str
    ubicacion: str
    motivo: str


class RespuestaEscaneo(BaseModel):
    """Lo que el handheld muestra al operador, en una sola pantalla."""

    desenlace: str
    id_bulto: str
    motivo: str
    sku: str | None = None
    cantidad: int = 0
    destino: DestinoSalida | None = None
    acumulado_sku: int | None = None


class LineaFaltanteSalida(BaseModel):
    sku: str
    cantidad_solicitada: int
    cantidad_recibida: int
    cantidad_faltante: int
    importe: float


class RespuestaCierreCita(BaseModel):
    """Cierre de cita: aquí nace el Acta de Faltante y la nota de crédito."""

    cita: str
    bultos_aceptados: int
    bultos_rechazados: int
    hay_faltantes: bool
    folio_acta: str | None = None
    importe_nota_credito: float = 0.0
    faltantes: list[LineaFaltanteSalida] = []


class SolicitudSimulacion(BaseModel):
    """Simulación completa de una recepción (prototipo del handheld)."""

    lineas: list[LineaOCEntrada] = Field(min_length=1)
    esperados: list[BultoEsperadoEntrada] = Field(min_length=1)
    escaneos: list[str] = Field(min_length=1, description="Cadenas de QR a escanear")
    ocupacion_embarque_abierto: float | None = Field(default=None, ge=0, le=2)
    ubicacion_rack: str | None = None


class RespuestaSimulacion(BaseModel):
    resultados: list[RespuestaEscaneo]
    recibidos_por_sku: dict[str, int]
    faltantes: list[LineaFaltanteSalida]
    importe_nota_credito: float
