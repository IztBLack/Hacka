"""Recepción de bultos en el andén (lógica pura).

Aquí vive lo que el handheld evalúa contra su copia local de la OC, sin red:
firma del QR, registro en el desglose, SKU solicitado, excedente e
idempotencia. También el flujo de faltantes que la v1 no tenía y la regla de
cross-dock que la v1 dejó en una palabra.

Nada de este módulo conoce FastAPI ni SQLAlchemy: el adaptador carga el estado,
llama a estas funciones y persiste el resultado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.dominio.qr import ErrorQR, PayloadBulto, verificar

__all__ = [
    "Desenlace",
    "TipoDestino",
    "LineaOC",
    "BultoEsperado",
    "Destino",
    "ResultadoEscaneo",
    "EstadoRecepcion",
    "Faltante",
    "ActaFaltante",
    "OCUPACION_CROSS_DOCK",
    "evaluar_bulto",
    "calcular_faltantes",
    "decidir_destino",
]

# A partir de este llenado del embarque abierto vale la pena el cross-dock:
# el bulto va directo al andén de salida y se ahorran 2 movimientos de
# montacargas y 1 posición de rack.
OCUPACION_CROSS_DOCK = 0.70


class Desenlace(StrEnum):
    """Los desenlaces posibles de un escaneo en el andén de recibo."""

    ACEPTADO = "ACEPTADO"
    RECHAZADO_EXCEDENTE = "RECHAZADO_EXCEDENTE"
    RECHAZADO_SKU_NO_SOLICITADO = "RECHAZADO_SKU_NO_SOLICITADO"
    RECHAZADO_FIRMA_INVALIDA = "RECHAZADO_FIRMA_INVALIDA"
    RECHAZADO_SIN_REGISTRO = "RECHAZADO_SIN_REGISTRO"
    DUPLICADO = "DUPLICADO"


class TipoDestino(StrEnum):
    """Hacia dónde manda el handheld el bulto aceptado."""

    CROSS_DOCK = "CROSS_DOCK"
    RACK = "RACK"


@dataclass(frozen=True, slots=True)
class LineaOC:
    """Una línea de la orden de compra: un SKU y lo que se le pidió al proveedor."""

    sku: str
    cantidad_solicitada: int
    precio_unitario: float = 0.0

    def __post_init__(self) -> None:
        if self.cantidad_solicitada <= 0:
            raise ValueError(f"cantidad solicitada inválida para {self.sku}")
        if self.precio_unitario < 0:
            raise ValueError(f"precio unitario negativo para {self.sku}")


@dataclass(frozen=True, slots=True)
class BultoEsperado:
    """Un bulto declarado por el proveedor en el desglose de la factura."""

    id_bulto: str
    sku: str
    cantidad: int


@dataclass(frozen=True, slots=True)
class Destino:
    """Instrucción de acomodo que el handheld muestra al operador."""

    tipo: TipoDestino
    ubicacion: str
    motivo: str


@dataclass(frozen=True, slots=True)
class ResultadoEscaneo:
    """Veredicto de un escaneo. Es el registro que se sincroniza a la nube."""

    desenlace: Desenlace
    id_bulto: str
    motivo: str
    sku: str | None = None
    cantidad: int = 0
    destino: Destino | None = None

    @property
    def aceptado(self) -> bool:
        return self.desenlace is Desenlace.ACEPTADO

    @property
    def rechazado(self) -> bool:
        """DUPLICADO no es rechazo: es el mismo bulto que ya fue resuelto."""
        return self.desenlace.name.startswith("RECHAZADO")


@dataclass(slots=True)
class EstadoRecepcion:
    """Acumulado de la recepción de una cita.

    Es el único objeto mutable del dominio y se mantiene a propósito: el
    handheld lo lleva en memoria durante la descarga y lo persiste al cerrar.
    """

    lineas: dict[str, LineaOC]
    esperados: dict[str, BultoEsperado]
    recibidos: dict[str, int] = field(default_factory=dict)
    escaneados: dict[str, Desenlace] = field(default_factory=dict)

    @classmethod
    def desde_listas(
        cls, lineas: list[LineaOC], esperados: list[BultoEsperado]
    ) -> "EstadoRecepcion":
        """Constructor cómodo para el adaptador que lee de la base."""
        return cls(
            lineas={linea.sku: linea for linea in lineas},
            esperados={bulto.id_bulto: bulto for bulto in esperados},
        )

    def cantidad_recibida(self, sku: str) -> int:
        return self.recibidos.get(sku, 0)

    def registrar(self, resultado: ResultadoEscaneo) -> None:
        """Aplica el resultado al acumulado. Solo ACEPTADO suma cantidad.

        La clave de la idempotencia: el id del bulto queda marcado con su
        desenlace, así un segundo escaneo del mismo QR no vuelve a sumar.
        """
        if resultado.desenlace is Desenlace.DUPLICADO:
            return
        self.escaneados[resultado.id_bulto] = resultado.desenlace
        if resultado.aceptado and resultado.sku is not None:
            self.recibidos[resultado.sku] = (
                self.cantidad_recibida(resultado.sku) + resultado.cantidad
            )


@dataclass(frozen=True, slots=True)
class Faltante:
    """Delta de un SKU al cerrar la cita."""

    sku: str
    cantidad_solicitada: int
    cantidad_recibida: int
    cantidad_faltante: int
    importe: float


@dataclass(frozen=True, slots=True)
class ActaFaltante:
    """Acta de faltante: cierra la OC parcialmente y dispara la nota de crédito."""

    lineas: tuple[Faltante, ...]
    importe_nota_credito: float

    @property
    def hay_faltantes(self) -> bool:
        return bool(self.lineas)


def decidir_destino(
    sucursal: str,
    ocupacion_embarque_abierto: float | None = None,
    ubicacion_rack: str | None = None,
    umbral_cross_dock: float = OCUPACION_CROSS_DOCK,
) -> Destino:
    """Cross-dock si la sucursal ya tiene embarque abierto al >= 70%.

    Si no, acomodo dirigido a la ubicación de rack que indique el sistema
    (o a la zona flex de desborde cuando el rack home está lleno).
    """
    if ocupacion_embarque_abierto is not None and ocupacion_embarque_abierto >= umbral_cross_dock:
        return Destino(
            tipo=TipoDestino.CROSS_DOCK,
            ubicacion=f"ANDEN-SALIDA/{sucursal}",
            motivo=(
                f"embarque abierto de {sucursal} al "
                f"{ocupacion_embarque_abierto * 100:.0f}% "
                f"(>= {umbral_cross_dock * 100:.0f}%)"
            ),
        )
    if ubicacion_rack:
        motivo = "sin embarque abierto elegible: acomodo dirigido a rack"
        if ocupacion_embarque_abierto is not None:
            motivo = (
                f"embarque abierto al {ocupacion_embarque_abierto * 100:.0f}%, "
                f"debajo del {umbral_cross_dock * 100:.0f}%: acomodo a rack"
            )
        return Destino(tipo=TipoDestino.RACK, ubicacion=ubicacion_rack, motivo=motivo)
    return Destino(
        tipo=TipoDestino.RACK,
        ubicacion=f"FLEX/{sucursal}",
        motivo="sin ubicación de rack disponible: zona flex de desborde",
    )


def evaluar_bulto(
    cadena_qr: str,
    llave: bytes,
    estado: EstadoRecepcion,
    ocupacion_embarque_abierto: float | None = None,
    ubicacion_rack: str | None = None,
    aplicar: bool = True,
) -> ResultadoEscaneo:
    """Evalúa un escaneo y devuelve su desenlace.

    Orden de las validaciones (importa, y es el orden en que falla más barato):
      1. firma del QR -> RECHAZADO_FIRMA_INVALIDA (etiqueta fotocopiada);
      2. bulto ya escaneado -> DUPLICADO (idempotencia: no suma dos veces);
      3. bulto no declarado en el desglose -> RECHAZADO_SIN_REGISTRO;
      4. SKU que no está en la OC -> RECHAZADO_SKU_NO_SOLICITADO;
      5. lo acumulado más este bulto pasa lo solicitado -> RECHAZADO_EXCEDENTE;
      6. en otro caso ACEPTADO, con destino de cross-dock o rack.

    Con `aplicar=True` el resultado se registra en `estado` (es lo que hace al
    doble escaneo idempotente). Con `aplicar=False` solo simula.
    """
    try:
        payload: PayloadBulto = verificar(cadena_qr, llave)
    except ErrorQR as exc:
        # Sin firma válida no se confía ni en el id del bulto impreso, así que
        # el rechazo NO se registra en el acumulado: si el operador reimprime
        # la etiqueta con folio trazable, el bulto legítimo debe poder entrar.
        return ResultadoEscaneo(
            desenlace=Desenlace.RECHAZADO_FIRMA_INVALIDA,
            id_bulto=_id_bulto_crudo(cadena_qr),
            motivo=f"etiqueta no emitida por el sistema: {exc}",
        )

    previo = estado.escaneados.get(payload.id_bulto)
    if previo is not None:
        # Doble escaneo (o reenvío de la cola de sincronización): no suma.
        return ResultadoEscaneo(
            desenlace=Desenlace.DUPLICADO,
            id_bulto=payload.id_bulto,
            motivo=f"bulto ya procesado con desenlace {previo}",
            sku=payload.sku,
            cantidad=payload.cantidad,
        )

    esperado = estado.esperados.get(payload.id_bulto)
    if esperado is None:
        return _resolver(
            estado,
            aplicar,
            ResultadoEscaneo(
                desenlace=Desenlace.RECHAZADO_SIN_REGISTRO,
                id_bulto=payload.id_bulto,
                motivo="el bulto no aparece en el desglose de la factura",
                sku=payload.sku,
                cantidad=payload.cantidad,
            ),
        )

    linea = estado.lineas.get(payload.sku)
    if linea is None:
        return _resolver(
            estado,
            aplicar,
            ResultadoEscaneo(
                desenlace=Desenlace.RECHAZADO_SKU_NO_SOLICITADO,
                id_bulto=payload.id_bulto,
                motivo=f"el SKU {payload.sku} no está en la orden de compra",
                sku=payload.sku,
                cantidad=payload.cantidad,
            ),
        )

    acumulado = estado.cantidad_recibida(payload.sku)
    if acumulado + payload.cantidad > linea.cantidad_solicitada:
        return _resolver(
            estado,
            aplicar,
            ResultadoEscaneo(
                desenlace=Desenlace.RECHAZADO_EXCEDENTE,
                id_bulto=payload.id_bulto,
                motivo=(
                    f"excedente de {payload.sku}: "
                    f"{acumulado} + {payload.cantidad} > "
                    f"{linea.cantidad_solicitada} solicitadas"
                ),
                sku=payload.sku,
                cantidad=payload.cantidad,
            ),
        )

    destino = decidir_destino(
        sucursal=payload.sucursal,
        ocupacion_embarque_abierto=ocupacion_embarque_abierto,
        ubicacion_rack=ubicacion_rack,
    )
    return _resolver(
        estado,
        aplicar,
        ResultadoEscaneo(
            desenlace=Desenlace.ACEPTADO,
            id_bulto=payload.id_bulto,
            motivo=f"{payload.cantidad} piezas de {payload.sku} recibidas",
            sku=payload.sku,
            cantidad=payload.cantidad,
            destino=destino,
        ),
    )


def calcular_faltantes(estado: EstadoRecepcion) -> ActaFaltante:
    """Delta por SKU al cerrar la cita, con el importe de la nota de crédito.

    El reto dice que "los faltantes se detectan tarde": aquí se detectan en el
    momento del cierre, no cuando Compras revisa la factura semanas después.
    """
    lineas: list[Faltante] = []
    total = 0.0
    for sku, linea in sorted(estado.lineas.items()):
        recibida = estado.cantidad_recibida(sku)
        faltante = linea.cantidad_solicitada - recibida
        if faltante <= 0:
            continue  # completo o con excedente ya rechazado en el andén
        importe = round(faltante * linea.precio_unitario, 2)
        total += importe
        lineas.append(
            Faltante(
                sku=sku,
                cantidad_solicitada=linea.cantidad_solicitada,
                cantidad_recibida=recibida,
                cantidad_faltante=faltante,
                importe=importe,
            )
        )
    return ActaFaltante(lineas=tuple(lineas), importe_nota_credito=round(total, 2))


def _resolver(
    estado: EstadoRecepcion, aplicar: bool, resultado: ResultadoEscaneo
) -> ResultadoEscaneo:
    """Registra el resultado en el estado si se pidió aplicarlo."""
    if aplicar:
        estado.registrar(resultado)
    return resultado


def _id_bulto_crudo(cadena_qr: str) -> str:
    """Id de bulto que venía impreso, solo para la bitácora del rechazo.

    No es un dato confiable (la firma falló), por eso nunca se usa para sumar.
    """
    partes = (cadena_qr or "").split("|")
    return partes[1] if len(partes) > 1 and partes[1] else "DESCONOCIDO"
