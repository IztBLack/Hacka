"""Pruebas de la sincronización idempotente (entregable B4).

La prueba del jurado: mandar 200 eventos dos veces y verificar que el conteo
no cambia.
"""

from __future__ import annotations

from app.dominio.qr import PayloadBulto, firmar
from app.dominio.recepcion import (
    BultoEsperado,
    Desenlace,
    EstadoRecepcion,
    LineaOC,
    ResultadoEscaneo,
)
from app.dominio.sincronizacion import EventoEscaneo, procesar_lote

LLAVE = b"llave-de-prueba-del-cedis"
SKU = "SKU-993201"
TOTAL = 200


def _qr(id_bulto: str) -> str:
    payload = PayloadBulto(
        id_bulto=id_bulto,
        orden_compra="OC-88213",
        proveedor="PRV-0147",
        sucursal="SUC-14",
        sku=SKU,
        cantidad=1,
        peso_kg=18.4,
        volumen_m3=0.42,
    )
    return firmar(payload, LLAVE)


def _estado(solicitadas: int = TOTAL, declarados: int = TOTAL) -> EstadoRecepcion:
    return EstadoRecepcion.desde_listas(
        lineas=[LineaOC(sku=SKU, cantidad_solicitada=solicitadas, precio_unitario=125.50)],
        esperados=[
            BultoEsperado(id_bulto=f"B{n:05d}", sku=SKU, cantidad=1)
            for n in range(1, declarados + 1)
        ],
    )


def _lote(n: int = TOTAL) -> list[EventoEscaneo]:
    return [
        EventoEscaneo(
            id_evento=f"EV-{i:05d}",
            cadena_qr=_qr(f"B{i:05d}"),
            escaneado_en="2026-11-25T15:00:00Z",
        )
        for i in range(1, n + 1)
    ]


def test_200_eventos_enviados_dos_veces_no_cambian_el_conteo() -> None:
    estado = _estado()
    vistos: dict[str, ResultadoEscaneo] = {}
    lote = _lote()

    primero = procesar_lote(lote, LLAVE, estado, vistos)
    recibidas_tras_primero = estado.cantidad_recibida(SKU)
    escaneados_tras_primero = len(estado.escaneados)

    segundo = procesar_lote(lote, LLAVE, estado, vistos)

    assert primero.nuevos == TOTAL and primero.repetidos == 0
    assert segundo.nuevos == 0 and segundo.repetidos == TOTAL
    assert recibidas_tras_primero == TOTAL
    assert estado.cantidad_recibida(SKU) == recibidas_tras_primero
    assert len(estado.escaneados) == escaneados_tras_primero
    assert len(vistos) == TOTAL


def test_reenviar_devuelve_el_mismo_veredicto_que_la_primera_vez() -> None:
    estado = _estado()
    vistos: dict[str, ResultadoEscaneo] = {}
    lote = _lote(10)

    primero = procesar_lote(lote, LLAVE, estado, vistos)
    segundo = procesar_lote(lote, LLAVE, estado, vistos)

    assert [r.resultado for r in primero.resultados] == [
        r.resultado for r in segundo.resultados
    ]
    assert all(r.resultado.desenlace is Desenlace.ACEPTADO for r in segundo.resultados)


def test_el_mismo_evento_dos_veces_dentro_del_mismo_lote_cuenta_una_vez() -> None:
    estado = _estado()
    vistos: dict[str, ResultadoEscaneo] = {}
    evento = _lote(1)[0]

    resumen = procesar_lote([evento, evento], LLAVE, estado, vistos)

    assert resumen.nuevos == 1 and resumen.repetidos == 1
    assert estado.cantidad_recibida(SKU) == 1


def test_lote_parcialmente_repetido_solo_procesa_lo_nuevo() -> None:
    estado = _estado()
    vistos: dict[str, ResultadoEscaneo] = {}
    lote = _lote(20)

    procesar_lote(lote[:12], LLAVE, estado, vistos)
    resumen = procesar_lote(lote, LLAVE, estado, vistos)

    assert resumen.repetidos == 12
    assert resumen.nuevos == 8
    assert estado.cantidad_recibida(SKU) == 20


def test_mismo_qr_con_otro_id_de_evento_es_duplicado_y_no_suma() -> None:
    estado = _estado()
    vistos: dict[str, ResultadoEscaneo] = {}
    qr = _qr("B00001")
    a = EventoEscaneo("EV-A", qr, "2026-11-25T15:00:00Z")
    b = EventoEscaneo("EV-B", qr, "2026-11-25T15:00:05Z")

    resumen = procesar_lote([a, b], LLAVE, estado, vistos)

    assert resumen.resultados[0].resultado.desenlace is Desenlace.ACEPTADO
    assert resumen.resultados[1].resultado.desenlace is Desenlace.DUPLICADO
    assert resumen.resultados[1].repetido is False  # evento nuevo, bulto repetido
    assert estado.cantidad_recibida(SKU) == 1


def test_un_evento_con_firma_alterada_se_rechaza_dentro_del_lote() -> None:
    estado = _estado()
    vistos: dict[str, ResultadoEscaneo] = {}
    bueno = _lote(1)[0]
    cadena = bueno.cadena_qr
    ultimo = "A" if cadena[-1] != "A" else "B"
    alterado = EventoEscaneo("EV-ALT", cadena[:-1] + ultimo, "2026-11-25T15:00:00Z")

    resumen = procesar_lote([alterado], LLAVE, estado, vistos)

    assert resumen.resultados[0].resultado.desenlace is Desenlace.RECHAZADO_FIRMA_INVALIDA
    assert estado.cantidad_recibida(SKU) == 0


def test_lote_vacio_no_hace_nada() -> None:
    estado = _estado()
    resumen = procesar_lote([], LLAVE, estado, {})
    assert resumen.nuevos == 0 and resumen.repetidos == 0
