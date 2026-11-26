"""Esquemas de agendamiento de citas."""

from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, Field, field_validator


class SolicitudDuracion(BaseModel):
    """Consulta de la duración que el sistema asigna a una descarga."""

    n_bultos: int = Field(ge=0, le=5000, description="Bultos declarados en el desglose")


class RespuestaDuracion(BaseModel):
    n_bultos: int
    duracion_minutos: int
    formula: str = "max(60, ceil(12 + 0.9 x n_bultos)) en bloques de 30 min"


class SolicitudSlots(BaseModel):
    """Consulta de disponibilidad de andén para una fecha."""

    fecha: date
    n_bultos: int = Field(ge=0, le=5000)
    incluir_anden_flex: bool = True


class SlotLibre(BaseModel):
    anden: int
    hora_inicio: time
    hora_fin: time
    es_anden_flex: bool


class RespuestaSlots(BaseModel):
    fecha: date
    duracion_minutos: int
    capacidad_dia: int
    total_slots: int
    slots: list[SlotLibre]


class SolicitudCita(BaseModel):
    """Reserva de cita. El proveedor elige andén y hora, no duración."""

    proveedor: str = Field(min_length=3, max_length=16, examples=["PRV-0147"])
    orden_compra: str = Field(min_length=3, max_length=32, examples=["OC-88213"])
    uuid_cfdi: str | None = Field(default=None, max_length=36)
    fecha: date
    anden: int = Field(ge=1, le=5)
    hora_inicio: time
    n_bultos: int = Field(ge=1, le=5000)

    @field_validator("uuid_cfdi")
    @classmethod
    def validar_formato_uuid(cls, valor: str | None) -> str | None:
        """El folio único es el UUID del CFDI 4.0: 36 caracteres con guiones."""
        if valor is None:
            return None
        if len(valor) != 36 or valor.count("-") != 4:
            raise ValueError("el UUID del CFDI no tiene el formato esperado")
        return valor.upper()


class RespuestaCita(BaseModel):
    folio: str
    proveedor: str
    orden_compra: str
    fecha: date
    anden: int
    hora_inicio: time
    hora_fin: time
    duracion_minutos: int
    estado: str
    cfdi_validado: bool = False

    model_config = {"from_attributes": True}


class ResumenCita(BaseModel):
    """Una cita como la ven las demás pantallas (etiquetas, handheld)."""

    folio: str
    proveedor: str
    razon_social: str
    orden_compra: str
    fecha: date
    anden: int
    hora_inicio: time
    hora_fin: time
    n_bultos: int
    estado: str


class BultoEtiqueta(BaseModel):
    """Lo que se imprime en una etiqueta 4" x 6"."""

    id_bulto: str
    secuencia: int
    sku: str
    descripcion: str
    sucursal: str
    nombre_sucursal: str
    cantidad: int
    peso_kg: float
    volumen_m3: float
    estado: str
    cadena_qr: str


class RespuestaEtiquetasCita(BaseModel):
    cita: ResumenCita
    total: int
    bultos: list[BultoEtiqueta]


class RespuestaCapacidad(BaseModel):
    """Diagnóstico de capacidad: el hallazgo que no se puede comprar."""

    andenes_recibo: int
    horas_operacion: int
    capacidad_sin_anden_flex: int
    capacidad_con_anden_flex: int
    citas_requeridas: int
    deficit_sin_flex: int
    alcanza_con_flex: bool
