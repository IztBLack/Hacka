"""Modelos SQLAlchemy 2.0 (adaptador de persistencia).

Se importan todos aquí para que `Base.metadata` quede completa antes de que
Alembic genere migraciones o las pruebas creen el esquema en SQLite.
"""

from app.modelos.acta import Acta, TipoActa
from app.modelos.bulto import Bulto
from app.modelos.cita import Cita
from app.modelos.embarque import Embarque
from app.modelos.evento_bulto import EventoBulto
from app.modelos.orden_compra import LineaOrdenCompra, OrdenCompra
from app.modelos.proveedor import Proveedor
from app.modelos.tarima import Tarima

__all__ = [
    "Acta",
    "TipoActa",
    "Bulto",
    "Cita",
    "Embarque",
    "EventoBulto",
    "LineaOrdenCompra",
    "OrdenCompra",
    "Proveedor",
    "Tarima",
]
