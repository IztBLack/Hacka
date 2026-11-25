# Imagen del servicio API para el nodo edge.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Las dependencias se instalan antes de copiar el codigo: asi la capa de
# dependencias se reutiliza entre builds.
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Usuario sin privilegios: el contenedor no necesita root.
RUN useradd --create-home --uid 10001 cedis && chown -R cedis:cedis /app
USER cedis

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
