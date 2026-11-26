"""Router de recepción contra PostgreSQL real: persistencia entre requests.

Cubre lo que las pruebas del dominio (en memoria) no pueden ver:
  * el acumulado por SKU sobrevive entre requests (tope de excedente real);
  * un QR con firma inválida no toca al bulto legítimo que nombra;
  * reenviar el mismo evento no duplica evento ni acta;
  * cerrar dos veces responde 409, no 500.

Reutiliza la BD temporal migrada de `test_persistencia_pg`.
"""

import uuid
from collections.abc import Iterator
from datetime import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import settings
from app.db import obtener_sesion
from app.dominio.qr import PayloadBulto, firmar
from app.main import app
from app.modelos import Acta, Bulto, EventoBulto, LineaOrdenCompra
from tests.test_persistencia_pg import _cita, _orden, _proveedor, motor_pg  # noqa: F401

pytestmark = pytest.mark.integracion

SKU = "SKU-993201"


@pytest.fixture
def sesion(motor_pg: Engine) -> Iterator[Session]:  # noqa: F811
    conexion = motor_pg.connect()
    transaccion = conexion.begin()
    s = Session(bind=conexion, join_transaction_mode="create_savepoint")
    yield s
    s.close()
    transaccion.rollback()
    conexion.close()


@pytest.fixture
def cliente(sesion: Session) -> Iterator[TestClient]:
    app.dependency_overrides[obtener_sesion] = lambda: sesion
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(obtener_sesion, None)


@pytest.fixture
def escenario(sesion: Session) -> dict:
    """OC de 48 piezas de un SKU y tres bultos de 24: el tercero es excedente."""
    sufijo = uuid.uuid4().hex[:6].upper()
    proveedor = _proveedor(sesion)
    orden = _orden(sesion, proveedor, f"OC-{sufijo}", str(uuid.uuid4()).upper())
    cita = _cita(sesion, orden, f"CITA-T-{sufijo}", time(8, 0), time(9, 0))
    sesion.add(
        LineaOrdenCompra(
            orden_compra_id=orden.id,
            sku=SKU,
            cantidad_solicitada=48,
            cantidad_recibida=0,
            precio_unitario=10.0,
        )
    )
    qrs = {}
    for n in range(3):
        id_bulto = f"T{sufijo}{n}"
        payload = PayloadBulto(
            id_bulto=id_bulto,
            orden_compra=orden.folio,
            proveedor=proveedor.clave,
            sucursal="SUC-14",
            sku=SKU,
            cantidad=24,
            peso_kg=18.4,
            volumen_m3=0.42,
        )
        cadena = firmar(payload, settings.llave_qr_bytes)
        sesion.add(
            Bulto(
                id_bulto=id_bulto,
                orden_compra_id=orden.id,
                cita_id=cita.id,
                sucursal="SUC-14",
                sku=SKU,
                cantidad=24,
                peso_kg=18.4,
                volumen_m3=0.42,
                estado="EN_TRANSITO",
                cadena_qr=cadena,
            )
        )
        qrs[id_bulto] = cadena
    sesion.flush()
    return {"cita": cita.folio, "orden_id": orden.id, "qrs": qrs}


def _escanear(cliente: TestClient, cita: str, cadena: str, uuid_evento: str | None = None):
    respuesta = cliente.post(
        "/recepcion/escaneo",
        json={
            "cadena_qr": cadena,
            "uuid_evento": uuid_evento or str(uuid.uuid4()),
            "cita": cita,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_excedente_se_detecta_entre_requests(cliente, escenario, sesion):
    cadenas = list(escenario["qrs"].values())
    assert _escanear(cliente, escenario["cita"], cadenas[0])["desenlace"] == "ACEPTADO"
    assert _escanear(cliente, escenario["cita"], cadenas[1])["desenlace"] == "ACEPTADO"
    # 24 + 24 = 48 = tope. El tercero, en otro request, ya no cabe.
    assert (
        _escanear(cliente, escenario["cita"], cadenas[2])["desenlace"]
        == "RECHAZADO_EXCEDENTE"
    )
    linea = sesion.scalars(
        select(LineaOrdenCompra).where(
            LineaOrdenCompra.orden_compra_id == escenario["orden_id"]
        )
    ).one()
    assert linea.cantidad_recibida == 48


def test_rescaneo_en_otro_request_es_duplicado(cliente, escenario):
    cadena = next(iter(escenario["qrs"].values()))
    assert _escanear(cliente, escenario["cita"], cadena)["desenlace"] == "ACEPTADO"
    segundo = _escanear(cliente, escenario["cita"], cadena)
    assert segundo["desenlace"] == "DUPLICADO"
    assert segundo["acumulado_sku"] == 24


def test_firma_invalida_no_toca_al_bulto_legitimo(cliente, escenario, sesion):
    id_bulto, cadena = next(iter(escenario["qrs"].items()))
    falsa = cadena.rsplit("|", 1)[0] + "|AAAAAAAAAAAAA"
    resultado = _escanear(cliente, escenario["cita"], falsa)
    assert resultado["desenlace"] == "RECHAZADO_FIRMA_INVALIDA"

    bulto = sesion.scalars(select(Bulto).where(Bulto.id_bulto == id_bulto)).one()
    assert bulto.estado == "EN_TRANSITO"
    # El legítimo sigue pudiendo entrar.
    assert _escanear(cliente, escenario["cita"], cadena)["desenlace"] == "ACEPTADO"


def test_reenvio_del_mismo_evento_no_duplica_acta(cliente, escenario, sesion):
    cadena = next(iter(escenario["qrs"].values()))
    falsa = cadena.rsplit("|", 1)[0] + "|AAAAAAAAAAAAA"
    uuid_evento = str(uuid.uuid4())
    _escanear(cliente, escenario["cita"], falsa, uuid_evento)
    reenvio = _escanear(cliente, escenario["cita"], falsa, uuid_evento)
    assert reenvio["desenlace"] == "DUPLICADO"
    actas = sesion.scalar(
        select(func.count(Acta.id)).where(Acta.orden_compra_id == escenario["orden_id"])
    )
    assert actas == 1


def test_reenvio_de_aceptado_no_duplica_evento(cliente, escenario, sesion):
    cadena = next(iter(escenario["qrs"].values()))
    uuid_evento = str(uuid.uuid4())
    _escanear(cliente, escenario["cita"], cadena, uuid_evento)
    assert _escanear(cliente, escenario["cita"], cadena, uuid_evento)["desenlace"] == "DUPLICADO"
    eventos = sesion.scalar(
        select(func.count(EventoBulto.id)).where(EventoBulto.uuid_evento == uuid_evento)
    )
    assert eventos == 1


def test_cierre_cuenta_lo_escaneado_y_no_se_repite(cliente, escenario):
    cadenas = list(escenario["qrs"].values())
    _escanear(cliente, escenario["cita"], cadenas[0])

    cierre = cliente.post(f"/recepcion/cierre/{escenario['cita']}")
    assert cierre.status_code == 200, cierre.text
    cuerpo = cierre.json()
    assert cuerpo["bultos_aceptados"] == 1
    assert cuerpo["hay_faltantes"] is True
    assert cuerpo["faltantes"][0]["cantidad_recibida"] == 24
    assert cuerpo["faltantes"][0]["cantidad_faltante"] == 24

    otra_vez = cliente.post(f"/recepcion/cierre/{escenario['cita']}")
    assert otra_vez.status_code == 409
