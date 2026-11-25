# Arquitectura del sistema YMS/WMS — CEDIS

> Documento de arquitectura para el reto "De la Orden de Compra al Embarque".
> Deriva de `propuesta-cedis-v2.md` y `tecnologias-cedis.txt`.
> Escala de diseño: **~35 camiones de proveedor/día** (≈148 bultos por camión),
> **32 sucursales**, **~20 embarques/día**, **~156 tarimas/día** de acomodo y 156 de surtido.
> Decisión central: **edge-first**. La operación vive en el nodo local del CEDIS; la nube es réplica, no dependencia.

**Stack fijo** (no se renegocia en este documento; se justifica en la sección 9):
FastAPI + Python 3.12 · PostgreSQL 16 · SQLAlchemy 2.0 · Alembic · Redis Streams ·
Docker Compose · React 18 + TypeScript · Kotlin nativo + Room + WorkManager · Ruckus R650.

---

## 1. Vista de contexto

El sistema es **un solo producto con dos despliegues** (edge y nube). Hacia afuera habla con siete
actores. Nada del flujo crítico de andén depende de un actor externo en línea.

```
          EXTERNOS FISCALES                             EXTERNOS CORPORATIVOS
  +-------------------------------+              +-------------------------------+
  |  SAT                          |              |  ERP corporativo              |
  |  Servicio de consulta de      |              |  Compras, inventario,          |
  |  estatus de CFDI 4.0 (UUID)   |              |  catalogo de SKU y sucursales  |
  +---------------+---------------+              +---------------+---------------+
                  ^                                              ^
              (2) |  HTTPS / SOAP, sincrono, timeout 4 s      (6) |  REST + SFTP de contingencia
                  |  (degradable: cita "pendiente_validacion")    |  (pull cada 15 min)
                  |                                              |
  +---------------+----------------------------------------------+---------------+
  |                                                                              |
  |                      S I S T E M A   Y M S / W M S   C E D I S               |
  |                                                                              |
  |   Momento 1          Momento 2          Momento 3        Momento 4           |
  |   Agendamiento  -->  Identificacion -->  Recepcion  -->  Almacen y Embarque  |
  |                                                                              |
  +--+--------------+-------------+--------------+-------------+-----------------+
     ^              ^             ^              |             |             ^
 (1) |          (3) |         (4) |          (5) |         (7) |         (8) |
     |              |             |              v             v             |
  +--+---------+ +--+---------+ +-+----------+ +-+----------+ +-+----------+ +-+----------+
  | Proveedor  | | PAC de     | | Cuadrilla  | | Impresoras | | Sucursal   | |Transportista|
  | (35)       | | timbrado   | | del CEDIS  | | ZT411 /    | | (32)       | | / operador |
  |            | | Facturama, | | 8 anden    | | laser      | |            | |            |
  | navegador  | | SW, Finkok | | 6 acomodo  | |            | | navegador  | | QR maestro |
  | web/celular| |            | | 2 VMT      | |            | | + escaneo  | | en caseta  |
  +------------+ +------------+ +------------+ +------------+ +------------+ +------------+
```

| # | Interaccion | Direccion | Protocolo | Sincronia | Si falla |
|:--|:---|:---|:---|:---|:---|
| 1 | El proveedor captura OC, UUID de CFDI y desglose por bulto; reserva anden; descarga etiquetas 4x6 | entrante | HTTPS + OIDC (Keycloak) | sincrono | El proveedor no agenda. No detiene la operacion del dia en curso. Kiosco en caseta como respaldo |
| 2 | Validacion del UUID del CFDI contra el SAT antes de confirmar la cita | saliente | HTTPS/SOAP | sincrono, 4 s | Cita queda `pendiente_validacion`; se revalida por job; el camion no entra sin validacion resuelta |
| 3 | Timbrado del CFDI de traslado con Complemento Carta Porte 3.1 al liberar embarque | saliente | HTTPS/REST | asincrono (cola) | La Relacion de Embarque se emite sin UUID de traslado y queda en `timbrado_pendiente`; el embarque **no** se detiene |
| 4 | Escaneo de bultos, aceptacion, rechazo, put-away dirigido, conteos | bidireccional | HTTPS/mTLS sobre Wi-Fi interno | **asincrono por diseno** | La operacion continua contra la copia local del handheld. Se vacia la cola al reconectar |
| 5 | Impresion de etiqueta 4x6 (reimpresion y kiosco) y de Relacion de Embarque | saliente | ZPL II sobre TCP 9100 · IPP para laser | sincrono | Se reintenta en otra impresora; el folio de reimpresion ya quedo registrado, no se pierde trazabilidad |
| 6 | Alta de OC y catalogos desde el ERP; devolucion de recepciones, actas y cierres parciales | bidireccional | REST (JSON) · SFTP con CSV/XML los primeros 60 dias | asincrono | Se opera con el ultimo catalogo replicado; las recepciones se acumulan y se reenvian |
| 7 | La sucursal consulta su embarque y confirma recepcion escaneando el QR maestro | bidireccional | HTTPS | sincrono | Confirmacion manual por folio; se conciliara despues |
| 8 | Pase de caseta por QR; captura de placas, sello, km y firma del operador | entrante | HTTPS (tablet de caseta) | sincrono contra el **edge** | La caseta es parte del CEDIS: si no hay internet igual funciona |

**Lo que el sistema NO hace** (frontera explicita): no emite el CFDI de ingreso del proveedor, no es el
sistema de inventario maestro (ese es el ERP), no calcula nomina ni costos de flete reales, no opera la
flota. Entrega los datos para que el transportista timbre su Carta Porte, pero no es el PAC.

---

## 2. Vista de contenedores

```
+=========================== CEDIS (on-premise, nave industrial) ==========================+
|                                                                                          |
|  +-------------------- NODO EDGE (Ubuntu Server LTS, Docker Compose) ------------------+  |
|  |                                                                                     | |
|  |  cedis-api          FastAPI 3.12 + Uvicorn  :8000   <-- toda la logica de negocio    | |
|  |  cedis-ws           FastAPI WebSocket       :8001   <-- push al tablero              | |
|  |  cedis-worker       consumidor Redis Streams        <-- eventos, actas, ZPL, PDF     | |
|  |  cedis-scheduler    APScheduler                     <-- no-show, antiguedad 36 h,    | |
|  |                                                         score, revalidacion SAT      | |
|  |  postgres           PostgreSQL 16 (RAID1 NVMe)      <-- BASE OPERATIVA               | |
|  |  redis              Redis 7 Streams + AOF           <-- cola de eventos y de salida  | |
|  |  migrator           job efimero: alembic upgrade head                                | |
|  |  nginx              TLS interno, mTLS a handhelds   :443                             | |
|  |  prometheus/grafana/loki/promtail                   <-- observabilidad local          | |
|  |  pgbackrest         respaldo + WAL a objeto                                          | |
|  +-------------------------------------+-----------------------------------------------+  |
|            ^                ^          |            ^                    ^               |
|   mTLS/HTTPS|       HTTP     |   TCP   |9100        |TCP 9100     HTTPS   |              |
|            |                |          v            |                    |               |
|  +---------+-------+  +-----+-------+  +-------------+-----+  +-----------+----------+   |
|  | HANDHELDS       |  | TABLERO DE  |  | IMPRESION         |  | TABLET DE CASETA     |   |
|  | 8 Zebra TC27    |  | CONSOLIDAC. |  | 2 Zebra ZT411 ZPL |  | pase QR, placas,     |   |
|  | 6 Honeywell     |  | PC + 27"    |  | 2 laser Brother   |  | sello, km, firma     |   |
|  |   EDA52         |  | React 18 TS |  |   HL-L5210DN IPP  |  | React 18 (misma SPA) |   |
|  | 2 Zebra VC8300  |  | WebSocket   |  +-------------------+  +----------------------+   |
|  |                 |  | Recharts    |                                                    |
|  | Kotlin + Compose|  +-------------+                                                    |
|  | Room (SQLite)   |                                                                      |
|  | WorkManager     |   RED: Ruckus R650 x16 (Wi-Fi 6, 5 GHz, 20 MHz, solo no-DFS),       |
|  | DataWedge intent|        switch L3 PoE+ 48p, WPA2-Enterprise + RADIUS, 802.11r/k/v,   |
|  | Android Keystore|        UPS 3 kVA online. Handheld y edge en VLAN 20 (operacion).    |
|  +-----------------+                                                                      |
+==========================================+===============================================+
                                           |
                        Fibra 300 Mbps + failover LTE (router dual WAN)
                        - replicacion logica de PostgreSQL (puerto 5432 sobre VPN)
                        - salida HTTPS a SAT, PAC y ERP
                                           |
+==========================================v===============================================+
|                                  N U B E  (replica, no dependencia)                       |
|                                                                                           |
|  portal-web        React 18 + TS + Vite + Tailwind + shadcn/ui  (CDN + S3/Blob)           |
|  cedis-api-cloud   MISMA imagen de FastAPI, perfil `cloud`: solo agendamiento,            |
|                    identificacion, BI y consultas. NO atiende escaneos.                   |
|  postgres-replica  suscriptor de replicacion logica (solo lectura)                        |
|  keycloak          OIDC: autoservicio de los 35 proveedores y 32 sucursales                |
|  pdf-renderer      Playwright headless: etiquetas 4x6 y Relacion de Embarque               |
|  object-storage    PDF, ZPL, evidencia fotografica, respaldos pgBackRest                   |
|  sentry            errores de app (handheld y web)                                          |
+===========================================================================================+
```

### Que corre donde, y por que

| Contenedor | Corre en | Habla con | Protocolo | Razon de estar ahi |
|:---|:---|:---|:---|:---|
| `cedis-api` | **edge** | postgres, redis, handhelds, tablero, caseta | HTTPS/mTLS interno | Es el arbitro de la maquina de estados. Si vive en la nube, el ISP se vuelve punto unico de falla del CEDIS |
| `postgres` | **edge** | `cedis-api`, replica en nube | TCP 5432 / replicacion logica | La verdad operativa del dia esta en el CEDIS. La nube recibe cambios, no los origina |
| `redis` | **edge** | `cedis-api`, `cedis-worker` | RESP | Desacopla el ACK del escaneo (debe ser < 150 ms) del trabajo lento: acta, ZPL, timbrado, ERP |
| `cedis-worker` | **edge** | redis, impresoras, PAC, ERP | RESP, TCP 9100, HTTPS | Lo que sale a internet nunca bloquea al operador en el anden |
| Handheld (app Kotlin) | **dispositivo** | `cedis-api` | HTTPS/mTLS, lotes | Valida **contra Room local**: firma HMAC, SKU, cantidad, destino. Trabaja con red o sin ella |
| Tablero | **PC de oficina** | `cedis-ws`, `cedis-api` | WebSocket + HTTPS | El jefe de embarques lo ve de pie, de lejos; necesita push, no polling |
| `portal-web` | **nube** | `cedis-api-cloud` | HTTPS | Los 35 proveedores estan fuera de la red del CEDIS. No se les abre un puerto a la nave |
| `keycloak` | **nube** | portal, API | OIDC | Autoservicio de contrasenas de 67 organizaciones externas no se administra a mano |
| `pdf-renderer` | **nube** | object-storage | HTTPS | Playwright pesa RAM; el edge tiene 32 GB dedicados a la operacion, no a renderizar PDF |
| Impresoras | **CEDIS** | `cedis-worker` | **ZPL II sobre TCP 9100** | El backend genera el ZPL, no el driver: la etiqueta es identica en las dos ZT411 y es reproducible y auditable |

**Regla de dependencia entre contenedores:** el edge puede operar con la nube caida; la nube **no** puede
operar sin el edge mas que en modo lectura y agendamiento. Esa asimetria es deliberada y es la tesis de
la seccion 9, ADR-001.

---

## 3. Vista de componentes del backend (arquitectura hexagonal)

Un solo paquete desplegable (`cedis`), organizado por **feature-first** con frontera explicita de puertos
y adaptadores. La direccion de dependencia es siempre hacia dentro: adaptadores -> aplicacion -> dominio.
El dominio no importa FastAPI, SQLAlchemy, Redis ni `httpx`.

```
src/cedis/
|
+-- dominio/                         # reglas puras. CERO imports de framework.
|   +-- comun/
|   |   +-- identificadores.py        FolioBulto, FolioCita, ClaveSucursal, Sku, UuidCfdi
|   |   +-- rangos.py                 VentanaTiempo (traslape, duracion)
|   |   +-- errores.py                ErrorDominio y jerarquia (ReglaViolada, TransicionInvalida)
|   +-- agendamiento/
|   |   +-- cita.py                   Cita (entidad): reservar, confirmar, no_show, cerrar
|   |   +-- anden.py                  Anden, AndenFlex (ventana de recibo 08:00-13:00)
|   |   +-- politica_duracion.py      duracion = max(60, 12 + 0.9 * n_bultos)  [minutos]
|   |   +-- politica_prioridad.py     score >= 90 -> ventana de 45 min; prioridad de reserva
|   +-- identificacion/
|   |   +-- bulto.py                  Bulto (entidad raiz). Un SKU, invariante estructural
|   |   +-- etiqueta.py               Etiqueta, SecuenciaReimpresion
|   |   +-- payload_qr.py             armado y parseo canonico del payload (sin criptografia)
|   |   +-- politica_pureza.py        un bulto = un SKU; rechaza desglose mixto
|   +-- recepcion/
|   |   +-- maquina_estados.py        TABLA de transiciones del bulto. El arbitro unico
|   |   +-- recepcion.py              agregado de la recepcion de una cita
|   |   +-- politica_excedente.py     cantidad recibida > solicitada -> rechazo
|   |   +-- politica_faltante.py      delta al cierre -> acta + cierre parcial de OC
|   |   +-- acta.py                   Acta (faltante, rechazo, dano, correccion, excepcion)
|   +-- almacen/
|   |   +-- tarima.py                 Tarima: tope 1,000 kg, un destino por tarima
|   |   +-- ubicacion.py              Ubicacion, ZonaFlex, capacidad y ocupacion
|   |   +-- politica_putaway.py       rack home -> zona flex -> alerta
|   |   +-- politica_crossdock.py     embarque abierto de la sucursal con ocupacion >= 70%
|   +-- embarque/
|       +-- embarque.py               Embarque: posiciones, peso, volumen, ocupacion
|       +-- selector_unidad.py        Torton 12 / Rabon 6 / Camioneta 3 posiciones
|       +-- politica_liberacion.py    1) >=90%  2) antiguedad >=36 h + acta  3) milk-run
|       +-- relacion_embarque.py      folio, QR maestro, sello, km, datos Carta Porte
|
+-- aplicacion/
|   +-- puertos/
|   |   +-- entrada/                  contratos de caso de uso (input/output DTO)
|   |   |   +-- agendar_cita.py        AgendarCita, EntradaAgendarCita, SalidaAgendarCita
|   |   |   +-- consultar_disponibilidad.py
|   |   |   +-- generar_etiquetas.py
|   |   |   +-- armar_paquete_offline.py
|   |   |   +-- sincronizar_eventos.py
|   |   |   +-- cerrar_recepcion.py
|   |   |   +-- consultar_consolidacion.py
|   |   |   +-- liberar_embarque.py
|   |   |   +-- generar_relacion_embarque.py
|   |   |   +-- reimprimir_etiqueta.py
|   |   |   +-- dirigir_putaway.py
|   |   +-- salida/                   capacidades, NO tecnologias
|   |       +-- repositorio_citas.py          RepositorioCitasPuerto
|   |       +-- repositorio_bultos.py         RepositorioBultosPuerto
|   |       +-- repositorio_eventos.py        RepositorioEventosPuerto (registrar idempotente)
|   |       +-- repositorio_embarques.py       RepositorioEmbarquesPuerto
|   |       +-- repositorio_ubicaciones.py     RepositorioUbicacionesPuerto
|   |       +-- repositorio_actas.py           RepositorioActasPuerto
|   |       +-- unidad_trabajo.py               UnidadTrabajoPuerto (transaccion explicita)
|   |       +-- validador_cfdi.py              ValidadorCfdiPuerto     (estatus del UUID)
|   |       +-- timbrado.py                     TimbradoPuerto          (Carta Porte 3.1)
|   |       +-- erp.py                          ErpPuerto               (OC, catalogos, cierres)
|   |       +-- impresora_etiquetas.py          ImpresoraEtiquetasPuerto
|   |       +-- generador_documentos.py         GeneradorDocumentosPuerto (PDF)
|   |       +-- publicador_eventos.py           PublicadorEventosPuerto
|   |       +-- firmante_qr.py                  FirmanteQrPuerto / VerificadorQrPuerto
|   |       +-- almacen_llaves.py               AlmacenLlavesPuerto     (kid -> secreto)
|   |       +-- notificador.py                  NotificadorPuerto       (compras, gerencia)
|   |       +-- reloj.py                         RelojPuerto
|   |       +-- generador_id.py                  GeneradorIdPuerto
|   +-- casos_uso/                    orquestacion pura, inyeccion por constructor
|       +-- agendar_cita.py            AgendarCitaCasoUso
|       +-- consultar_disponibilidad_andenes.py
|       +-- generar_etiquetas.py
|       +-- armar_paquete_offline.py
|       +-- sincronizar_lote_eventos.py          <-- el corazon de la idempotencia
|       +-- cerrar_recepcion.py
|       +-- consultar_consolidacion.py
|       +-- liberar_embarque.py
|       +-- generar_relacion_embarque.py
|       +-- reimprimir_etiqueta.py
|       +-- dirigir_putaway.py
|       +-- recalcular_score_proveedor.py
|
+-- adaptadores/
|   +-- entrada/
|   |   +-- http/                     FastAPI: routers, esquemas Pydantic v2, mapeo de errores
|   |   |   +-- v1/citas.py, andenes.py, etiquetas.py, sync.py, recepcion.py,
|   |   |       consolidacion.py, embarques.py, salud.py
|   |   |   +-- dependencias.py        auth OIDC, mTLS del dispositivo, unidad de trabajo
|   |   |   +-- mapeo_errores.py       ErrorDominio -> codigo HTTP + cuerpo de error
|   |   +-- websocket/tablero.py      push de consolidacion
|   |   +-- consumidores/             Redis Streams: eventos, impresion, timbrado, erp
|   |   +-- cli/                      backfill, reproceso de cola, simulador de handheld
|   +-- salida/
|       +-- postgres/                 SQLAlchemy 2.0 (tipado, `Mapped[...]`), modelos ORM
|       |   +-- modelos.py             tablas (seccion 4). Separadas de las entidades
|       |   +-- mapeadores.py          ORM <-> entidad de dominio, en los dos sentidos
|       |   +-- repositorio_*.py       implementaciones de los puertos de repositorio
|       |   +-- unidad_trabajo_sa.py   UnidadTrabajoSqlAlchemy
|       +-- sat/validador_cfdi_sat.py           cliente SOAP + cache + corto-circuito
|       +-- pac/timbrado_facturama.py           CFDI de traslado + Carta Porte 3.1
|       +-- erp/cliente_rest.py, cliente_sftp.py (contingencia por archivo plano)
|       +-- impresion/zpl/
|       |   +-- plantilla_etiqueta_4x6.py       ^XA ... ^XZ generado aqui, no por driver
|       |   +-- impresora_tcp9100.py
|       +-- documentos/renderizador_playwright.py
|       +-- redis/publicador_streams.py
|       +-- cripto/firmante_hmac.py             HMAC-SHA256 truncado (seccion 8)
|       +-- llaves/almacen_llaves_archivo.py    secreto montado, cifrado en reposo
|       +-- notificacion/correo_smtp.py
|       +-- sistema/reloj_utc.py, generador_uuid.py
|
+-- composicion/
|   +-- contenedor.py                 UNICA raiz de cableado. Ensambla puertos -> casos de uso
|   +-- perfiles.py                   perfil `edge` (todo) vs `cloud` (sin escaneo ni put-away)
|
+-- infra/
    +-- configuracion.py              pydantic-settings, 12-factor
    +-- observabilidad.py             structlog -> Loki, metricas Prometheus, Sentry
    +-- migraciones/                  Alembic: env.py + versions/
```

### Como se ve el flujo critico atravesando el hexagono

```
Handheld --POST /v1/sync/eventos--> [adaptadores.entrada.http.v1.sync]
                                        | valida esquema Pydantic, extrae id_dispositivo del mTLS
                                        v
                                   [casos_uso.sincronizar_lote_eventos.SincronizarLoteEventosCasoUso]
                                        | por cada evento, en una transaccion:
                                        |   RepositorioEventosPuerto.registrar(evento)   -> aplicado|duplicado
                                        |   dominio.recepcion.maquina_estados.transicion(bulto, destino)
                                        |   RepositorioBultosPuerto.guardar(bulto)
                                        |   PublicadorEventosPuerto.publicar(BultoRecibido)
                                        v
                       [salida.postgres.repositorio_eventos]  [salida.redis.publicador_streams]
                                        |                                 |
                                        v                                 v
                                   PostgreSQL 16                      Redis Streams
                                                                          |
                                                     [entrada.consumidores.eventos] --> acta, ZPL,
                                                                                        ERP, tablero
```

Los tres puntos que hacen que esto sea hexagonal y no "capas con nombres bonitos":

1. `maquina_estados.transicion()` es una **funcion pura** sobre un `Bulto` y un estado destino. Se prueba
   con 0 mocks y 0 base de datos. Las 23 transiciones de la seccion 5 son su tabla de verdad.
2. `SincronizarLoteEventosCasoUso` no conoce HTTP: recibe `EntradaSincronizarEventos` (lista de DTO) y
   devuelve `SalidaSincronizarEventos` (resultado por evento). El mismo caso de uso lo invoca el
   consumidor de Redis para reproceso y el CLI para backfill, sin tocar HTTP.
3. `ValidadorCfdiPuerto` tiene **dos** implementaciones en produccion: `ValidadorCfdiSat` y
   `ValidadorCfdiDegradado` (devuelve `pendiente_validacion` cuando el SAT no responde). El caso de uso
   no cambia; el contenedor decide. Esa es la razon practica de tener el puerto.

---

## 4. Modelo de datos

PostgreSQL 16. Nombres en español, `snake_case`, **singular**. Llaves primarias `UUID v7` generadas en la aplicación (ordenables por tiempo, sin exponer conteo). Todas las marcas de tiempo son `TIMESTAMPTZ` en UTC.

### 4.1 Tablas

**`proveedor`**

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `clave` | `text` | `UNIQUE NOT NULL` — `PRV-0147` |
| `razon_social` | `text` | `NOT NULL` |
| `rfc` | `char(13)` | `UNIQUE NOT NULL` |
| `score` | `smallint` | `NOT NULL DEFAULT 70`, `CHECK (score BETWEEN 0 AND 100)` |
| `activo` | `boolean` | `NOT NULL DEFAULT true` |
| `creado_en` | `timestamptz` | `NOT NULL DEFAULT now()` |

**`sucursal`**

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `clave` | `text` | `UNIQUE NOT NULL` — `SUC-14` |
| `nombre` | `text` | `NOT NULL` |
| `rack_home` | `smallint` | `UNIQUE NOT NULL`, `CHECK (rack_home BETWEEN 1 AND 32)` |
| `km_ruta` | `numeric(6,1)` | `NOT NULL` — alimenta el costo de flete |

**`orden_compra`**

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `folio` | `text` | `UNIQUE NOT NULL` — `OC-88213` |
| `proveedor_id` | `uuid` | FK → `proveedor(id)`, `NOT NULL` |
| `estado` | `text` | `NOT NULL`, `CHECK (estado IN ('abierta','cerrada_total','cerrada_parcial','cancelada'))` |
| `emitida_en` | `timestamptz` | `NOT NULL` |

**`orden_compra_linea`** — el autorizado contra el que se valida el excedente

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `orden_compra_id` | `uuid` | FK → `orden_compra(id)`, `NOT NULL` |
| `sku` | `text` | `NOT NULL` |
| `sucursal_id` | `uuid` | FK → `sucursal(id)`, `NOT NULL` |
| `piezas_autorizadas` | `integer` | `NOT NULL CHECK (piezas_autorizadas > 0)` |
| `piezas_recibidas` | `integer` | `NOT NULL DEFAULT 0` |
| | | `UNIQUE (orden_compra_id, sku, sucursal_id)` |

**`cfdi`**

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `uuid_fiscal` | `uuid` | **`UNIQUE NOT NULL`** — la restricción que el reto exige |
| `orden_compra_id` | `uuid` | FK → `orden_compra(id)`, `NOT NULL` |
| `estatus_sat` | `text` | `NOT NULL`, `CHECK (estatus_sat IN ('vigente','cancelado','no_encontrado','pendiente_validacion'))` |
| `validado_en` | `timestamptz` | nulo mientras esté pendiente |

**`anden`**

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `numero` | `smallint` | `UNIQUE NOT NULL`, 1 a 7 |
| `tipo` | `text` | `CHECK (tipo IN ('recibo','embarque','flex'))` |
| `recibo_desde` | `time` | nulo salvo en `flex` → `08:00` |
| `recibo_hasta` | `time` | nulo salvo en `flex` → `13:00` |

**`cita`** — aquí vive la restricción de traslape

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `folio` | `text` | `UNIQUE NOT NULL` |
| `orden_compra_id` | `uuid` | FK, `NOT NULL` |
| `cfdi_id` | `uuid` | FK → `cfdi(id)`, `UNIQUE NOT NULL` — un CFDI, una cita |
| `anden_id` | `uuid` | FK → `anden(id)`, `NOT NULL` |
| `ventana` | `tstzrange` | `NOT NULL` — inicio y fin en un solo campo |
| `n_bultos` | `integer` | `NOT NULL CHECK (n_bultos > 0)` |
| `estado` | `text` | `CHECK (estado IN ('provisional','confirmada','en_curso','cerrada','no_show','cancelada'))` |

```sql
-- La regla "no dos entregas en el mismo andén y horario" NO vive en Python.
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE cita ADD CONSTRAINT cita_sin_traslape
  EXCLUDE USING gist (
    anden_id WITH =,
    ventana  WITH &&
  ) WHERE (estado IN ('provisional','confirmada','en_curso'));
```

> Los 15 minutos de maniobra se incluyen **dentro** de `ventana` al reservar. Así el motor de exclusión los respeta sin lógica extra.

**`bulto`**

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `folio` | `text` | `UNIQUE NOT NULL` — `B00412` |
| `cita_id` | `uuid` | FK → `cita(id)`, `NOT NULL` |
| `sku` | `text` | `NOT NULL` — **uno solo: la pureza es estructural, no una validación** |
| `sucursal_id` | `uuid` | FK, `NOT NULL` |
| `piezas` | `integer` | `NOT NULL CHECK (piezas > 0)` |
| `peso_kg` | `numeric(8,2)` | `NOT NULL CHECK (peso_kg > 0)` |
| `volumen_m3` | `numeric(6,3)` | `NOT NULL` |
| `estado` | `text` | `NOT NULL` — ver §5 |
| `tarima_id` | `uuid` | FK → `tarima(id)`, nulo hasta el put-away |

> La pureza por bulto no necesita un `CHECK`: la tabla tiene **una sola columna `sku`**. Un bulto mixto es inexpresable. Eso es más fuerte que validarlo.

**`etiqueta`**

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `bulto_id` | `uuid` | FK, `NOT NULL` |
| `secuencia` | `smallint` | `NOT NULL DEFAULT 1` — 2 en adelante = reimpresión |
| `kid` | `text` | `NOT NULL` — identificador de la llave que firmó |
| `firma` | `text` | `NOT NULL` |
| `motivo_reimpresion` | `text` | nulo en la original |
| | | `UNIQUE (bulto_id, secuencia)` |

**`evento_bulto`** — la bitácora, y el mecanismo de idempotencia

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `uuid_evento` | `uuid` | **`UNIQUE NOT NULL`** — generado en el handheld |
| `bulto_id` | `uuid` | FK, `NOT NULL` |
| `estado_destino` | `text` | `NOT NULL` |
| `dispositivo_id` | `text` | `NOT NULL` |
| `operador_id` | `uuid` | FK → `usuario(id)` |
| `ocurrido_en` | `timestamptz` | `NOT NULL` — hora del **dispositivo** |
| `registrado_en` | `timestamptz` | `NOT NULL DEFAULT now()` — hora del servidor |
| `hash_previo` | `bytea` | cadena de resúmenes: bitácora inmutable (RNF) |

> `ocurrido_en` y `registrado_en` son distintos a propósito: la diferencia entre ambos **es** la métrica de retraso de sincronización.

**`tarima`**

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `folio` | `text` | `UNIQUE NOT NULL` — `T-0441` |
| `sucursal_id` | `uuid` | FK, `NOT NULL` — **una tarima, un destino** |
| `ubicacion_id` | `uuid` | FK → `ubicacion(id)`, nulo si va en cross-dock |
| `embarque_id` | `uuid` | FK → `embarque(id)`, nulo hasta asignarse |
| `peso_kg` | `numeric(8,2)` | `NOT NULL CHECK (peso_kg <= 1000)` |
| `armada_en` | `timestamptz` | `NOT NULL` — de aquí sale la antigüedad de 36 h |

**`ubicacion`**

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `clave` | `text` | `UNIQUE NOT NULL` — `SUC14-N2-P05` |
| `sucursal_id` | `uuid` | FK, nulo en zona flex |
| `zona` | `text` | `CHECK (zona IN ('rack_home','flex','anden_salida'))` |
| `ocupada` | `boolean` | `NOT NULL DEFAULT false` |

**`embarque`**

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `folio` | `text` | `UNIQUE NOT NULL` — `REL-2026-01184` |
| `sucursal_id` | `uuid` | FK, `NOT NULL` |
| `clase_unidad` | `text` | `CHECK (clase_unidad IN ('torton','rabon','camioneta_3_5'))` |
| `estado` | `text` | `CHECK (estado IN ('abierto','cargando','cerrado','en_transito','recibido'))` |
| `motivo_liberacion` | `text` | `CHECK (motivo_liberacion IN ('regla_90','excepcion_antiguedad','milk_run'))` |
| `placas` | `text` | nulo hasta el cierre |
| `sello` | `text` | nulo hasta el cierre |
| `km_salida` | `integer` | nulo hasta el cierre |
| `uuid_carta_porte` | `uuid` | nulo si `timbrado_pendiente` |

> Solo puede haber un embarque `abierto` por sucursal:
> `CREATE UNIQUE INDEX embarque_abierto_unico ON embarque (sucursal_id) WHERE estado = 'abierto';`

**`acta`**

| Columna | Tipo | Restricción |
|:---|:---|:---|
| `id` | `uuid` | PK |
| `folio` | `text` | `UNIQUE NOT NULL` — `ACT-2026-0392` |
| `tipo` | `text` | `CHECK (tipo IN ('faltante','rechazo','dano','correccion','excepcion_antiguedad','reimpresion'))` |
| `cita_id` / `embarque_id` / `bulto_id` | `uuid` | FK, al menos uno `NOT NULL` |
| `detalle` | `jsonb` | `NOT NULL` — delta por SKU, importe, motivo |
| `autorizado_por` | `uuid` | FK → `usuario(id)` — obligatorio en `excepcion_antiguedad` |

**`usuario`** — operadores, jefes, compradores y administradores, con su rol.

### 4.2 Índices que importan

```sql
-- Consolidación por sucursal: la consulta del tablero, cada 5 s
CREATE INDEX tarima_consolidacion ON tarima (sucursal_id, armada_en)
  WHERE embarque_id IS NULL;

-- Disponibilidad de andenes por día
CREATE INDEX cita_anden_ventana ON cita USING gist (anden_id, ventana);

-- Validación de excedente en el andén: debe ser instantánea
CREATE INDEX ocl_busqueda ON orden_compra_linea (orden_compra_id, sku, sucursal_id);

-- Bultos pendientes de una cita, para el paquete offline
CREATE INDEX bulto_por_cita ON bulto (cita_id, estado);
```

---

## 5. Máquina de estados del bulto

El árbitro único es `dominio/recepcion/maquina_estados.py`. Ninguna otra capa cambia un estado.

```
                    [el proveedor genera la etiqueta]
                                  |
                                  v
                            ETIQUETADO
                                  |  (sale del proveedor)
                                  v
                            EN_TRANSITO
                                  |  (escaneo en andén)
                                  v
                          ESCANEADO_ANDEN
                        /         |          \
          firma inválida|      coincide       | excedente / SKU
          o sin registro|                     | no solicitado
                        v         v           v
                   RECHAZADO   RECIBIDO    RECHAZADO
                        |         |            |
                (vuelve a la      |     (vuelve a la unidad)
                 unidad)          |
                                  |
                        +---------+---------+
                        |                   |
                 cross-dock >=70%     acomodo normal
                        |                   |
                        v                   v
                  EN_ANDEN_SALIDA        UBICADO
                        |                   |
                        +---------+---------+
                                  |
                                  v
                        ASIGNADO_EMBARQUE
                                  |  (escaneo al cargar)
                                  v
                              CARGADO
                                  |  (cierre del embarque)
                                  v
                            EMBARCADO
                                  |  (QR maestro en destino)
                                  v
                       RECIBIDO_SUCURSAL   [terminal]

  NO_RECIBIDO  [terminal]  <- al cerrar la cita, lo que nunca se escaneó;
                              genera acta de faltante
```

### 5.1 Tabla de transiciones

| Desde | Hacia | Quién dispara | Qué la bloquea |
|:---|:---|:---|:---|
| `ETIQUETADO` | `EN_TRANSITO` | portal, al confirmar salida | cita no confirmada |
| `EN_TRANSITO` | `ESCANEADO_ANDEN` | handheld | cita no `en_curso` |
| `ESCANEADO_ANDEN` | `RECIBIDO` | handheld | excedente, SKU ajeno, firma inválida |
| `ESCANEADO_ANDEN` | `RECHAZADO` | handheld | — (genera acta automática) |
| `RECIBIDO` | `UBICADO` | handheld o VMT | ubicación ocupada |
| `RECIBIDO` | `EN_ANDEN_SALIDA` | sistema (cross-dock) | embarque de la sucursal por debajo del 70% |
| `UBICADO` | `ASIGNADO_EMBARQUE` | jefe de embarques | embarque no liberado |
| `EN_ANDEN_SALIDA` | `ASIGNADO_EMBARQUE` | jefe de embarques | — |
| `ASIGNADO_EMBARQUE` | `CARGADO` | handheld, al subir | embarque cerrado |
| `CARGADO` | `EMBARCADO` | sistema, al cerrar | faltan sello, placas o km |
| `EMBARCADO` | `RECIBIDO_SUCURSAL` | sucursal, QR maestro | — |
| `EN_TRANSITO` | `NO_RECIBIDO` | sistema, al cerrar la cita | — |

**Reglas de la máquina**

1. `RECHAZADO`, `RECIBIDO_SUCURSAL` y `NO_RECIBIDO` son **terminales**. No hay salida.
2. Nunca se retrocede. Corregir un error es un acta de corrección, no un paso atrás.
3. La idempotencia se apoya en `UNIQUE (uuid_evento)`, no en `(bulto_id, estado_destino)`: la segunda opción impediría reintentos legítimos. La máquina trata la transición repetida como **`DUPLICADO`, no como error**.

---

## 6. Contratos de API

Prefijo `/v1`. Autenticación: OIDC (portal) o mTLS de dispositivo (handheld). Errores en formato RFC 7807.

### 6.1 `POST /v1/citas` — agendar

```json
{
  "folio_oc": "OC-88213",
  "uuid_cfdi": "3f2a9c41-7b8d-4e55-9a12-c6d80f4b1e77",
  "anden_preferido": 2,
  "inicio_solicitado": "2026-11-26T16:00:00Z",
  "bultos": [
    {"sku": "SKU-993201", "sucursal": "SUC-14", "piezas": 24,
     "peso_kg": 18.4, "volumen_m3": 0.42}
  ]
}
```

**201** — la cita quedó, posiblemente en otro andén:

```json
{
  "folio_cita": "CITA-2026-04412",
  "anden_asignado": 5,
  "anden_solicitado": 2,
  "reubicada": true,
  "motivo_reubicacion": "traslape_en_anden_solicitado",
  "inicio": "2026-11-26T16:00:00Z",
  "fin": "2026-11-26T18:30:00Z",
  "duracion_min": 150,
  "duracion_calculada_min": 146,
  "estado": "confirmada",
  "qr_pase_caseta": "/v1/citas/CITA-2026-04412/pase.png"
}
```

**409** `uuid_cfdi_duplicado` · **422** `cfdi_cancelado`, `bulto_multi_sku`, `desglose_no_cuadra_con_oc` · **202** `pendiente_validacion` cuando el SAT no respondió.

### 6.2 `GET /v1/andenes/disponibilidad?fecha=2026-11-26&duracion_min=150`

Devuelve por andén las franjas libres, marcando `tipo: "flex"` y su ventana de recibo.

### 6.3 `POST /v1/citas/{folio}/etiquetas` → `202` + `id_trabajo`

`GET /v1/trabajos/{id}` → `{"estado":"listo","pdf":"https://…/etiquetas.pdf","n_etiquetas":148}`

### 6.4 `GET /v1/citas/{folio}/paquete-offline` — lo que el handheld descarga

```json
{
  "folio_cita": "CITA-2026-04412",
  "generado_en": "2026-11-26T15:40:00Z",
  "vigente_hasta": "2026-11-27T03:00:00Z",
  "kid_firma": "k-2026-11",
  "autorizado": [
    {"sku": "SKU-993201", "sucursal": "SUC-14",
     "piezas_autorizadas": 480, "piezas_recibidas": 0}
  ],
  "bultos_esperados": [
    {"folio": "B00412", "sku": "SKU-993201", "sucursal": "SUC-14",
     "piezas": 24, "firma": "SOKQGK7HEFRKI"}
  ]
}
```

> No lleva la llave HMAC. Lleva **las firmas esperadas**. El handheld compara, no firma. Si se pierde el equipo, no se pierde la llave.

### 6.5 `POST /v1/sync/eventos` — el endpoint crítico

```json
{
  "dispositivo_id": "TC27-A04",
  "eventos": [
    {"uuid_evento": "018f3c2a-7b10-7c3e-9a44-1f2b3c4d5e6f",
     "folio_bulto": "B00412", "estado_destino": "RECIBIDO",
     "ocurrido_en": "2026-11-26T16:42:11Z",
     "cadena_qr": "v1|B00412|OC-88213|…|SOKQGK7HEFRKI"}
  ]
}
```

**200** — siempre 200 si el lote se procesó; el detalle va por evento:

```json
{
  "procesados": 1,
  "resultados": [
    {"uuid_evento": "018f3c2a-…", "resultado": "aplicado",
     "estado_final": "RECIBIDO", "destino": {"tipo": "cross_dock", "anden": 2}}
  ]
}
```

`resultado` ∈ `aplicado` · `duplicado` · `rechazado_excedente` · `rechazado_sku_no_solicitado` · `rechazado_firma_invalida` · `rechazado_sin_registro` · `transicion_invalida`.

> **Un evento rechazado no es un error HTTP.** El rechazo es un resultado de negocio válido y debe quedar registrado. Devolver 422 por un bulto excedente rompería el lote completo.

### 6.6 `POST /v1/citas/{folio}/cerrar`

Devuelve el conteo final y, si hubo delta, el folio del acta de faltante con el importe para la nota de crédito.

### 6.7 `GET /v1/consolidacion`

Por sucursal: tarimas acumuladas, peso, volumen, ocupación, unidad sugerida, antigüedad de la tarima más vieja y `decision` ∈ `liberar` · `excepcion` · `acumulando`.

### 6.8 `POST /v1/embarques` — liberar

```json
{"sucursal": "SUC-14", "clase_unidad": "torton",
 "motivo": "regla_90", "anden_salida": 2}
```

**422** `ocupacion_insuficiente` si es `regla_90` y no llega al 90%. Con `motivo: "excepcion_antiguedad"` exige `autorizado_por`.

### 6.9 `POST /v1/embarques/{folio}/cerrar`

Exige `placas`, `sello`, `km_salida` y `operador`. Devuelve el PDF de la Relación de Embarque y dispara el timbrado de la Carta Porte de forma asíncrona.

---

## 7. Sincronización offline e idempotencia

### 7.1 Qué baja al handheld y cuándo

Al confirmarse la cita y, de nuevo, al llegar el camión a caseta: el paquete de §6.4. Pesa unos 40 KB para 148 bultos. Vigencia 12 horas; vencido, el equipo exige reconectar.

### 7.2 El ciclo

```
escaneo -> verifica firma contra `kid` local      (sin red)
        -> busca el folio en `bultos_esperados`   (sin red)
        -> aplica reglas de excedente y SKU       (sin red)
        -> pinta verde o rojo                     (< 150 ms)
        -> inserta en cola Room con uuid_evento   (sin red)
                         |
                WorkManager, red disponible
                         v
        POST /v1/sync/eventos  (lotes de 50, reintento exponencial 1 s -> 5 min)
                         v
        respuesta por evento -> marca sincronizado o conflicto
```

### 7.3 Exactamente una vez, de verdad

El `uuid_evento` lo genera el **handheld**, no el servidor. En el servidor:

```sql
INSERT INTO evento_bulto (uuid_evento, bulto_id, estado_destino, ...)
VALUES (...)
ON CONFLICT (uuid_evento) DO NOTHING
RETURNING id;
```

Sin fila devuelta significa que ya estaba, y se responde `duplicado` con el estado final que ya tenía. **La idempotencia la garantiza la base de datos, no la aplicación.** Un reintento tras un timeout de red, un lote reenviado completo o un equipo restaurado desde respaldo convergen al mismo estado.

### 7.4 Conflictos

| Conflicto | Resolución |
|:---|:---|
| Dos equipos escanean el mismo bulto | Gana el primero en llegar; el segundo recibe `duplicado`. Decide el servidor, no el reloj del dispositivo |
| El estado del servidor ya avanzó más | `transicion_invalida`; el evento queda en bitácora pero no cambia nada |
| El reloj del equipo está desfasado | Se usa `registrado_en` para ordenar. `ocurrido_en` es informativo |
| La OC se canceló mientras se descargaba | Al sincronizar, los eventos se aceptan y la recepción se marca para revisión manual. **No se borra lo que ya pasó físicamente** |

### 7.5 Handheld perdido con eventos sin sincronizar

Es pérdida de datos real y no se disfraza. Mitigación: al cerrar la cita, el sistema compara lo escaneado contra `bultos_esperados` y lo faltante entra al acta de faltante. Si el equipo aparece después, sus eventos se aplican y el acta se corrige con un acta de corrección. Métrica vigilada: eventos con más de 30 min sin sincronizar.

---

## 8. Firma del QR

### 8.1 Formato

```
v1|B00412|OC-88213|PRV-0147|SUC-14|SKU-993201|24|18.4|0.42|SOKQGK7HEFRKI
└┬┘ └──┬─┘                                                  └──────┬─────┘
versión  campos canónicos, separador "|", decimales con punto     firma
```

Firma = `base32(HMAC-SHA256(llave, cadena_sin_firma)[:8])` sin relleno, en mayúsculas → **13 caracteres**.

### 8.2 Llaves

| Aspecto | Decisión |
|:---|:---|
| Almacenamiento | Secreto montado en el edge, cifrado en reposo. **Nunca viaja al handheld** |
| Identificador | `kid` tipo `k-2026-11`, guardado en `etiqueta.kid` |
| Rotación | Mensual. Se conservan 3 llaves vigentes para verificar etiquetas en tránsito |
| Verificación offline | El handheld compara contra la firma esperada del paquete, no recalcula |

### 8.3 Qué protege y qué no

**Protege:** etiqueta fabricada fuera del sistema, etiqueta fotocopiada de otro bulto, alteración de SKU, piezas o sucursal en la etiqueta impresa.

**NO protege:** el contenido físico de la caja — una etiqueta válida pegada en una caja con otro producto pasa, y eso lo detecta el conteo, no la firma. Tampoco cifra: quien lea el QR ve los datos en claro, y es a propósito, porque el operador necesita leerlos. Tampoco impide reusar una etiqueta legítima en otro bulto de la misma OC; eso lo detecta la idempotencia por folio.

---

## 9. Decisiones de arquitectura

### ADR-001 · Edge-first en vez de nube pura

**Contexto.** La v1 proponía validar cada escaneo contra un servidor en la nube. El CEDIS procesa unos 5,200 bultos diarios en 10 horas.
**Decisión.** La base operativa y la API viven en un nodo local. La nube es réplica de lectura, portal y BI.
**Alternativas.** Nube pura: más simple de operar, pero el ISP se vuelve punto único de falla del CEDIS. Híbrido con caché en el handheld y sin nodo local: no resuelve la caída del enlace para el tablero ni la impresión.
**Consecuencias.** Buenas: la operación sobrevive a la caída del enlace; validación en decenas de milisegundos. Malas: hay hardware que mantener en sitio, UPS, y una replicación que puede atrasarse; el equipo debe saber operar PostgreSQL.

### ADR-002 · Kotlin nativo en vez de React Native o Flutter

**Contexto.** El motor de escaneo de Zebra expone DataWedge y EMDK como SDK nativos.
**Decisión.** App Android nativa en Kotlin con Jetpack Compose.
**Alternativas.** React Native o Flutter con un plugin puente al SDK.
**Consecuencias.** Buenas: el escaneo llega como intent del sistema, sin puente de JavaScript; acceso directo a Room, WorkManager y Keystore. Malas: no hay reuso con el portal web; se necesita alguien con Android en el equipo.

### ADR-003 · PostgreSQL monolítico en vez de microservicios

**Contexto.** Cuatro momentos de operación que comparten entidades y necesitan transacciones entre ellos.
**Decisión.** Una base, un esquema, un desplegable, modularizado por dominio.
**Alternativas.** Un servicio por momento con base propia.
**Consecuencias.** Buenas: "recibir un bulto y decrementar el autorizado" es una transacción, no una saga; un CEDIS no justifica cuatro despliegues. Malas: no se escala por módulo; el acoplamiento hay que disciplinarlo con la frontera hexagonal, no con la red.

### ADR-004 · QR firmado en vez de QR en claro

**Contexto.** Un QR de texto plano se fotocopia y se fabrica con cualquier generador.
**Decisión.** HMAC-SHA256 truncado a 8 bytes, con `kid` y rotación mensual.
**Alternativas.** QR en claro confiando en la validación contra la OC: no detecta una etiqueta fabricada con datos plausibles. Firma asimétrica Ed25519: más larga, y no hay requisito de verificación por terceros.
**Consecuencias.** Buenas: una etiqueta no emitida por el sistema se rechaza en el andén, sin red. Malas: 13 caracteres más en el QR; hay que administrar llaves y su rotación.

### ADR-005 · Docker Compose en vez de Kubernetes

**Contexto.** Un nodo físico en una nave industrial, operado por el equipo de sistemas del CEDIS.
**Decisión.** Docker Compose con reinicio automático.
**Alternativas.** K3s o Kubernetes gestionado.
**Consecuencias.** Buenas: lo opera alguien que no es especialista; el `docker-compose.yml` se lee completo en una pantalla. Malas: sin reprogramación automática si el nodo muere — eso lo cubren el UPS y el modo degradado del handheld, no el orquestador.

### ADR-006 · El UUID del CFDI como folio único

**Contexto.** El reto pide que cada OC tenga relacionado un folio de factura y que el folio no se repita.
**Decisión.** El folio único es el **UUID fiscal del CFDI 4.0**, con `UNIQUE` en base de datos y validación contra el SAT.
**Alternativas.** Consecutivo interno del proveedor: se repite entre proveedores y no detecta factura apócrifa. Folio impreso por el proveedor: lo controla él.
**Consecuencias.** Buenas: unicidad garantizada por el SAT, no por nosotros; se detecta factura cancelada antes de que el camión entre. Malas: dependencia de un servicio externo que se cae, resuelta con el estado `pendiente_validacion`.

---

## 10. Despliegue y entornos

| Entorno | Dónde | Base | Para qué |
|:---|:---|:---|:---|
| Desarrollo | máquina de cada quien | Postgres 16 en Docker | Día a día |
| Integración | un nodo compartido | Postgres 16 + semillas | Demo del jurado y pruebas de extremo a extremo |
| Producción edge | nave del CEDIS | Postgres 16 en NVMe RAID1 | Operación |
| Producción nube | proveedor | réplica lógica de lectura | Portal, BI, respaldos |

### Migraciones

Alembic, una revisión por cambio, **nunca editada después de integrarse**. El contenedor `migrator` corre `alembic upgrade head` antes de que arranque la API. Toda migración debe tener `downgrade` probado. Las que agregan columna `NOT NULL` se hacen en tres pasos: agregar nullable, rellenar, imponer la restricción.

### Respaldo y recuperación

| Métrica | Objetivo | Cómo |
|:---|:---|:---|
| RPO | 5 min o menos | WAL continuo a almacenamiento de objetos con pgBackRest |
| RTO | 2 h o menos | Respaldo completo diario más WAL; restauración ensayada cada mes |
| Retención | 30 días | Más allá, respaldo mensual por un año |

**La restauración se ensaya.** Un respaldo que nunca se restauró no es un respaldo.

---

## 11. Riesgos de arquitectura

| Riesgo | Prob. | Impacto | Mitigación de diseño |
|:---|:---:|:---:|:---|
| El nodo edge muere a media operación | Baja | Crítico | UPS 3 kVA; el handheld sigue 8 h contra su copia local; nodo de repuesto frío con la misma imagen |
| `btree_gist` no disponible en el Postgres del cliente | Media | Alto | Alternativa: índice único por `(anden_id, bloque_30min)`, con la malla de 30 min que ya usa el motor de citas |
| La replicación lógica se atrasa y el BI muestra datos viejos | Media | Bajo | Métrica de retraso visible en Grafana; el tablero operativo lee del edge, nunca de la réplica |
| El SAT no responde durante horas | Media | Medio | Estado `pendiente_validacion` y revalidación programada; el camión no entra sin resolver |
| El PAC falla al timbrar la Carta Porte | Media | Medio | El embarque **no se detiene**; queda `timbrado_pendiente` y se reintenta. La unidad no sale sin el documento impreso, que sí se genera |
| El ERP cambia su contrato sin avisar | Alta | Alto | Adaptador aislado tras `ErpPuerto`; contingencia por archivo plano; pruebas de contrato en integración |
| Crecimiento a un segundo CEDIS | Media | Medio | El diseño es por sitio: un edge por CEDIS, una nube común. No hay estado compartido entre sitios |
| Deriva entre el dominio y lo que hace la interfaz | Alta | Medio | `app/dominio/` es fuente única; la interfaz no reimplementa reglas. Se revisa en cada integración |
