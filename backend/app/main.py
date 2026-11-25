"""Aplicación FastAPI del nodo edge del CEDIS.

La operación vive aquí, dentro del CEDIS. La nube es réplica, no dependencia:
si se cae internet, este servicio sigue atendiendo a los handhelds.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import citas, consolidacion, embarques, etiquetas, recepcion
from app.config import settings
from app.db import motor

ETIQUETAS_OPENAPI = [
    {"name": "salud", "description": "Estado del servicio y de sus dependencias"},
    {"name": "citas", "description": "Momento 1: agendamiento y andén 5 flex"},
    {"name": "etiquetas", "description": "Momento 2: etiquetas 4x6 con QR firmado"},
    {"name": "recepcion", "description": "Momento 3: escaneo, excepciones y faltantes"},
    {"name": "consolidacion", "description": "Momento 4: semáforo y flota heterogénea"},
    {"name": "embarques", "description": "Relación de Embarque y Carta Porte 3.1"},
]


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    """Arranque y apagado.

    El esquema NO se crea aquí: lo administra Alembic (`alembic upgrade head`).
    Crear tablas al arrancar esconde migraciones pendientes en producción.
    """
    yield
    motor.dispose()


def crear_app() -> FastAPI:
    """Fábrica de la app, para poder instanciarla distinta en las pruebas."""
    app = FastAPI(
        title=settings.nombre_app,
        version=settings.version_app,
        description=(
            "De la orden de compra al embarque. Backend edge-first del CEDIS: "
            "citas, etiquetas firmadas, recepción offline-first, consolidación "
            "con flota heterogénea y embarque con Carta Porte 3.1."
        ),
        openapi_tags=ETIQUETAS_OPENAPI,
        lifespan=ciclo_vida,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origenes_permitidos,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(citas.router, prefix="/citas", tags=["citas"])
    app.include_router(etiquetas.router, prefix="/etiquetas", tags=["etiquetas"])
    app.include_router(recepcion.router, prefix="/recepcion", tags=["recepcion"])
    app.include_router(
        consolidacion.router, prefix="/consolidacion", tags=["consolidacion"]
    )
    app.include_router(embarques.router, prefix="/embarques", tags=["embarques"])

    @app.get("/salud", tags=["salud"])
    def salud() -> dict[str, str]:
        """Healthcheck del contenedor: solo dice que el proceso responde."""
        return {"estado": "ok", "servicio": settings.nombre_app, "version": settings.version_app}

    @app.get("/salud/profunda", tags=["salud"])
    def salud_profunda() -> dict[str, object]:
        """Healthcheck con base de datos.

        Distinguirlo del anterior importa: el CEDIS puede operar en modo
        degradado con la base caída, y un healthcheck que tumba el contenedor
        por eso sería peor que el problema.
        """
        try:
            with motor.connect() as conexion:
                conexion.execute(text("SELECT 1"))
            base = "ok"
        except Exception as exc:  # noqa: BLE001 - se reporta, no se traga
            base = f"error: {type(exc).__name__}"
        return {"estado": "ok" if base == "ok" else "degradado", "base_datos": base}

    return app


app = crear_app()
