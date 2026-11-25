"""Modelos ORM del CEDIS. Importar este paquete registra todas las tablas en Base."""

from app.modelos.acta import Acta
from app.modelos.bulto import Bulto
from app.modelos.catalogos import Anden, Sucursal, Ubicacion, Usuario
from app.modelos.cita import Cita
from app.modelos.embarque import Embarque
from app.modelos.etiqueta import Etiqueta
from app.modelos.evento_bulto import EventoBulto
from app.modelos.orden_compra import LineaOrdenCompra, OrdenCompra
from app.modelos.proveedor import Proveedor
from app.modelos.tarima import Tarima

__all__ = [
    "Acta",
    "Anden",
    "Bulto",
    "Cita",
    "Embarque",
    "Etiqueta",
    "EventoBulto",
    "LineaOrdenCompra",
    "OrdenCompra",
    "Proveedor",
    "Sucursal",
    "Tarima",
    "Ubicacion",
    "Usuario",
]
