"""Cita -> etiquetas, contra PostgreSQL real.

Reservar una cita (C1) deja sus bultos con QR firmado listos para imprimir
(C4) y para escanear (C2).
"""

import uuid
from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import settings
from app.db import obtener_sesion
from app.dominio.qr import verificar
from app.main import app
from app.modelos import LineaOrdenCompra
from app.modelos.catalogos import Sucursal
from tests.test_persistencia_pg import _orden, _proveedor, motor_pg  # noqa: F401

pytestmark = pytest.mark.integracion


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
def oc(sesion: Session) -> dict:
    for n in (1, 2, 3):
        sesion.add(
            Sucursal(
                clave=f"SUC-9{n}",
                nombre=f"Prueba {n}",
                rack_home=n,  # CHECK 1..32; la BD de prueba arranca sin catálogo
                km_ruta=Decimal("10.00"),
            )
        )
    proveedor = _proveedor(sesion)
    orden = _orden(sesion, proveedor, f"OC-{uuid.uuid4().hex[:6]}", str(uuid.uuid4()).upper())
    sesion.add_all(
        [
            LineaOrdenCompra(
                orden_compra_id=orden.id, sku="SKU-1", descripcion="Atún",
                cantidad_solicitada=60, precio_unitario=10.0,
            ),
            LineaOrdenCompra(
                orden_compra_id=orden.id, sku="SKU-2", descripcion="Sardina",
                cantidad_solicitada=20, precio_unitario=8.0,
            ),
        ]
    )
    sesion.flush()
    return {"proveedor": proveedor.clave, "orden": orden.folio}


def _reservar(cliente: TestClient, oc: dict, n_bultos: int = 8) -> dict:
    r = cliente.post(
        "/citas",
        json={
            "proveedor": oc["proveedor"],
            "orden_compra": oc["orden"],
            "fecha": str(date(2027, 3, 3)),
            "anden": 1,
            "hora_inicio": "08:00:00",
            "n_bultos": n_bultos,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_reservar_genera_etiquetas_firmadas(cliente, oc):
    cita = _reservar(cliente, oc)
    r = cliente.get(f"/citas/{cita['folio']}/etiquetas")
    assert r.status_code == 200, r.text
    cuerpo = r.json()

    assert cuerpo["total"] == 8
    assert cuerpo["cita"]["orden_compra"] == oc["orden"]
    assert cuerpo["cita"]["anden"] == 1
    assert sum(b["cantidad"] for b in cuerpo["bultos"] if b["sku"] == "SKU-1") == 60
    assert sum(b["cantidad"] for b in cuerpo["bultos"] if b["sku"] == "SKU-2") == 20

    for b in cuerpo["bultos"]:
        payload = verificar(b["cadena_qr"], settings.llave_qr_bytes)
        assert payload.id_bulto == b["id_bulto"]
        assert payload.sucursal == b["sucursal"]
        assert b["estado"] == "ETIQUETADO"
    assert {b["descripcion"] for b in cuerpo["bultos"]} == {"Atún", "Sardina"}


def test_pedir_etiquetas_dos_veces_no_duplica(cliente, oc):
    cita = _reservar(cliente, oc)
    a = cliente.get(f"/citas/{cita['folio']}/etiquetas").json()
    b = cliente.get(f"/citas/{cita['folio']}/etiquetas").json()
    assert [x["id_bulto"] for x in a["bultos"]] == [x["id_bulto"] for x in b["bultos"]]


def test_listar_citas_por_fecha(cliente, oc):
    cita = _reservar(cliente, oc)
    r = cliente.get("/citas", params={"fecha": "2027-03-03"})
    assert r.status_code == 200
    assert cita["folio"] in [c["folio"] for c in r.json()]


def test_etiquetas_de_cita_inexistente_es_404(cliente):
    assert cliente.get("/citas/NO-EXISTE/etiquetas").status_code == 404
