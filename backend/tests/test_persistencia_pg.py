"""Pruebas de integración contra PostgreSQL 16 real (contenedor cedis-postgres).

Crean una BD temporal, aplican las migraciones de Alembic y revierten cada prueba.
"""

import uuid
from collections.abc import Iterator
from datetime import date, time
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import ahora_utc
from app.modelos import Bulto, Cita, EventoBulto, OrdenCompra, Proveedor
from app.servicios.repositorios import RepositorioEventoBulto

pytestmark = pytest.mark.integracion

NOMBRE_BD_PRUEBA = "cedis_test_persistencia"
RAIZ_BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def motor_pg() -> Iterator[Engine]:
    url_base = make_url(settings.url_base_datos)
    url_prueba = url_base.set(database=NOMBRE_BD_PRUEBA)
    admin = create_engine(url_base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conexion:
            conexion.execute(
                text(f'DROP DATABASE IF EXISTS "{NOMBRE_BD_PRUEBA}" WITH (FORCE)')
            )
            conexion.execute(text(f'CREATE DATABASE "{NOMBRE_BD_PRUEBA}"'))
    except OperationalError:
        admin.dispose()
        pytest.skip("PostgreSQL 16 no disponible (levanta cedis-postgres)")

    cfg = Config(str(RAIZ_BACKEND / "alembic.ini"))
    url_texto = url_prueba.render_as_string(hide_password=False).replace("%", "%%")
    cfg.set_main_option("sqlalchemy.url", url_texto)
    command.upgrade(cfg, "head")

    motor = create_engine(url_prueba)
    yield motor
    motor.dispose()
    with admin.connect() as conexion:
        conexion.execute(text(f'DROP DATABASE IF EXISTS "{NOMBRE_BD_PRUEBA}" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture
def sesion(motor_pg: Engine) -> Iterator[Session]:
    conexion = motor_pg.connect()
    transaccion = conexion.begin()
    s = Session(bind=conexion, join_transaction_mode="create_savepoint")
    yield s
    s.close()
    transaccion.rollback()
    conexion.close()


def _proveedor(sesion: Session) -> Proveedor:
    proveedor = Proveedor(
        clave=f"PRV-{uuid.uuid4().hex[:6]}",
        razon_social="Proveedor de prueba",
        rfc="PRU010101AA1",
        score=80,
        score_puntualidad=80,
        score_etiquetado=80,
        score_documental=80,
        pre_paletizado=False,
        no_shows=0,
        activo=True,
    )
    sesion.add(proveedor)
    sesion.flush()
    return proveedor


def _orden(sesion: Session, proveedor: Proveedor, folio: str, uuid_cfdi: str) -> OrdenCompra:
    orden = OrdenCompra(
        folio=folio,
        proveedor_id=proveedor.id,
        uuid_cfdi=uuid_cfdi,
        cfdi_validado=True,
        cfdi_vigente=True,
        fecha_emision=date(2026, 1, 12),
        estado="ABIERTA",
        importe_total=Decimal("100.00"),
    )
    sesion.add(orden)
    sesion.flush()
    return orden


def _cita(
    sesion: Session,
    orden: OrdenCompra,
    folio: str,
    inicio: time,
    fin: time,
    estado: str = "CONFIRMADA",
) -> Cita:
    cita = Cita(
        folio=folio,
        proveedor_id=orden.proveedor_id,
        orden_compra_id=orden.id,
        fecha=date(2026, 1, 15),
        anden=5,
        hora_inicio=inicio,
        hora_fin=fin,
        n_bultos_declarados=10,
        duracion_minutos=60,
        estado=estado,
        minutos_tolerancia=15,
        pase_caseta=None,
    )
    sesion.add(cita)
    sesion.flush()
    return cita


def test_uuid_cfdi_duplicado_viola_unicidad(sesion: Session) -> None:
    proveedor = _proveedor(sesion)
    uuid_cfdi = str(uuid.uuid4())
    _orden(sesion, proveedor, "OC-T-0001", uuid_cfdi)
    with pytest.raises(IntegrityError):
        _orden(sesion, proveedor, "OC-T-0002", uuid_cfdi)


def test_cita_traslapada_en_mismo_anden_es_rechazada(sesion: Session) -> None:
    orden = _orden(sesion, _proveedor(sesion), "OC-T-0010", str(uuid.uuid4()))
    _cita(sesion, orden, "CIT-T-0001", time(9, 0), time(10, 30))
    with pytest.raises(IntegrityError) as excepcion:
        _cita(sesion, orden, "CIT-T-0002", time(10, 0), time(11, 0))
    assert "ex_cita_sin_traslape_anden" in str(excepcion.value)


def test_citas_contiguas_o_canceladas_no_chocan(sesion: Session) -> None:
    orden = _orden(sesion, _proveedor(sesion), "OC-T-0020", str(uuid.uuid4()))
    _cita(sesion, orden, "CIT-T-0010", time(9, 0), time(10, 0))
    _cita(sesion, orden, "CIT-T-0011", time(10, 0), time(11, 0))  # contigua: permitido
    _cita(sesion, orden, "CIT-T-0012", time(9, 30), time(10, 30), estado="CANCELADA")


def test_evento_bulto_es_idempotente_por_uuid_evento(sesion: Session) -> None:
    orden = _orden(sesion, _proveedor(sesion), "OC-T-0030", str(uuid.uuid4()))
    cita = _cita(sesion, orden, "CIT-T-0020", time(9, 0), time(10, 0))
    bulto = Bulto(
        id_bulto="B-T-0001",
        orden_compra_id=orden.id,
        cita_id=cita.id,
        sucursal="SUC-14",
        sku="SKU-993201",
        cantidad=1,
        peso_kg=Decimal("5.00"),
        volumen_m3=Decimal("0.050"),
        estado="ESPERADO",
        cadena_qr="B-T-0001|SKU-993201|SUC-14|A7F3K9Q2M5X1B",
        tipo_destino="RACK_HOME",
    )
    sesion.add(bulto)
    sesion.flush()

    repositorio = RepositorioEventoBulto(sesion)
    valores: dict[str, Any] = {
        "uuid_evento": uuid.uuid4(),
        "bulto_id": bulto.id,
        "estado": "RECIBIDO",
        "desenlace": "OK",
        "motivo": None,
        "ocurrido_en": ahora_utc(),
        "dispositivo": "TC-01",
        "operador": "op1",
    }

    assert repositorio.insertar_idempotente(valores) is True
    assert repositorio.insertar_idempotente(valores) is False  # reintento offline
    total = sesion.scalar(
        select(func.count()).select_from(EventoBulto).where(EventoBulto.bulto_id == bulto.id)
    )
    assert total == 1
