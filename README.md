# De la Orden de Compra al Embarque — Reto de logística · CEDIS

Sistema YMS/WMS ligero que digitaliza el flujo desde que se emite una Orden de Compra hasta que la mercancía sale en embarque a la sucursal.

**Escala del problema:** un CEDIS de 100 m × 40 m, 4 andenes de recibo y 3 de embarque, ~35 camiones de proveedor al día y 32 sucursales que surtir con ~20 embarques diarios.

---

## Empieza por aquí

**Si es tu primer día en el proyecto, lee en este orden:**

| # | Documento | Qué te da | Tiempo |
|:--|:---|:---|:---|
| 1 | [`docs/propuesta-cedis-v2.md`](docs/propuesta-cedis-v2.md) | El problema, la solución y por qué. Incluye cotización y ROI | 20 min |
| 2 | [`docs/03-plan-de-trabajo.md`](docs/03-plan-de-trabajo.md) | **Tu bloque, tus carpetas y tu definición de terminado** | 10 min |
| 3 | [`docs/01-requisitos.md`](docs/01-requisitos.md) | 75 RF y 53 RNF con criterio de aceptación | consulta |
| 4 | [`docs/02-arquitectura.md`](docs/02-arquitectura.md) | Modelo de datos, API, estados, ADR | consulta |
| 5 | [`docs/tecnologias-cedis.txt`](docs/tecnologias-cedis.txt) | Qué tecnología usa cada dispositivo y por qué | 10 min |

Los mockups de las 6 pantallas están en [`mockups/mockups-cedis.html`](mockups/mockups-cedis.html) — ábrelo con doble clic, no necesita servidor.

---

## Las tres ideas que sostienen todo

Si solo te llevas tres cosas de este proyecto, que sean estas:

1. **El cuello de botella no es el software: son los andenes.** La capacidad real de recibo es de 32 citas al día contra 35 que se necesitan. Se resuelve prestando un andén de embarque al recibo de 8:00 a 13:00, sin comprar nada.
2. **La regla del 90% de llenado mata a las sucursales chicas.** Una sucursal de bajo volumen tardaría más de 4 días en llenar un tortón. Se resuelve con flota heterogénea —tortón, rabón, camioneta— más un tope de antigüedad de 36 h con acta de excepción.
3. **La operación no puede depender de internet.** El handheld valida contra su copia local; la nube es réplica, no dependencia. Si se cae el enlace, el CEDIS sigue recibiendo.

---

## Reparto del trabajo

Cada bloque es **dueño exclusivo** de sus carpetas. Nadie edita archivos de otro bloque.

| Bloque | Dueño | Carpetas | Primer paso |
|:---|:---|:---|:---|
| **A · Datos** | — | `backend/app/modelos/`, `backend/app/servicios/repositorios.py`, `backend/alembic/` | Instalar Docker y PostgreSQL 16 |
| **B · API y reglas** | — | `backend/app/dominio/`, `api/`, `esquemas/`, `tests/` | Instalar pytest y correr la suite |
| **C · Frontend** | — | `frontend/` (crear), `backend/app/servicios/impresion.py` | Montar Vite + React |
| **D · Coordinación** | — | `docs/`, `mockups/` | Congelar contratos de API |

El detalle completo, con entregables y criterio de terminado, está en [`docs/03-plan-de-trabajo.md`](docs/03-plan-de-trabajo.md).

---

## Entorno — todos con lo mismo

```
python --version          ->  3.13.x
node --version            ->  v24.x
docker compose version    ->  v2.x
psql --version            ->  16.x
```

Si algo no coincide, se arregla **antes** de escribir código. Las versiones completas por bloque están en `docs/03-plan-de-trabajo.md`, sección 0.5.

### Convenciones para los cuatro

- **Español de México** en todo: variables, comentarios, commits, documentos.
- **UTF-8 sin BOM**, saltos de línea LF: `git config core.autocrlf input`
- **Fechas** `AAAA-MM-DD` en datos y API; UTC en base de datos, se convierte solo al mostrar.
- **Dinero** en MXN sin IVA.
- **Commits** con prefijo de bloque: `[A] agrega migración de citas`
- **Una rama por bloque**: `bloque-a-datos`, `bloque-b-api`, `bloque-c-frontend`

---

## Estructura del repositorio

```
.
├── README.md              <- estás aquí
├── docs/                  <- toda la documentación (bloque D)
│   ├── propuesta-cedis-v2.md    propuesta técnica y económica
│   ├── 01-requisitos.md         75 RF + 53 RNF
│   ├── 02-arquitectura.md       modelo de datos, API, ADR
│   ├── 03-plan-de-trabajo.md    reparto por bloques
│   └── tecnologias-cedis.txt    stack por dispositivo
├── mockups/
│   └── mockups-cedis.html       6 pantallas, autónomo
└── backend/
    ├── app/
    │   ├── dominio/       <- REGLAS PURAS. Sin FastAPI ni SQLAlchemy
    │   ├── modelos/       <- SQLAlchemy
    │   ├── esquemas/      <- Pydantic v2
    │   ├── api/           <- routers FastAPI
    │   └── servicios/     <- adaptadores
    ├── tests/
    ├── docker-compose.yml
    └── pyproject.toml
```

---

## Estado actual — qué está hecho y qué no

| Pieza | Estado |
|:---|:---|
| Propuesta, requisitos, arquitectura, plan | **Completos** |
| Mockups de las 6 pantallas y plano de red | **Completos** |
| Dominio del backend (1,127 líneas, reglas puras) | **Implementado**, verificado a mano |
| Pruebas | Escritas, **nunca ejecutadas** — falta instalar pytest |
| Migraciones Alembic | **Faltan** |
| Routers conectados a base real | **Faltan** |
| Frontend | **No existe** |

### Verificación manual del dominio

```
cita de 148 bultos   ->  150 min      correcto
cita de 50 bultos    ->   60 min      correcto
QR alterado          ->  rechazado    correcto
11 tarimas           ->  Tortón       correcto
10 tarimas           ->  None         correcto
 6 tarimas           ->  Rabón        correcto
```

---

## Decisiones abiertas

Tres cosas que hay que resolver antes de avanzar mucho. No las decidas solo: acuérdenlas.

1. **Estructura del código.** La arquitectura describe `src/cedis/`, pero el código vive en `backend/app/`. Son dos formas de lo mismo; hay que elegir una.
2. **Longitud de la firma del QR.** El mockup muestra 8 caracteres; la especificación dice 8 *bytes*, que en base32 son 13, y así está implementado. Recomendación: dejar 13 y corregir el mockup.
3. **Python 3.13 contra 3.12.** La propuesta y la arquitectura dicen 3.12; la máquina de referencia trae 3.13.14 y el plan de trabajo ya fija 3.13. Falta actualizar esos dos documentos.

---

## Levantar el backend

> Aún no está probado de extremo a extremo. Esto es lo que debería funcionar una vez que A entregue las migraciones.

```bash
cd backend
cp .env.example .env
docker compose up -d
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Documentación interactiva de la API en `http://localhost:8000/docs`.

---

## Una advertencia sobre los números

El retorno de inversión de la propuesta depende de un dato que **nadie ha medido**: el porcentaje de llenado actual de los camiones. El punto de equilibrio está alrededor del 80%. Por encima de eso, el ahorro de flete no existe.

Por eso la Fase 0 del proyecto es medir, y es una puerta de decisión con poder de cancelar el resto. Si alguien del jurado pregunta por el ROI, esa es la respuesta honesta: el escenario base da 5.4 meses de recuperación, y el adverso no se paga.
