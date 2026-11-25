"""Firma y verificación del QR de bulto (lógica pura, sin framework).

El QR de la etiqueta 4x6" lleva los datos del bulto más una firma HMAC-SHA256.
Sin firma válida el handheld rechaza la etiqueta aunque los datos sean
correctos: eso mata la etiqueta fotocopiada y la reimpresa fuera del sistema.

Formato de la cadena (10 campos separados por "|"):

    v1|B00412|OC-88213|PRV-0147|SUC-14|SKU-993201|24|18.4|0.42|K7QX4M2A
    ^  ^      ^        ^        ^      ^          ^  ^    ^    ^
    |  bulto  OC       prov.    suc.   SKU      cant peso vol  firma

Nota de implementación: la propuesta especifica "HMAC truncado a 8 bytes en
base32 sin relleno". Ocho bytes en base32 son 13 caracteres; el ejemplo del
documento muestra 8 caracteres (que serían 5 bytes). Aquí manda la regla
criptográfica (8 bytes = 64 bits de firma), por lo que la firma real mide
13 caracteres. `verificar` no asume longitud: compara contra el HMAC recalculado.
"""

from __future__ import annotations

import base64
import hmac
from dataclasses import dataclass
from hashlib import sha256

__all__ = [
    "ErrorQR",
    "FirmaInvalida",
    "FormatoInvalido",
    "PayloadBulto",
    "VERSION_QR",
    "BYTES_FIRMA",
    "firmar",
    "verificar",
]

VERSION_QR = "v1"
SEPARADOR = "|"
CAMPOS_ESPERADOS = 10
BYTES_FIRMA = 8  # 64 bits: suficiente contra falsificación casual de etiquetas


class ErrorQR(Exception):
    """Error base de la lectura de un QR de bulto."""


class FormatoInvalido(ErrorQR):
    """La cadena no tiene la estructura esperada (campos, tipos o versión)."""


class FirmaInvalida(ErrorQR):
    """La estructura es correcta pero la firma no corresponde a la llave."""


@dataclass(frozen=True, slots=True)
class PayloadBulto:
    """Datos que viajan impresos en el QR de un bulto.

    Regla de pureza del reto: un bulto contiene un solo SKU, por eso aquí
    hay un único `sku` y una única `cantidad`.
    """

    id_bulto: str
    orden_compra: str
    proveedor: str
    sucursal: str
    sku: str
    cantidad: int
    peso_kg: float
    volumen_m3: float
    version: str = VERSION_QR

    def __post_init__(self) -> None:
        if self.cantidad <= 0:
            raise ValueError("la cantidad del bulto debe ser positiva")
        if self.peso_kg <= 0:
            raise ValueError("el peso del bulto debe ser positivo")
        if self.volumen_m3 <= 0:
            raise ValueError("el volumen del bulto debe ser positivo")
        for campo in (self.id_bulto, self.orden_compra, self.proveedor, self.sucursal, self.sku):
            if not campo or SEPARADOR in campo:
                raise ValueError(f"campo inválido en el payload: {campo!r}")

    def cadena_sin_firma(self) -> str:
        """Los 9 campos de datos, en el orden exacto que se firma."""
        return SEPARADOR.join(
            (
                self.version,
                self.id_bulto,
                self.orden_compra,
                self.proveedor,
                self.sucursal,
                self.sku,
                str(self.cantidad),
                _formatear_decimal(self.peso_kg),
                _formatear_decimal(self.volumen_m3),
            )
        )


def _formatear_decimal(valor: float) -> str:
    """Formatea pesos y volúmenes sin ceros de relleno (18.4, no 18.400000).

    La representación tiene que ser estable: la firma se calcula sobre el
    texto, así que 18.40 y 18.4 no pueden producir firmas distintas.
    """
    texto = f"{float(valor):.6f}".rstrip("0").rstrip(".")
    return texto or "0"


def _firma_de(cadena_sin_firma: str, llave: bytes) -> str:
    """HMAC-SHA256 truncado a 8 bytes, en base32 sin relleno y en mayúsculas."""
    if not llave:
        raise ValueError("la llave de firma no puede estar vacía")
    digest = hmac.new(llave, cadena_sin_firma.encode("utf-8"), sha256).digest()
    crudo = base64.b32encode(digest[:BYTES_FIRMA]).decode("ascii")
    return crudo.rstrip("=").upper()


def firmar(payload: PayloadBulto, llave: bytes) -> str:
    """Devuelve la cadena completa lista para codificarse en el QR."""
    base = payload.cadena_sin_firma()
    return f"{base}{SEPARADOR}{_firma_de(base, llave)}"


def verificar(cadena: str, llave: bytes) -> PayloadBulto:
    """Valida estructura y firma; devuelve el payload o lanza excepción.

    Lanza `FormatoInvalido` si la cadena no es interpretable y `FirmaInvalida`
    si los datos son legibles pero la firma no coincide con la llave.
    """
    if not isinstance(cadena, str) or not cadena:
        raise FormatoInvalido("la cadena del QR está vacía")

    partes = cadena.strip().split(SEPARADOR)
    if len(partes) != CAMPOS_ESPERADOS:
        raise FormatoInvalido(
            f"se esperaban {CAMPOS_ESPERADOS} campos y llegaron {len(partes)}"
        )

    version, id_bulto, oc, proveedor, sucursal, sku, cantidad, peso, volumen, firma = partes
    if version != VERSION_QR:
        raise FormatoInvalido(f"versión de etiqueta no soportada: {version!r}")
    if not firma:
        raise FormatoInvalido("la etiqueta no trae firma")

    try:
        payload = PayloadBulto(
            id_bulto=id_bulto,
            orden_compra=oc,
            proveedor=proveedor,
            sucursal=sucursal,
            sku=sku,
            cantidad=int(cantidad),
            peso_kg=float(peso),
            volumen_m3=float(volumen),
            version=version,
        )
    except ValueError as exc:
        raise FormatoInvalido(f"campos numéricos inválidos: {exc}") from exc

    esperada = _firma_de(payload.cadena_sin_firma(), llave)
    # compare_digest evita filtrar información por tiempo de comparación.
    if not hmac.compare_digest(esperada, firma.strip().upper()):
        raise FirmaInvalida(f"firma no emitida por el sistema para {id_bulto}")

    return payload
