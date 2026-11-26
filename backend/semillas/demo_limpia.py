"""Deja la base en el estado limpio de la demo (DESTRUCTIVO).

Borra todo lo operativo (OC, citas, bultos, tarimas, embarques, actas,
eventos) y deja solo:
  * catálogos: andenes, sucursales y ubicaciones;
  * 2 proveedores;
  * 3 citas de ejemplo con sus etiquetas firmadas (C4);
  * 2 órdenes de compra sin cita, listas para reservar en el Portal (C1).
    `OC-88213` es la que usa el Portal;
  * tarimas en rack de 9 sucursales para el Tablero (C3).

Uso: cd backend && python -m semillas.demo_limpia --confirmar
"""

import sys
from datetime import date, time, timedelta
from decimal import Decimal

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.db import FabricaSesion, ahora_utc
from app.dominio.citas import Franja, duracion_minutos
from app.modelos import Cita, LineaOrdenCompra, OrdenCompra, Proveedor, Sucursal, Tarima
from app.servicios.desglose import asegurar_desglose
from semillas.poblar_cedis import poblar_andenes, poblar_sucursales_y_ubicaciones

FECHA_DEMO = date(2026, 11, 26)

TABLAS_OPERATIVAS = (
    "evento_bulto",
    "etiqueta",
    "acta",
    "bulto",
    "tarima",
    "embarque",
    "cita",
    "linea_orden_compra",
    "orden_compra",
)

PROVEEDORES = [
    {
        "clave": "PRV-0147",
        "razon_social": "Alimentos del Golfo",
        "rfc": "AGO120315AB7",
        "score": 94,
        "score_puntualidad": 96,
        "score_etiquetado": 92,
        "score_documental": 94,
        "pre_paletizado": True,
    },
    {
        "clave": "PRV-0102",
        "razon_social": "Abarrotes del Bajío",
        "rfc": "ABA090811KP3",
        "score": 88,
        "score_puntualidad": 85,
        "score_etiquetado": 90,
        "score_documental": 89,
        "pre_paletizado": False,
    },
]

# (folio, proveedor, uuid CFDI, líneas[(sku, descripción, piezas, precio)])
ORDENES = [
    # Sin cita: las reserva el Portal.
    ("OC-88213", "PRV-0147", "3F2A9C41-7B8D-4E55-9A12-C6D80F4B1E77", [
        ("SKU-993201", "Atún en agua 140 g (caja 24)", 480, "18.40"),
        ("SKU-993202", "Sardina en tomate 155 g (caja 24)", 240, "22.50"),
    ]),
    ("OC-88214", "PRV-0102", "8C1D2E3F-4A5B-4C6D-8E7F-901A2B3C4D5E", [
        ("SKU-410022", "Frijol bayo 900 g (caja 12)", 300, "31.00"),
    ]),
    # Con cita y etiquetas: los ejemplos de C4.
    ("OC-88201", "PRV-0147", "1A2B3C4D-5E6F-4A7B-8C9D-0E1F2A3B4C5D", [
        ("SKU-993201", "Atún en agua 140 g (caja 24)", 36, "18.40"),
    ]),
    ("OC-88202", "PRV-0102", "2B3C4D5E-6F7A-4B8C-9D0E-1F2A3B4C5D6E", [
        ("SKU-410022", "Frijol bayo 900 g (caja 12)", 40, "31.00"),
        ("SKU-410035", "Arroz súper extra 1 kg (caja 10)", 24, "27.80"),
    ]),
    ("OC-88203", "PRV-0147", "3C4D5E6F-7A8B-4C9D-8E1F-2A3B4C5D6E7F", [
        ("SKU-883417", "Chiles jalapeños 380 g (caja 12)", 30, "24.90"),
        ("SKU-993202", "Sardina en tomate 155 g (caja 24)", 18, "22.50"),
    ]),
]

# Tarimas en rack para el Tablero (C3), las mismas 9 sucursales del diseño:
# (sucursal, nombre, tarimas, horas de la más antigua, kg y m3 totales).
# La antigüedad se cuenta desde que corre el script: si pasa un día, las
# filas se vuelven excepción. Vuelva a correrlo antes de presentar.
TARIMAS = [
    ("SUC-03", "Centro", 11, 14, 10_840, 26.8),         # tortón al 92%: liberar
    ("SUC-14", "Plaza Oriente", 11, 9, 10_500, 26.2),   # tortón al 92%: liberar
    ("SUC-07", "Norte", 9, 22, 8_960, 21.4),            # acumulando
    ("SUC-21", "Las Flores", 6, 17, 5_720, 14.3),       # rabón lleno: liberar
    ("SUC-28", "Industrial", 5, 41, 4_810, 11.9),       # > 36 h: excepción
    ("SUC-11", "Sur", 4, 38, 3_900, 9.5),               # > 36 h: excepción
    ("SUC-19", "Valle", 3, 12, 2_740, 7.1),             # camioneta llena: liberar
    ("SUC-32", "Lomas", 2, 37, 1_880, 4.8),             # > 36 h: excepción
    ("SUC-25", "Poniente", 2, 6, 1_910, 4.8),           # acumulando
]

# (folio cita, OC, andén, hora, bultos declarados)
CITAS = [
    ("CITA-20261126-001", "OC-88201", 1, time(8, 0), 6),
    ("CITA-20261126-002", "OC-88202", 2, time(9, 0), 8),
    ("CITA-20261126-003", "OC-88203", 4, time(10, 0), 10),
]


def vaciar(sesion: Session) -> None:
    sesion.execute(
        text(f"TRUNCATE {', '.join(TABLAS_OPERATIVAS)} RESTART IDENTITY CASCADE")
    )
    sesion.execute(delete(Proveedor))


def poblar(sesion: Session) -> None:
    poblar_andenes(sesion)
    poblar_sucursales_y_ubicaciones(sesion)

    proveedores = {}
    for datos in PROVEEDORES:
        p = Proveedor(**datos, no_shows=0, activo=True)
        sesion.add(p)
        proveedores[p.clave] = p
    sesion.flush()

    ordenes = {}
    for folio, clave, uuid_cfdi, lineas in ORDENES:
        orden = OrdenCompra(
            folio=folio,
            proveedor_id=proveedores[clave].id,
            uuid_cfdi=uuid_cfdi,
            cfdi_validado=True,
            cfdi_vigente=True,
            fecha_emision=date(2026, 11, 20),
            estado="ABIERTA",
            importe_total=sum(Decimal(p) * n for _, _, n, p in lineas),
        )
        sesion.add(orden)
        sesion.flush()
        for sku, descripcion, piezas, precio in lineas:
            sesion.add(
                LineaOrdenCompra(
                    orden_compra_id=orden.id,
                    sku=sku,
                    descripcion=descripcion,
                    cantidad_solicitada=piezas,
                    cantidad_recibida=0,
                    precio_unitario=float(precio),
                )
            )
        ordenes[folio] = orden
    sesion.flush()

    for folio, folio_oc, anden, inicio, n_bultos in CITAS:
        orden = ordenes[folio_oc]
        duracion = duracion_minutos(n_bultos)
        franja = Franja.desde_duracion(inicio, duracion, anden=anden)
        cita = Cita(
            folio=folio,
            proveedor_id=orden.proveedor_id,
            orden_compra_id=orden.id,
            fecha=FECHA_DEMO,
            anden=anden,
            hora_inicio=franja.inicio,
            hora_fin=franja.fin,
            n_bultos_declarados=n_bultos,
            duracion_minutos=duracion,
            estado="CONFIRMADA",
        )
        sesion.add(cita)
        sesion.flush()
        asegurar_desglose(sesion, cita)

    poblar_tarimas(sesion)


def poblar_tarimas(sesion: Session) -> None:
    ahora = ahora_utc()
    consecutivo = 1
    for clave, nombre, n, horas, kg, m3 in TARIMAS:
        sucursal = sesion.scalars(select(Sucursal).where(Sucursal.clave == clave)).one()
        sucursal.nombre = nombre
        numero = int(clave[4:])
        for i in range(n):
            # La primera es la más antigua; las demás se armaron después.
            armada = ahora - timedelta(hours=horas - i * (horas / max(n, 1)) * 0.6)
            sesion.add(
                Tarima(
                    folio=f"T-{consecutivo:04d}",
                    sucursal=clave,
                    peso_kg=min(990.0, round(kg / n, 1)),
                    volumen_m3=round(m3 / n, 3),
                    n_bultos=24,
                    armada_en=armada,
                    ubicacion=f"SUC{numero:02d}-N{i // 6 + 1}-P{i % 6 + 1:02d}",
                    estado="EN_RACK",
                )
            )
            consecutivo += 1


def principal() -> None:
    if "--confirmar" not in sys.argv:
        print("Esto BORRA todos los datos operativos. Repite con --confirmar.")
        sys.exit(1)
    with FabricaSesion() as sesion:
        vaciar(sesion)
        poblar(sesion)
        sesion.commit()
    print(
        f"Demo limpia: {len(PROVEEDORES)} proveedores, {len(CITAS)} citas con etiquetas, "
        f"{len(ORDENES) - len(CITAS)} OC sin cita para el Portal, "
        f"{sum(t[2] for t in TARIMAS)} tarimas en rack ({len(TARIMAS)} sucursales)."
    )


if __name__ == "__main__":
    principal()
