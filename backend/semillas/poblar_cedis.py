"""Semillas sintéticas del CEDIS (idempotentes).

Uso: cd backend && python -m semillas.poblar_cedis
"""

import random
import uuid
from datetime import date, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Base, FabricaSesion, ahora_utc
from app.modelos import (
    Acta,
    Anden,
    Bulto,
    Cita,
    Embarque,
    Etiqueta,
    LineaOrdenCompra,
    OrdenCompra,
    Proveedor,
    Sucursal,
    Tarima,
    Ubicacion,
)

# (numero, tipo, recibo_desde, recibo_hasta). Andén 5 = Salida 3 flex; 6 y 7 = Salidas 1 y 2.
ANDENES: list[tuple[int, str, time | None, time | None]] = [
    (1, "recibo", None, None),
    (2, "recibo", None, None),
    (3, "recibo", None, None),
    (4, "recibo", None, None),
    (5, "flex", time(8, 0), time(13, 0)),
    (6, "embarque", None, None),
    (7, "embarque", None, None),
]

RAICES_PROVEEDOR = [
    "Distribuidora Atlántico",
    "Abarrotes del Bajío",
    "Lácteos de la Sierra",
    "Comercializadora Pacífico",
    "Bebidas del Centro",
    "Higiene y Hogar",
    "Granos y Semillas",
    "Embutidos Norteños",
]


def _obtener_o_crear[T: Base](
    sesion: Session,
    modelo: type[T],
    buscar: dict[str, Any],
    valores: dict[str, Any] | None = None,
) -> T:
    """Devuelve la fila que cumple `buscar` o la crea con `buscar` + `valores`."""
    instancia = sesion.scalars(select(modelo).filter_by(**buscar)).first()
    if instancia is None:
        instancia = modelo(**buscar, **(valores or {}))
        sesion.add(instancia)
        sesion.flush()
    return instancia


def poblar_andenes(sesion: Session) -> None:
    for numero, tipo, desde, hasta in ANDENES:
        _obtener_o_crear(
            sesion,
            Anden,
            {"numero": numero},
            {"tipo": tipo, "recibo_desde": desde, "recibo_hasta": hasta},
        )


def poblar_sucursales_y_ubicaciones(sesion: Session) -> None:
    for n in range(1, 33):
        sucursal = _obtener_o_crear(
            sesion,
            Sucursal,
            {"clave": f"SUC-{n:02d}"},
            {
                "nombre": f"Sucursal {n:02d}",
                "rack_home": n,
                "km_ruta": Decimal(12 + n * 9),
                "activa": True,
            },
        )
        # Rack home: 3 niveles x 6 posiciones por sucursal (ej. SUC14-N2-P05).
        for nivel in range(1, 4):
            for posicion in range(1, 7):
                _obtener_o_crear(
                    sesion,
                    Ubicacion,
                    {"clave": f"SUC{n:02d}-N{nivel}-P{posicion:02d}"},
                    {"sucursal_id": sucursal.id, "zona": "rack_home", "ocupada": False},
                )
    for posicion in range(1, 9):
        _obtener_o_crear(
            sesion,
            Ubicacion,
            {"clave": f"FLEX-P{posicion:02d}"},
            {"sucursal_id": None, "zona": "flex", "ocupada": False},
        )
    for salida in range(1, 4):
        _obtener_o_crear(
            sesion,
            Ubicacion,
            {"clave": f"SAL-{salida:02d}"},
            {"sucursal_id": None, "zona": "anden_salida", "ocupada": False},
        )


def poblar_proveedores(sesion: Session) -> None:
    _obtener_o_crear(
        sesion,
        Proveedor,
        {"clave": "PRV-0147"},
        {
            "razon_social": "Alimentos del Golfo",
            "rfc": "AGO120315AB7",
            "score": 94,
            "score_puntualidad": 96,
            "score_etiquetado": 92,
            "score_documental": 94,
            "pre_paletizado": True,
            "no_shows": 0,
            "activo": True,
        },
    )
    azar = random.Random(42)  # determinista: mismas cifras en cada corrida
    for indice, numero in enumerate(range(101, 135)):  # 34 proveedores + PRV-0147 = 35
        raiz = RAICES_PROVEEDOR[indice % len(RAICES_PROVEEDOR)]
        _obtener_o_crear(
            sesion,
            Proveedor,
            {"clave": f"PRV-{numero:04d}"},
            {
                "razon_social": f"{raiz} {numero:04d} S.A. de C.V.",
                "rfc": f"PRV{numero:04d}01XX1",
                "score": azar.randint(60, 99),
                "score_puntualidad": azar.randint(60, 100),
                "score_etiquetado": azar.randint(60, 100),
                "score_documental": azar.randint(60, 100),
                "pre_paletizado": azar.random() < 0.4,
                "no_shows": azar.randint(0, 3),
                "activo": True,
            },
        )


def poblar_escenario_mockup(sesion: Session) -> None:
    ahora = ahora_utc()
    proveedor = sesion.scalars(select(Proveedor).where(Proveedor.clave == "PRV-0147")).one()

    orden = _obtener_o_crear(
        sesion,
        OrdenCompra,
        {"folio": "OC-88213"},
        {
            "proveedor_id": proveedor.id,
            "uuid_cfdi": "3f2b8c1e-5a47-4d9e-8b61-2c7a9d4e1f03",
            "cfdi_validado": True,
            "cfdi_vigente": True,
            "fecha_emision": date(2026, 1, 12),
            "estado": "ABIERTA",
            "importe_total": Decimal("14232.00"),
        },
    )
    for sku, descripcion, solicitada, precio in [
        ("SKU-993201", "Atún en agua 140 g (caja 24)", 480, Decimal("18.40")),
        ("SKU-993202", "Sardina en tomate 155 g (caja 24)", 240, Decimal("22.50")),
    ]:
        _obtener_o_crear(
            sesion,
            LineaOrdenCompra,
            {"orden_compra_id": orden.id, "sku": sku},
            {
                "descripcion": descripcion,
                "cantidad_solicitada": solicitada,
                "cantidad_recibida": 0,
                "precio_unitario": precio,
            },
        )

    cita = _obtener_o_crear(
        sesion,
        Cita,
        {"folio": "CIT-2026-0412"},
        {
            "proveedor_id": proveedor.id,
            "orden_compra_id": orden.id,
            "fecha": date(2026, 1, 15),
            "anden": 5,
            "hora_inicio": time(9, 0),
            "hora_fin": time(10, 30),
            "n_bultos_declarados": 48,
            "duracion_minutos": 90,
            "estado": "CONFIRMADA",
            "minutos_tolerancia": 15,
            "pase_caseta": "PC-0412",
        },
    )

    tarima = _obtener_o_crear(
        sesion,
        Tarima,
        {"folio": "T-0450"},
        {
            "sucursal": "SUC-14",
            "embarque_id": None,
            "peso_kg": Decimal("18.50"),
            "volumen_m3": Decimal("0.120"),
            "n_bultos": 1,
            "armada_en": ahora - timedelta(hours=4),
            "ubicacion": "FLEX-P01",
            "estado": "ARMADA",
            "posicion_unidad": None,
        },
    )

    # Tarimas con más de 36 h sin embarque: prueban la excepción de consolidación.
    for folio, sucursal, horas in [
        ("T-0441", "SUC-14", 40),
        ("T-0442", "SUC-14", 52),
        ("T-0443", "SUC-07", 75),
    ]:
        _obtener_o_crear(
            sesion,
            Tarima,
            {"folio": folio},
            {
                "sucursal": sucursal,
                "embarque_id": None,
                "peso_kg": Decimal("420.00"),
                "volumen_m3": Decimal("1.800"),
                "n_bultos": 12,
                "armada_en": ahora - timedelta(hours=horas),
                "ubicacion": "FLEX-P02",
                "estado": "ARMADA",
                "posicion_unidad": None,
            },
        )

    firma = "A7F3K9Q2M5X1B"  # 13 caracteres
    bulto = _obtener_o_crear(
        sesion,
        Bulto,
        {"id_bulto": "B00412"},
        {
            "orden_compra_id": orden.id,
            "cita_id": cita.id,
            "tarima_id": tarima.id,
            "sucursal": "SUC-14",
            "sku": "SKU-993201",
            "cantidad": 24,
            "peso_kg": Decimal("18.50"),
            "volumen_m3": Decimal("0.120"),
            "estado": "EN_TARIMA",
            "cadena_qr": f"B00412|SKU-993201|SUC-14|{firma}",
            "tipo_destino": "RACK_HOME",
            "ubicacion": "SUC14-N2-P05",
        },
    )
    _obtener_o_crear(
        sesion,
        Etiqueta,
        {"bulto_id": bulto.id, "secuencia": 1},
        {"kid": "k-2026-01", "firma": firma},
    )

    _obtener_o_crear(
        sesion,
        Embarque,
        {"folio": "REL-2026-01184"},
        {
            "sucursal": "SUC-14",
            "clase_unidad": "TORTON",
            "posiciones_unidad": 12,
            "estado": "ABIERTO",
            "tarimas_acumuladas": 0,
            "peso_kg": Decimal("0"),
            "volumen_m3": Decimal("0"),
            "ocupacion": 0,
        },
    )

    _obtener_o_crear(
        sesion,
        Acta,
        {"folio": "ACT-2026-0392"},
        {
            "tipo": "DIFERENCIA_RECEPCION",
            "cita_id": cita.id,
            "orden_compra_id": orden.id,
            "bulto_id": bulto.id,
            "importe": Decimal("1250.00"),
            "cuerpo": {
                "sku": "SKU-993201",
                "observacion": "Faltante de 3 cajas en recibo",
                "uuid_ref": str(uuid.uuid5(uuid.NAMESPACE_URL, "ACT-2026-0392")),
            },
            "reportada": False,
        },
    )


def principal() -> None:
    with FabricaSesion() as sesion:
        poblar_andenes(sesion)
        poblar_sucursales_y_ubicaciones(sesion)
        poblar_proveedores(sesion)
        poblar_escenario_mockup(sesion)
        sesion.commit()
    print("Semillas del CEDIS cargadas (idempotente).")


if __name__ == "__main__":
    principal()
