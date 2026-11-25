# Plan de trabajo en equipo — Prototipo CEDIS

**Regla base:** cada bloque es dueño exclusivo de sus carpetas. Nadie edita archivos de otro bloque. Si necesitas un cambio en territorio ajeno, lo pides; no lo haces.

## Quién lleva qué

| Bloque | Quién |
|:---|:---|
| **A · Datos y persistencia** | **Delegado** a un compañero |
| **B · API y reglas de negocio** | **Delegado** a un compañero |
| **C · Frontend y documentos** | **Equipo base** |
| **D · Coordinación** | **Equipo base** |

Consecuencia directa de este reparto: **la frontera entre B y C dejó de ser interna.** Antes era un acuerdo entre dos personas del mismo equipo; ahora es la frontera entre lo delegado y lo que llevamos nosotros. Por eso el contrato de API de la sección 6 pasa de ser buena práctica a ser **la pieza que decide si el proyecto se entrega o no**.

---

## 0. Punto de partida — qué ya existe

Antes de repartir, esto es lo que el equipo recibe hecho. No se vuelve a hacer.

| Entregable | Estado | Ubicación |
|:---|:---|:---|
| Propuesta técnica y económica v2 | **Completa** | `propuesta-cedis-v2.md` |
| Tecnologías por dispositivo | **Completa** | `tecnologias-cedis.txt` |
| Requisitos: 75 RF + 53 RNF | **Completa** | `docs/01-requisitos.md` |
| Mockups de las 6 pantallas + plano | **Completos** | `mockups/mockups-cedis.html` |
| Dominio del backend (reglas puras) | **Completo y probado a mano** | `backend/app/dominio/` |
| Documento de arquitectura | **Truncado en §3 de 11** | `docs/02-arquitectura.md` |
| Migraciones, README, entorno | **No existe** | — |

### Lo que falta y bloquea a alguien

| Hueco | A quién bloquea | Dueño |
|:---|:---|:---|
| Arquitectura §4–§11 (modelo de datos, API, sync, ADR) | A y B no pueden empezar en firme | **Coordinación** |
| `pytest` no está instalado — las pruebas nunca corrieron | B | **B** |
| Sin Alembic ni migraciones | A | **A** |

### Dos inconsistencias detectadas, una resuelta y una pendiente

1. **Resuelta.** RF-005 reservaba 146 min para 148 bultos; el mockup y el dominio usan bloques de 30 min. El requisito quedó alineado a 150 min y el código ya lo cumple.
2. **Pendiente, decisión de B.** El mockup muestra la firma del QR con 8 caracteres (`K7QX4M2A`), pero la especificación dice 8 *bytes*, que en base32 son 13 caracteres, y así lo implementó el dominio (`SOKQGK7HEFRKI`). Hay que elegir: 13 caracteres y corregir el mockup, o 5 bytes y corregir el código. **Recomendación: dejar 13 caracteres**, porque 8 bytes de firma es el mínimo defendible contra falsificación; el mockup es lo barato de cambiar.

---

## 0.5 Entorno común — los cuatro con exactamente lo mismo

Esto se acuerda **antes de la primera línea de código**. Una diferencia de versión entre dos máquinas cuesta medio día de "en la mía sí funciona".

### Verificado hoy en la máquina de referencia

| Herramienta | Instalado | Lo que fija el proyecto | Estado |
|:---|:---|:---|:---|
| Python | 3.13.14 | **3.13.x** | Correcto |
| Node.js | v24.18.0 | **24.x LTS** | Correcto |
| npm | 11.16.0 | 11.x | Correcto |
| git | 2.53.0 | 2.40 o superior | Correcto |
| Docker Engine + Compose v2 | **no instalado** | 24+ / Compose v2 | **Falta — bloquea A y B** |
| PostgreSQL y cliente `psql` | **no instalado** | **16.x** | **Falta — bloquea A** |
| pytest | **no instalado** | 8.x | **Falta — bloquea B** |

### Decisión sobre la versión de Python

La propuesta y la arquitectura dicen Python **3.12**, pero la máquina de referencia trae **3.13.14** y todo el stack lo soporta. **Se fija 3.13.x** y se corrigen esos dos documentos. Hacer que cuatro personas instalen 3.12 no compra nada; lo que sí cuesta es que cada quien use la suya.

### Lo que cada quien corre antes de empezar

```
python --version          ->  3.13.x
node --version            ->  v24.x
docker compose version    ->  v2.x
psql --version            ->  16.x
```

Si algo no coincide, se arregla **antes**, no a medio sprint.

### Fijado en archivo, no en acuerdo verbal

| Archivo | Qué fija |
|:---|:---|
| `backend/pyproject.toml` | `requires-python = ">=3.13,<3.14"` |
| `backend/.python-version` | `3.13` |
| `frontend/.nvmrc` | `24` |
| `frontend/package.json` | `"engines": { "node": ">=24 <25" }` |
| `backend/docker-compose.yml` | `postgres:16-alpine`, `redis:7-alpine` |

### Convenciones que aplican a los cuatro

- **Idioma:** español de México en todo — nombres de variable, comentarios, mensajes de commit, documentos. Sin mezclar.
- **Codificación:** UTF-8 sin BOM. Saltos de línea LF, no CRLF (`git config core.autocrlf input`).
- **Fechas:** `AAAA-MM-DD` en datos y API; prosa en español en documentos.
- **Dinero:** MXN sin IVA, punto decimal, coma de miles.
- **Zona horaria:** todo en UTC en la base; se convierte a `America/Mexico_City` solo al mostrar.

---

## 1. Los cuatro bloques

```
            == DELEGADO ==              ==== EQUIPO BASE ====

+-----------------+   +-------------------+   +-------------------+
| A · DATOS       |   | B · API Y REGLAS  |   | C · FRONTEND      |
| Modelo físico   |-->| Routers · sync    |-->| Portal · tablero  |
| Migraciones     |   | OpenAPI · pruebas |   | Handheld sim      |
| Repositorios    |   |                   |   | PDF y etiquetas   |
+-----------------+   +---------+---------+   +---------+---------+
                                 |                       |
                                 |  <-- FRONTERA -->     |
                                 |   contrato de API     |
                                 +-----------+-----------+
                                             |
                                  +----------v-----------+
                                  | D · COORDINACIÓN     |
                                  | arquitectura         |
                                  | contratos · negocio  |
                                  | integración · jurado |
                                  +----------------------+
```

El flujo de dependencia es **A → B → C**, pero no es secuencial: B y C arrancan contra contratos acordados el día 1, no contra código terminado.

---

## 2. Bloque A — Datos y persistencia

**Perfil:** quien se sienta cómodo con SQL y modelado. Es el bloque con menos código y más decisiones difíciles de revertir.

### Stack del bloque

| Qué | Versión fija |
|:---|:---|
| Lenguaje | Python **3.13.x** |
| ORM | SQLAlchemy **2.0.x**, estilo declarativo con `Mapped[...]` — no el estilo 1.4 |
| Migraciones | Alembic **1.13.x** |
| Base de datos | PostgreSQL **16**, con extensión `btree_gist` habilitada |
| Pruebas | pytest **8.x** — las de A son de integración contra Postgres real en Docker, no SQLite |
| Formato y lint | ruff **0.6.x**, `line-length = 100` |
| Convención de nombres | tablas y columnas en `snake_case`, en español, **singular** (`orden_compra`, no `ordenes_compra`) |
| Llaves primarias | `UUID v7` generado en la aplicación, no `SERIAL` |
| Tipos de fecha | `TIMESTAMPTZ` siempre, nunca `TIMESTAMP` |

### Carpetas de su propiedad
```
backend/app/modelos/                    (ya hay 8 archivos: revisarlos, no empezar de cero)
backend/app/servicios/repositorios.py
backend/alembic/                        (crear)
backend/alembic.ini                     (crear)
backend/semillas/                       (crear)
```

### Entregables

| # | Entregable | Definición de terminado |
|:---|:---|:---|
| A1 | Modelo físico completo en SQLAlchemy 2.0 | Las 13 tablas de la arquitectura, con `Mapped[...]`, tipos correctos y comentarios en español |
| A2 | Las restricciones del reto **en la base de datos, no en la aplicación** | `UNIQUE` en UUID de CFDI; exclusión de traslape por andén (`EXCLUDE USING gist` con `tsrange`); `CHECK` de un solo SKU por bulto. Prueba: un `INSERT` directo que las viole falla |
| A3 | Índices | La consulta de consolidación por sucursal y la de disponibilidad por andén y fecha responden en menos de 50 ms con 100 mil bultos |
| A4 | Migraciones Alembic | `alembic upgrade head` levanta la base desde cero; `downgrade` regresa sin error |
| A5 | Repositorios | Una clase por agregado, con interfaz acordada con B. Sin lógica de negocio adentro |
| A6 | Semillas sintéticas | 35 proveedores, 32 sucursales, 2 semanas de operación simulada. Es lo que alimenta la demo del jurado |
| A7 | Respaldo y restauración | Script probado de `pg_dump` y restauración; RPO menor o igual a 5 min documentado |

### Lo que NO hace
No escribe reglas de negocio. No toca `app/dominio/` ni `app/api/`.

### Riesgo principal
La restricción de exclusión de traslapes en PostgreSQL requiere la extensión `btree_gist`. Si el entorno no la permite, hay que caer a un índice único por `(anden_id, bloque_30min)` y documentar el cambio.

---

## 3. Bloque B — API y reglas de negocio

**Perfil:** quien tenga más soltura en Python. Es el bloque con más superficie, pero arranca con ventaja: el núcleo ya está escrito.

### Stack del bloque

| Qué | Versión fija |
|:---|:---|
| Lenguaje | Python **3.13.x** |
| Framework | FastAPI **0.115.x** + Uvicorn |
| Validación | Pydantic **v2.9.x** — v2, nunca v1 ni `pydantic.v1` |
| Configuración | pydantic-settings **2.x** |
| Pruebas | pytest **8.x** + `httpx.AsyncClient`; SQLite en memoria para unitarias |
| Tipado | mypy en **modo estricto solo en `app/dominio/`**; el resto, gradual |
| Formato y lint | ruff **0.6.x**, misma config que A |
| Estilo async | `async def` en routers y adaptadores; **el dominio es síncrono y puro** |
| Regla dura | `app/dominio/` no importa FastAPI, SQLAlchemy, Redis ni `httpx`. Si lo hace, está mal ubicado |

### Carpetas de su propiedad
```
backend/app/dominio/          (1,127 líneas ya escritas: completar, no reescribir)
backend/app/api/              (5 routers esqueleto)
backend/app/esquemas/
backend/app/servicios/sat.py
backend/app/main.py
backend/app/config.py
backend/tests/
backend/pyproject.toml
```

### Entregables

| # | Entregable | Definición de terminado |
|:---|:---|:---|
| B1 | Entorno reproducible | `pip install -e ".[dev]"` instala todo y `pytest` corre. **Hoy pytest no está instalado y las pruebas nunca se ejecutaron: esto es lo primero** |
| B2 | Suite verde | Los 4 archivos de prueba pasan. Cobertura de al menos 85% en `app/dominio/` |
| B3 | Routers conectados | Los 5 routers responden contra la base real, no contra datos en memoria |
| B4 | Sincronización idempotente | Recibe un lote de eventos del handheld; reenviar el mismo lote no duplica nada. Prueba: enviar 200 eventos dos veces y verificar que el conteo no cambia |
| B5 | Paquete offline de una cita | Un solo `GET` devuelve la OC, el desglose y las firmas esperadas, listo para guardarse en el equipo |
| B6 | OpenAPI publicado | `/docs` documenta todos los endpoints con ejemplos; es el contrato que C consume |
| B7 | Decisión sobre la longitud de la firma del QR | Resolver la inconsistencia de §0 y dejar código y mockup alineados |

### Casos de prueba que no son negociables
Son las reglas que el jurado va a querer ver fallar a propósito:

- Etiqueta alterada en un solo carácter → rechazada
- Bulto 481 de 480 autorizados → `RECHAZADO_EXCEDENTE`
- El mismo QR escaneado dos veces → `DUPLICADO`, no suma
- 11 tarimas liberan tortón; 10 no liberan nada
- 5 tarimas con 40 h de antigüedad → liberan por excepción, con acta
- Cita de recibo en andén 5 que termine después de las 13:00 → rechazada

### Lo que NO hace
No crea ni modifica migraciones. No escribe React.

---

## 4. Bloque C — Frontend y documentos

**Perfil:** quien tenga ojo visual. Es el bloque con el entregable más visible ante el jurado, y el que más ventaja lleva: **los mockups ya están diseñados pantalla por pantalla**.

### Stack del bloque

| Qué | Versión fija |
|:---|:---|
| Runtime | Node **24.x LTS** |
| Lenguaje | TypeScript **5.5+**, `"strict": true` — sin `any` sin justificar |
| Framework | React **18.3** |
| Empaquetador | Vite **5.x** |
| Estilos | Tailwind **3.4** + shadcn/ui |
| Datos del servidor | TanStack Query **5.x** + `fetch` nativo — sin axios |
| Gráficas | Recharts **2.x** |
| Tiempo real | WebSocket nativo contra `cedis-ws` |
| QR | librería `qrcode` — **QR real escaneable**, no el patrón decorativo del mockup |
| PDF | Playwright headless del lado del servidor, no en el navegador |
| Formato y lint | ESLint **9** (flat config) + Prettier **3** |
| Paleta y tipografía | las del mockup: Inter + JetBrains Mono; azul `#1F5FD0`, verde `#0F7B4F`, rojo `#C02626`, ámbar `#B45309` |
| Accesibilidad | objetivos táctiles ≥44 px, contraste ≥4.5:1 — es RNF, no un extra |

### Carpetas de su propiedad
```
frontend/                              (crear)
backend/app/servicios/impresion.py     (generación de PDF y ZPL)
```

### Entregables

| # | Entregable | Definición de terminado |
|:---|:---|:---|
| C1 | Portal de proveedores | Las 3 secciones del mockup funcionando: captura de OC y UUID, carga del desglose, malla de andenes con detección de traslape visible |
| C2 | Simulador de handheld | Los tres desenlaces del mockup: aceptado, rechazo por excedente y rechazo por firma inválida. **Más el modo sin red con la cola de sincronización visible** |
| C3 | Tablero de consolidación | Semáforo por sucursal sobre posiciones de tarima, con la unidad sugerida cambiando sola y el botón de excepción en ámbar |
| C4 | Generador de etiquetas | PDF 4×6 con QR real escaneable, no el patrón decorativo del mockup |
| C5 | Relación de Embarque y Acta de Faltante | PDF tamaño carta, con QR maestro escaneable y folio de sello |
| C6 | Responsivo | El portal funciona en celular: varios proveedores chicos agendan desde ahí |

### Lo que NO hace
No define endpoints. Si falta un dato en la respuesta, lo pide a B; no inventa el campo.

### Ventaja a aprovechar
`mockups/mockups-cedis.html` tiene el CSS, los colores, la tipografía y el espaciado ya resueltos. Es copiar y conectar, no diseñar.

---

## 5. Coordinación — equipo base

No es un bloque menor: es el que decide si el proyecto se entiende. Va junto con el bloque C, así que el equipo base carga con **el entregable más visible ante el jurado y además la integración de todo**. Conviene no subestimarlo: entre C y D hay más trabajo que en A o B por separado.

### Stack del bloque

| Qué | Versión o convención fija |
|:---|:---|
| Documentos | Markdown puro, **sin notación LaTeX** — no renderiza en el visor del jurado |
| Diagramas | ASCII dentro de bloque de código, no imágenes |
| Numeración | `RF-0xx`, `RNF-0xx`, `ADR-00x`, `A-xx` para supuestos, `L-xx` para limitaciones |
| Moneda | MXN **sin IVA**, con la fecha de referencia del precio |
| Fechas en prosa | «26 de noviembre de 2026»; en tablas y datos, `AAAA-MM-DD` |
| Control de versiones | una rama por bloque, integración a `main` solo con el bloque corriendo |
| Mensajes de commit | español, imperativo, con prefijo de bloque: `[A] agrega migración de citas` |

### Carpetas de su propiedad

```
README.md
docs/
mockups/
```

| # | Entregable | Por qué es tuyo |
|:---|:---|:---|
| D1 | **Completar `docs/02-arquitectura.md` §4 a §11** | A y B están bloqueados hasta que exista el modelo de datos y los contratos de API. Es lo más urgente del proyecto |
| D2 | Congelar los contratos de API el día 1 | Sin esto, B y C no pueden trabajar en paralelo y el equipo se serializa |
| D3 | Cotización y viabilidad | Ya está en la propuesta v2; mantenerla viva si cambian los supuestos |
| D4 | Plano de red y site survey | Ya está dibujado; es tuyo defenderlo |
| D5 | Integración y demo | Levantar los tres bloques juntos y ensayar el guion ante el jurado |
| D6 | Resolver conflictos de alcance | Cuando dos bloques quieran el mismo archivo |

---

## 6. Contratos entre bloques — acordar el día 1

Esto es lo que permite trabajar en paralelo. Si no se acuerda primero, el equipo se bloquea entre sí.

### A ↔ B — interfaz de repositorios
B consume repositorios, no SQLAlchemy. Se acuerda la firma de cada método antes de que A escriba la implementación. Mientras tanto, B trabaja contra un repositorio falso en memoria.

### B ↔ C — contrato de API
Se acuerda el JSON de petición y respuesta de los 9 endpoints principales **antes de escribir código**. C trabaja contra respuestas de ejemplo en archivos hasta que B tenga el endpoint vivo.

### Todos ↔ dominio
`app/dominio/` es la única fuente de verdad de las reglas. Si una regla aparece duplicada en un router, en el frontend o en una consulta SQL, es un error, aunque funcione.

---

## 7. Orden sugerido

| Etapa | A · Datos | B · API | C · Frontend | Coordinación |
|:---|:---|:---|:---|:---|
| **1** | Revisar modelos existentes | **Instalar pytest y correr la suite** | Montar proyecto React | **Arquitectura §4–§11** |
| **2** | Migraciones y restricciones | Routers contra repositorio falso | Portal con datos de ejemplo | Congelar contratos |
| **3** | Repositorios reales | Conectar a base real | Tablero y handheld | Revisar integración |
| **4** | Semillas de demo | Sync idempotente y OpenAPI | PDF y etiquetas | Ensayar demo |
| **5** | Respaldo y restauración | Cerrar cobertura | Responsivo y pulido | Guion del jurado |

---

## 8. Reglas de convivencia

1. **Un bloque, un dueño.** Nadie edita archivos ajenos.
2. **Rama por bloque.** `bloque-a-datos`, `bloque-b-api`, `bloque-c-frontend`. Integración a `main` solo con el bloque corriendo.
3. **El contrato antes que el código.** Si cambia un contrato acordado, se avisa antes, no después.
4. **El dominio no se duplica.** Una regla vive en un solo lugar.
5. **Nada se da por terminado sin su criterio de aceptación.** Los RF del documento de requisitos ya traen el criterio escrito: se usa ese, no uno nuevo.
6. **Lo que no se midió, no se afirma.** Aplica al ROI del proyecto y aplica al desempeño del código.

---

## 9. Riesgos de coordinación

| Riesgo | Mitigación |
|:---|:---|
| La arquitectura §4–§11 no se termina y A y B avanzan a ciegas | Es la tarea 1 de coordinación. Si se atrasa, A y B acuerdan un modelo de datos provisional por escrito |
| B y C se serializan esperándose | Contratos congelados el día 1 y respuestas de ejemplo en archivos |
| **C depende de un bloque delegado.** Si B se atrasa, el entregable más visible se queda sin datos | C trabaja contra respuestas de ejemplo en archivos desde el día 1 y **nunca espera** a que B tenga el endpoint vivo. La demo del jurado debe poder correr con datos de ejemplo si hace falta |
| Dos bloques tocan `app/servicios/` | `impresion.py` es de C, `repositorios.py` es de A, `sat.py` es de B. Está repartido a propósito |
| El prototipo se demuestra con datos a mano en vez de la base real | La semilla A6 es entregable con fecha, no un extra |
| Nadie prueba la demo completa hasta el final | D5 ensaya desde la etapa 3, no en la etapa 5 |
