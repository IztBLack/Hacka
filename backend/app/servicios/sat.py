"""Validación del UUID del CFDI 4.0 contra el SAT (stub).

Por qué existe: el folio único de la OC es el UUID del CFDI, no un
consecutivo interno. Validarlo antes de que el camión entre al patio detecta
factura cancelada o apócrifa a tiempo.

Por qué es un stub: el servicio de consulta del SAT es SOAP, requiere
certificado y no puede ser dependencia de una prueba. El contrato queda fijo
aquí y el adaptador real se enchufa sin tocar quien lo llama.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.config import settings

__all__ = ["EstadoCFDI", "ResultadoValidacionSAT", "ValidadorSAT", "ValidadorSATStub"]

PATRON_UUID = re.compile(
    r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$", re.IGNORECASE
)


class EstadoCFDI(StrEnum):
    """Estados que devuelve la consulta del SAT."""

    VIGENTE = "VIGENTE"
    CANCELADO = "CANCELADO"
    NO_ENCONTRADO = "NO_ENCONTRADO"
    FORMATO_INVALIDO = "FORMATO_INVALIDO"
    NO_VALIDADO = "NO_VALIDADO"


@dataclass(frozen=True, slots=True)
class ResultadoValidacionSAT:
    """Veredicto de la consulta. `vigente` es lo único que mira el motor de citas."""

    uuid: str
    estado: EstadoCFDI
    vigente: bool
    detalle: str

    @property
    def bloquea_cita(self) -> bool:
        """Un CFDI cancelado o inexistente no debe poder reservar andén."""
        return self.estado in (EstadoCFDI.CANCELADO, EstadoCFDI.NO_ENCONTRADO)


class ValidadorSAT:
    """Interfaz que consume el motor de citas."""

    def validar(self, uuid: str) -> ResultadoValidacionSAT:  # pragma: no cover
        raise NotImplementedError


class ValidadorSATStub(ValidadorSAT):
    """Implementación de desarrollo: valida formato, no consulta al SAT.

    Con `SAT_VALIDACION_ACTIVA=false` (el default) solo revisa el formato del
    UUID y marca el resultado como NO_VALIDADO, para que nadie confunda este
    stub con una validación real. Con la bandera en true, falla en claro
    mientras no se configure el adaptador SOAP con certificado.
    """

    def validar(self, uuid: str) -> ResultadoValidacionSAT:
        if not PATRON_UUID.match(uuid or ""):
            return ResultadoValidacionSAT(
                uuid=uuid,
                estado=EstadoCFDI.FORMATO_INVALIDO,
                vigente=False,
                detalle="el UUID no cumple el formato de 36 caracteres del CFDI 4.0",
            )
        if settings.sat_validacion_activa:
            raise NotImplementedError(
                "La validación real contra el SAT requiere el adaptador SOAP con "
                "certificado (ver Fase 1 del roadmap). Desactive "
                "SAT_VALIDACION_ACTIVA para operar con el stub."
            )
        return ResultadoValidacionSAT(
            uuid=uuid.upper(),
            estado=EstadoCFDI.NO_VALIDADO,
            vigente=True,
            detalle="formato correcto; validación contra el SAT desactivada",
        )


def obtener_validador() -> ValidadorSAT:
    """Dependencia de FastAPI: se sustituye por el adaptador real en producción."""
    return ValidadorSATStub()
