"""Pruebas de recepción en andén: excedente, idempotencia, faltantes y destino.

Incluye la máquina de estados del bulto, porque es la regla que garantiza que
la traza de la recepción sea auditable.
"""

from __future__ import annotations

import pytest

from app.dominio.estados import (
    EstadoBulto,
    TransicionInvalida,
    aplicar_transicion,
    es_terminal,
    ruta_valida,
    transicion_valida,
)
from app.dominio.qr import PayloadBulto, firmar
from app.dominio.recepcion import (
    BultoEsperado,
    Desenlace,
    EstadoRecepcion,
    LineaOC,
    TipoDestino,
    calcular_faltantes,
    decidir_destino,
    evaluar_bulto,
)

LLAVE = b"llave-de-prueba-del-cedis"
SKU = "SKU-993201"
SOLICITADAS = 480  # 480 piezas en la OC
DECLARADOS = 481  # el proveedor declara un bulto de más en el desglose


def _qr(id_bulto: str, sku: str = SKU, cantidad: int = 1, sucursal: str = "SUC-14") -> str:
    """Etiqueta firmada por el sistema para el bulto indicado."""
    payload = PayloadBulto(
        id_bulto=id_bulto,
        orden_compra="OC-88213",
        proveedor="PRV-0147",
        sucursal=sucursal,
        sku=sku,
        cantidad=cantidad,
        peso_kg=18.4,
        volumen_m3=0.42,
    )
    return firmar(payload, LLAVE)


@pytest.fixture
def estado() -> EstadoRecepcion:
    """OC de 480 piezas de un SKU, con 481 bultos de 1 pieza declarados."""
    return EstadoRecepcion.desde_listas(
        lineas=[LineaOC(sku=SKU, cantidad_solicitada=SOLICITADAS, precio_unitario=125.50)],
        esperados=[
            BultoEsperado(id_bulto=f"B{n:05d}", sku=SKU, cantidad=1)
            for n in range(1, DECLARADOS + 1)
        ],
    )


# --- Excedente -------------------------------------------------------------


def test_el_bulto_481_de_480_se_rechaza_por_excedente(estado: EstadoRecepcion) -> None:
    for n in range(1, SOLICITADAS + 1):
        resultado = evaluar_bulto(_qr(f"B{n:05d}"), LLAVE, estado)
        assert resultado.desenlace is Desenlace.ACEPTADO, f"falló el bulto {n}"

    excedente = evaluar_bulto(_qr(f"B{DECLARADOS:05d}"), LLAVE, estado)

    assert excedente.desenlace is Desenlace.RECHAZADO_EXCEDENTE
    assert excedente.rechazado is True
    # El rechazo no contamina el acumulado: siguen siendo 480 piezas.
    assert estado.cantidad_recibida(SKU) == SOLICITADAS


def test_un_bulto_que_rebasa_por_cantidad_tambien_se_rechaza() -> None:
    """24 + 1 piezas contra 24 solicitadas: el segundo bulto no entra completo."""
    estado = EstadoRecepcion.desde_listas(
        lineas=[LineaOC(sku=SKU, cantidad_solicitada=24)],
        esperados=[
            BultoEsperado("B00001", SKU, 20),
            BultoEsperado("B00002", SKU, 20),
        ],
    )

    assert evaluar_bulto(_qr("B00001", cantidad=20), LLAVE, estado).aceptado
    segundo = evaluar_bulto(_qr("B00002", cantidad=20), LLAVE, estado)

    assert segundo.desenlace is Desenlace.RECHAZADO_EXCEDENTE
    assert estado.cantidad_recibida(SKU) == 20  # no se recibe parcial


# --- Idempotencia ----------------------------------------------------------


def test_doble_escaneo_del_mismo_bulto_no_duplica(estado: EstadoRecepcion) -> None:
    """Un reenvío de la cola de sincronización no puede sumar dos veces."""
    primero = evaluar_bulto(_qr("B00001"), LLAVE, estado)
    segundo = evaluar_bulto(_qr("B00001"), LLAVE, estado)

    assert primero.desenlace is Desenlace.ACEPTADO
    assert segundo.desenlace is Desenlace.DUPLICADO
    assert segundo.rechazado is False  # no es un rechazo, es un reenvío
    assert estado.cantidad_recibida(SKU) == 1


def test_diez_escaneos_del_mismo_bulto_siguen_sumando_uno(estado: EstadoRecepcion) -> None:
    desenlaces = [evaluar_bulto(_qr("B00007"), LLAVE, estado).desenlace for _ in range(10)]

    assert desenlaces[0] is Desenlace.ACEPTADO
    assert set(desenlaces[1:]) == {Desenlace.DUPLICADO}
    assert estado.cantidad_recibida(SKU) == 1


def test_reescanear_un_rechazado_devuelve_duplicado_sin_sumar(
    estado: EstadoRecepcion,
) -> None:
    fuera = evaluar_bulto(_qr("B99999"), LLAVE, estado)
    repetido = evaluar_bulto(_qr("B99999"), LLAVE, estado)

    assert fuera.desenlace is Desenlace.RECHAZADO_SIN_REGISTRO
    assert repetido.desenlace is Desenlace.DUPLICADO
    assert estado.cantidad_recibida(SKU) == 0


# --- Rechazos --------------------------------------------------------------


def test_firma_alterada_se_rechaza_sin_tocar_el_acumulado(
    estado: EstadoRecepcion,
) -> None:
    cadena = _qr("B00002")
    base, firma = cadena.rsplit("|", 1)
    falsificada = f"{base}|{'A' * len(firma)}"

    resultado = evaluar_bulto(falsificada, LLAVE, estado)

    assert resultado.desenlace is Desenlace.RECHAZADO_FIRMA_INVALIDA
    assert estado.cantidad_recibida(SKU) == 0
    # No se marca como escaneado: la reimpresión con folio trazable debe poder entrar.
    assert "B00002" not in estado.escaneados


def test_etiqueta_reimpresa_por_el_sistema_entra_despues_de_una_falsificada(
    estado: EstadoRecepcion,
) -> None:
    cadena = _qr("B00002")
    base, firma = cadena.rsplit("|", 1)

    evaluar_bulto(f"{base}|{'A' * len(firma)}", LLAVE, estado)
    buena = evaluar_bulto(cadena, LLAVE, estado)

    assert buena.desenlace is Desenlace.ACEPTADO
    assert estado.cantidad_recibida(SKU) == 1


def test_bulto_sin_registro_en_el_desglose_se_rechaza(estado: EstadoRecepcion) -> None:
    resultado = evaluar_bulto(_qr("B77777"), LLAVE, estado)

    assert resultado.desenlace is Desenlace.RECHAZADO_SIN_REGISTRO


def test_sku_no_solicitado_se_rechaza_aunque_el_bulto_este_declarado() -> None:
    estado = EstadoRecepcion.desde_listas(
        lineas=[LineaOC(sku=SKU, cantidad_solicitada=10)],
        esperados=[BultoEsperado("B00001", "SKU-000999", 5)],
    )

    resultado = evaluar_bulto(_qr("B00001", sku="SKU-000999", cantidad=5), LLAVE, estado)

    assert resultado.desenlace is Desenlace.RECHAZADO_SKU_NO_SOLICITADO
    assert estado.cantidad_recibida("SKU-000999") == 0


def test_la_firma_se_valida_antes_que_todo_lo_demas(estado: EstadoRecepcion) -> None:
    """Un bulto inexistente con firma mala se rechaza por la firma, no por el registro."""
    cadena = _qr("B88888")
    base, firma = cadena.rsplit("|", 1)

    resultado = evaluar_bulto(f"{base}|{'B' * len(firma)}", LLAVE, estado)

    assert resultado.desenlace is Desenlace.RECHAZADO_FIRMA_INVALIDA


def test_modo_simulacion_no_modifica_el_estado(estado: EstadoRecepcion) -> None:
    evaluar_bulto(_qr("B00001"), LLAVE, estado, aplicar=False)

    assert estado.cantidad_recibida(SKU) == 0
    assert estado.escaneados == {}


# --- Faltantes -------------------------------------------------------------


def test_faltantes_devuelven_delta_por_sku_e_importe_de_nota_de_credito() -> None:
    estado = EstadoRecepcion.desde_listas(
        lineas=[
            LineaOC(sku="SKU-A", cantidad_solicitada=100, precio_unitario=25.50),
            LineaOC(sku="SKU-B", cantidad_solicitada=40, precio_unitario=310.00),
            LineaOC(sku="SKU-C", cantidad_solicitada=10, precio_unitario=99.99),
        ],
        esperados=[
            BultoEsperado("B1", "SKU-A", 90),
            BultoEsperado("B2", "SKU-B", 40),
        ],
    )
    evaluar_bulto(_qr("B1", sku="SKU-A", cantidad=90), LLAVE, estado)
    evaluar_bulto(_qr("B2", sku="SKU-B", cantidad=40), LLAVE, estado)

    acta = calcular_faltantes(estado)

    assert acta.hay_faltantes is True
    # SKU-B llegó completo y no aparece en el acta.
    assert [linea.sku for linea in acta.lineas] == ["SKU-A", "SKU-C"]
    assert acta.lineas[0].cantidad_faltante == 10
    assert acta.lineas[0].importe == 255.00
    assert acta.lineas[1].cantidad_faltante == 10  # nunca llegó un solo bulto
    assert acta.lineas[1].importe == 999.90
    assert acta.importe_nota_credito == 1254.90


def test_sin_faltantes_el_acta_queda_vacia(estado: EstadoRecepcion) -> None:
    for n in range(1, SOLICITADAS + 1):
        evaluar_bulto(_qr(f"B{n:05d}"), LLAVE, estado)

    acta = calcular_faltantes(estado)

    assert acta.hay_faltantes is False
    assert acta.importe_nota_credito == 0.0


# --- Destino / cross-dock --------------------------------------------------


@pytest.mark.parametrize(
    "ocupacion,tipo_esperado",
    [
        (0.70, TipoDestino.CROSS_DOCK),  # el límite exacto sí cruza
        (0.90, TipoDestino.CROSS_DOCK),
        (0.6999, TipoDestino.RACK),  # un pelo abajo va a rack
        (0.0, TipoDestino.RACK),
        (None, TipoDestino.RACK),  # sin embarque abierto
    ],
    ids=["limite-70", "noventa", "abajo-del-limite", "vacio", "sin-embarque"],
)
def test_cross_dock_solo_con_embarque_abierto_al_70(
    ocupacion: float | None, tipo_esperado: TipoDestino
) -> None:
    destino = decidir_destino(
        sucursal="SUC-14",
        ocupacion_embarque_abierto=ocupacion,
        ubicacion_rack="A-04-3-02",
    )

    assert destino.tipo is tipo_esperado


def test_sin_ubicacion_de_rack_el_bulto_va_a_la_zona_flex() -> None:
    destino = decidir_destino("SUC-31", ocupacion_embarque_abierto=0.2)

    assert destino.tipo is TipoDestino.RACK
    assert destino.ubicacion == "FLEX/SUC-31"


def test_el_bulto_aceptado_trae_instruccion_de_cross_dock(
    estado: EstadoRecepcion,
) -> None:
    resultado = evaluar_bulto(
        _qr("B00001"),
        LLAVE,
        estado,
        ocupacion_embarque_abierto=0.75,
        ubicacion_rack="A-04-3-02",
    )

    assert resultado.destino is not None
    assert resultado.destino.tipo is TipoDestino.CROSS_DOCK
    assert resultado.destino.ubicacion == "ANDEN-SALIDA/SUC-14"


def test_el_bulto_rechazado_no_trae_destino(estado: EstadoRecepcion) -> None:
    resultado = evaluar_bulto(_qr("B77777"), LLAVE, estado, ubicacion_rack="A-04-3-02")

    assert resultado.destino is None


# --- Máquina de estados ----------------------------------------------------


@pytest.mark.parametrize(
    "desde,hacia",
    [
        (EstadoBulto.ETIQUETADO, EstadoBulto.EN_TRANSITO),
        (EstadoBulto.EN_TRANSITO, EstadoBulto.ESCANEADO_ANDEN),
        (EstadoBulto.ESCANEADO_ANDEN, EstadoBulto.RECIBIDO),
        (EstadoBulto.ESCANEADO_ANDEN, EstadoBulto.RECHAZADO),
        (EstadoBulto.RECIBIDO, EstadoBulto.UBICADO),
        (EstadoBulto.RECIBIDO, EstadoBulto.ASIGNADO_EMBARQUE),  # cross-dock
        (EstadoBulto.UBICADO, EstadoBulto.ASIGNADO_EMBARQUE),
        (EstadoBulto.ASIGNADO_EMBARQUE, EstadoBulto.CARGADO),
        (EstadoBulto.CARGADO, EstadoBulto.EMBARCADO),
        (EstadoBulto.EMBARCADO, EstadoBulto.RECIBIDO_SUCURSAL),
    ],
)
def test_transiciones_permitidas(desde: EstadoBulto, hacia: EstadoBulto) -> None:
    assert transicion_valida(desde, hacia) is True
    assert aplicar_transicion(desde, hacia) is hacia


@pytest.mark.parametrize(
    "desde,hacia",
    [
        (EstadoBulto.ETIQUETADO, EstadoBulto.EMBARCADO),  # salto largo
        (EstadoBulto.ETIQUETADO, EstadoBulto.RECIBIDO),  # se brinca el andén
        (EstadoBulto.UBICADO, EstadoBulto.RECIBIDO),  # retroceso
        (EstadoBulto.RECHAZADO, EstadoBulto.RECIBIDO),  # resucitar un rechazo
        (EstadoBulto.RECIBIDO_SUCURSAL, EstadoBulto.EMBARCADO),  # reembarcar
        (EstadoBulto.RECIBIDO, EstadoBulto.RECIBIDO),  # doble registro
        (EstadoBulto.CARGADO, EstadoBulto.ASIGNADO_EMBARQUE),
        (EstadoBulto.EN_TRANSITO, EstadoBulto.RECHAZADO),  # sin escanear no hay rechazo
    ],
)
def test_transiciones_ilegales_se_bloquean(desde: EstadoBulto, hacia: EstadoBulto) -> None:
    assert transicion_valida(desde, hacia) is False

    with pytest.raises(TransicionInvalida):
        aplicar_transicion(desde, hacia)


def test_estados_terminales() -> None:
    assert es_terminal(EstadoBulto.RECHAZADO) is True
    assert es_terminal(EstadoBulto.RECIBIDO_SUCURSAL) is True
    assert es_terminal(EstadoBulto.RECIBIDO) is False


def test_ruta_completa_por_rack_es_valida() -> None:
    assert ruta_valida(
        [
            EstadoBulto.ETIQUETADO,
            EstadoBulto.EN_TRANSITO,
            EstadoBulto.ESCANEADO_ANDEN,
            EstadoBulto.RECIBIDO,
            EstadoBulto.UBICADO,
            EstadoBulto.ASIGNADO_EMBARQUE,
            EstadoBulto.CARGADO,
            EstadoBulto.EMBARCADO,
            EstadoBulto.RECIBIDO_SUCURSAL,
        ]
    )


def test_ruta_de_cross_dock_es_valida() -> None:
    """El bulto que no toca rack salta de RECIBIDO a ASIGNADO_EMBARQUE."""
    assert ruta_valida(
        [
            EstadoBulto.ESCANEADO_ANDEN,
            EstadoBulto.RECIBIDO,
            EstadoBulto.ASIGNADO_EMBARQUE,
            EstadoBulto.CARGADO,
        ]
    )


def test_ruta_con_un_salto_ilegal_es_invalida() -> None:
    assert not ruta_valida(
        [EstadoBulto.ETIQUETADO, EstadoBulto.EN_TRANSITO, EstadoBulto.UBICADO]
    )


def test_ruta_vacia_es_invalida() -> None:
    assert ruta_valida([]) is False


def test_estado_desconocido_no_es_valido() -> None:
    assert transicion_valida("INVENTADO", EstadoBulto.RECIBIDO) is False
