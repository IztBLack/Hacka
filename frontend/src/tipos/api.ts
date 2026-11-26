/**
 * Contrato del backend FastAPI real — espejo de `backend/app/esquemas/*.py`.
 *
 * Rutas SIN prefijo `/v1` (ver `backend/app/main.py`):
 *   /citas, /etiquetas, /recepcion, /consolidacion, /embarques, /salud
 *
 * Si el backend cambia un esquema Pydantic, se cambia aquí en el mismo PR.
 * Las pantallas NO consumen estos tipos directo: pasan por
 * `src/api/adaptadores.ts`, que traduce al modelo de vista (`tipos/vista.ts`).
 */

// ---------------------------------------------------------------------------
// Primitivos
// ---------------------------------------------------------------------------

/** `date` de Python: "2026-11-26". */
export type FechaIso = string

/**
 * `time` de Python SIN zona: "08:00:00" (o "08:00"). Es hora de pared del
 * CEDIS. Nunca se convierte con `new Date()`: se parte a minutos con
 * `minutosDeHora` y ya.
 */
export type HoraLocal = string

/** `datetime` de Python (con zona, UTC). */
export type FechaHoraIso = string

/** Error de FastAPI: `HTTPException` → `{detail: string}`; validación 422 → lista. */
export interface ErrorFastApi {
  detail:
    | string
    | Array<{ loc: (string | number)[]; msg: string; type: string }>
}

// ---------------------------------------------------------------------------
// /citas  (esquemas/citas.py)
// ---------------------------------------------------------------------------

/** POST /citas/duracion */
export interface SolicitudDuracion {
  n_bultos: number
}

export interface RespuestaDuracion {
  n_bultos: number
  duracion_minutos: number
  formula: string
}

/** POST /citas/slots */
export interface SolicitudSlots {
  fecha: FechaIso
  n_bultos: number
  incluir_anden_flex?: boolean // default true
}

export interface SlotLibre {
  anden: number
  hora_inicio: HoraLocal
  hora_fin: HoraLocal
  es_anden_flex: boolean
}

export interface RespuestaSlots {
  fecha: FechaIso
  duracion_minutos: number
  capacidad_dia: number
  total_slots: number
  slots: SlotLibre[]
}

/** POST /citas → 201. 404 proveedor/OC, 409 CFDI o andén ocupado, 503 folio. */
export interface SolicitudCita {
  proveedor: string // "PRV-0147"
  orden_compra: string // "OC-88213"
  uuid_cfdi?: string | null
  fecha: FechaIso
  anden: number // 1..5
  hora_inicio: HoraLocal
  n_bultos: number
}

export interface RespuestaCita {
  folio: string
  proveedor: string
  orden_compra: string
  fecha: FechaIso
  anden: number
  hora_inicio: HoraLocal
  hora_fin: HoraLocal
  duracion_minutos: number
  estado: string
  cfdi_validado: boolean
}

/** GET /citas/capacidad */
export interface RespuestaCapacidad {
  andenes_recibo: number
  horas_operacion: number
  capacidad_sin_anden_flex: number
  capacidad_con_anden_flex: number
  citas_requeridas: number
  deficit_sin_flex: number
  alcanza_con_flex: boolean
}

// ---------------------------------------------------------------------------
// /etiquetas  (esquemas/etiquetas.py)
// ---------------------------------------------------------------------------

export interface SolicitudEtiqueta {
  id_bulto: string
  orden_compra: string
  proveedor: string
  sucursal: string
  sku: string
  cantidad: number
  peso_kg: number
  volumen_m3: number
}

export interface SolicitudLote {
  bultos: SolicitudEtiqueta[]
}

export interface RespuestaEtiqueta {
  id_bulto: string
  cadena_qr: string
  longitud_cadena: number
  version_qr: number
  nivel_correccion: string
  modulo_mm: number
  medida_pulgadas: string
}

export interface RespuestaLote {
  total: number
  etiquetas: RespuestaEtiqueta[]
}

export interface SolicitudVerificacion {
  cadena_qr: string
}

export interface RespuestaVerificacion {
  valida: boolean
  motivo: string | null
  id_bulto: string | null
  orden_compra: string | null
  proveedor: string | null
  sucursal: string | null
  sku: string | null
  cantidad: number | null
  peso_kg: number | null
  volumen_m3: number | null
}

export interface SolicitudReimpresion {
  id_bulto: string
  motivo: string
  operador: string
}

export interface RespuestaReimpresion {
  folio_reimpresion: string
  id_bulto: string
  cadena_qr: string
  zpl: string
}

// ---------------------------------------------------------------------------
// /recepcion  (esquemas/recepcion.py)
// ---------------------------------------------------------------------------

/** Valores de `dominio.recepcion.Desenlace`. */
export type Desenlace =
  | 'ACEPTADO'
  | 'DUPLICADO'
  | 'RECHAZADO_EXCEDENTE'
  | 'RECHAZADO_SKU_NO_SOLICITADO'
  | 'RECHAZADO_FIRMA_INVALIDA'
  | 'RECHAZADO_SIN_REGISTRO'

/** POST /recepcion/escaneo. `uuid_evento` (36 chars) es la llave de idempotencia. */
export interface SolicitudEscaneo {
  cadena_qr: string
  uuid_evento: string
  cita: string
  dispositivo?: string | null
  operador?: string | null
  ocurrido_en?: FechaHoraIso | null
}

export interface DestinoSalida {
  tipo: string
  ubicacion: string
  motivo: string
}

export interface RespuestaEscaneo {
  desenlace: Desenlace | string
  id_bulto: string
  motivo: string
  sku: string | null
  cantidad: number
  destino: DestinoSalida | null
  acumulado_sku: number | null
}

export interface LineaFaltanteSalida {
  sku: string
  cantidad_solicitada: number
  cantidad_recibida: number
  cantidad_faltante: number
  importe: number
}

/** POST /recepcion/cierre/{folio_cita}. 409 si ya estaba cerrada. */
export interface RespuestaCierreCita {
  cita: string
  bultos_aceptados: number
  bultos_rechazados: number
  hay_faltantes: boolean
  folio_acta: string | null
  importe_nota_credito: number
  faltantes: LineaFaltanteSalida[]
}

export interface LineaOCEntrada {
  sku: string
  cantidad_solicitada: number
  precio_unitario?: number
}

export interface BultoEsperadoEntrada {
  id_bulto: string
  sku: string
  cantidad: number
}

/** POST /recepcion/simulacion (no toca la base). */
export interface SolicitudSimulacion {
  lineas: LineaOCEntrada[]
  esperados: BultoEsperadoEntrada[]
  escaneos: string[]
  ocupacion_embarque_abierto?: number | null
  ubicacion_rack?: string | null
}

export interface RespuestaSimulacion {
  resultados: RespuestaEscaneo[]
  recibidos_por_sku: Record<string, number>
  faltantes: LineaFaltanteSalida[]
  importe_nota_credito: number
}

// ---------------------------------------------------------------------------
// /consolidacion  (esquemas/consolidacion.py)
// ---------------------------------------------------------------------------

/** Valores de `dominio.consolidacion.ClaseUnidad`. */
export type ClaseUnidadApi = 'CAMIONETA_3_5' | 'RABON' | 'TORTON'

/** Valores de `MotivoLiberacion`. */
export type MotivoLiberacion = 'REGLA_90' | 'EXCEPCION_ANTIGUEDAD' | 'ACUMULANDO'

export interface UnidadSalida {
  clase: ClaseUnidadApi | string
  posiciones: number
  minimo_90: number
  peso_max_kg: number
  volumen_max_m3: number
  costo_viaje: number
}

/** GET /consolidacion/catalogo */
export interface RespuestaCatalogo {
  unidades: UnidadSalida[]
  volumen_tarima_m3: number
  peso_max_tarima_kg: number
  ocupacion_minima: number
  horas_antiguedad_limite: number
}

/** POST /consolidacion/evaluar */
export interface SolicitudEvaluacion {
  sucursal: string
  tarimas_acumuladas: number
  peso_kg: number
  volumen_m3: number
  antiguedad_horas: number
}

export interface RespuestaEvaluacion {
  sucursal: string
  liberar: boolean
  motivo: MotivoLiberacion | string
  requiere_acta: boolean
  detalle: string
  unidad: UnidadSalida | null
  ocupacion: number | null
}

/** Una fila de GET /consolidacion/tablero. */
export interface SemaforoSucursal {
  sucursal: string
  tarimas_acumuladas: number
  antiguedad_horas: number
  liberar: boolean
  motivo: MotivoLiberacion | string
  clase_unidad: ClaseUnidadApi | string | null
  /** 0..1, null cuando ninguna unidad cumple todavía (ACUMULANDO). */
  ocupacion: number | null
  alerta_antiguedad: boolean
}

/** GET /consolidacion/tablero */
export interface RespuestaTablero {
  total_sucursales: number
  liberables: number
  en_alerta_antiguedad: number
  filas: SemaforoSucursal[]
}

// ---------------------------------------------------------------------------
// /embarques  (esquemas/embarques.py)
// ---------------------------------------------------------------------------

/** POST /embarques/liberar */
export interface SolicitudLiberacion {
  sucursal: string
  tarimas: string[] // folios, 1..12
  peso_kg: number
  volumen_m3: number
  antiguedad_horas: number
  sello_seguridad?: string | null
  km_salida?: number | null
  operador?: string | null
  placas?: string | null
}

export interface RespuestaLiberacion {
  folio: string // "" si no se liberó
  sucursal: string
  clase_unidad: string | null
  motivo_liberacion: MotivoLiberacion | string
  liberado: boolean
  requiere_acta: boolean
  folio_acta: string | null
  ocupacion: number | null
  detalle: string
  liberado_en: FechaHoraIso | null
}

export interface DatosCartaPorte {
  permiso_sict: string | null
  configuracion_vehicular: string | null
  placas: string | null
  aseguradora: string | null
  poliza: string | null
  completo: boolean
}

/** GET /embarques/{folio}/relacion  (HTML en /relacion.html) */
export interface RespuestaRelacionEmbarque {
  folio: string
  sucursal: string
  clase_unidad: string | null
  tarimas: string[]
  peso_kg: number
  volumen_m3: number
  ocupacion: number
  qr_maestro: string
  sello_seguridad: string | null
  km_salida: number | null
  operador: string | null
  carta_porte: DatosCartaPorte
  generado_en: FechaHoraIso
}

/** POST /embarques/recepcion-sucursal */
export interface SolicitudRecepcionSucursal {
  qr_maestro: string
  sucursal: string
  tarimas_recibidas?: string[]
}

export interface RespuestaRecepcionSucursal {
  folio: string
  conciliado: boolean
  tarimas_esperadas: number
  tarimas_recibidas: number
  faltantes: string[]
}

// ---------------------------------------------------------------------------
// /salud
// ---------------------------------------------------------------------------

export interface RespuestaSalud {
  estado: string
  servicio: string
  version: string
}
