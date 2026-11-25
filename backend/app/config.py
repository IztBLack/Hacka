"""Configuración del nodo edge, leída del entorno con pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes del servicio. Todo valor sensible llega por variable de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    nombre_app: str = "CEDIS API"
    version_app: str = "0.1.0"
    depurar: bool = False

    # PostgreSQL 16 en el nodo edge; SQLite en las pruebas.
    url_base_datos: str = "postgresql+psycopg://cedis:cedis@localhost:5432/cedis"
    url_redis: str = "redis://localhost:6379/0"

    # Llave HMAC de las etiquetas. En producción se monta como secreto, nunca
    # se versiona: si se filtra, cualquiera imprime etiquetas válidas.
    llave_firma_qr: str = Field(default="cambiar-esta-llave-en-produccion")

    # Parámetros operativos del CEDIS (ver propuesta v2).
    andenes_recibo: int = 4
    anden_flex: int = 5
    horas_operacion: int = 10
    horas_anden_flex: int = 5
    horas_antiguedad_limite: float = 36.0
    umbral_cross_dock: float = 0.70

    # Validación de UUID del CFDI 4.0 contra el SAT (stub en este esqueleto).
    sat_url_consulta: str = "https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc"
    sat_validacion_activa: bool = False

    origenes_permitidos: list[str] = ["http://localhost:5173"]

    @property
    def llave_qr_bytes(self) -> bytes:
        """La llave en bytes, como la espera el dominio."""
        return self.llave_firma_qr.encode("utf-8")


@lru_cache
def obtener_settings() -> Settings:
    """Settings en caché: se leen una vez por proceso."""
    return Settings()


settings = obtener_settings()
