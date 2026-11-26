"""Esquemas del tablero de consolidación."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UnidadSalida(BaseModel):
    """Clase de unidad con sus tres límites reales."""

    clase: str
    posiciones: int
    minimo_90: int
    peso_max_kg: float
    volumen_max_m3: float
    costo_viaje: float


class SolicitudEvaluacion(BaseModel):
    """Estado acumulado de una sucursal para pasarlo por el semáforo."""

    sucursal: str = Field(min_length=3, max_length=16, examples=["SUC-14"])
    tarimas_acumuladas: int = Field(ge=0, le=100)
    peso_kg: float = Field(ge=0, le=100000)
    volumen_m3: float = Field(ge=0, le=300)
    antiguedad_horas: float = Field(ge=0, le=1000)


class RespuestaEvaluacion(BaseModel):
    """Veredicto del semáforo, con el motivo explícito."""

    sucursal: str
    liberar: bool
    motivo: str  # REGLA_90 | EXCEPCION_ANTIGUEDAD | ACUMULANDO
    requiere_acta: bool
    detalle: str
    unidad: UnidadSalida | None = None
    ocupacion: float | None = None


class SemaforoSucursal(BaseModel):
    """Una fila del tablero que el jefe de embarques lee de pie, de lejos."""

    sucursal: str
    tarimas_acumuladas: int
    antiguedad_horas: float
    liberar: bool
    motivo: str
    clase_unidad: str | None = None
    ocupacion: float | None = None
    alerta_antiguedad: bool = False
    peso_kg: float = 0.0
    volumen_m3: float = 0.0


class RespuestaTablero(BaseModel):
    total_sucursales: int
    liberables: int
    en_alerta_antiguedad: int
    filas: list[SemaforoSucursal]


class RespuestaCatalogo(BaseModel):
    """Catálogo de la flota y los parámetros de la tarima."""

    unidades: list[UnidadSalida]
    volumen_tarima_m3: float
    peso_max_tarima_kg: float
    ocupacion_minima: float
    horas_antiguedad_limite: float
