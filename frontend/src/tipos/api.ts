/**
 * Tipos del contrato de API — docs/02-arquitectura.md §6.
 *
 * Esta es la frontera entre el bloque B (API) y el bloque C (frontend).
 * Si algo aquí no coincide con lo que devuelve el backend, el error está
 * en el contrato, no en una de las dos partes. Se avisa y se corrige aquí
 * primero; nadie "ajusta su lado" en silencio.
 *
 * Mientras B no entregue los endpoints, estas formas las cumplen los datos
 * de ejemplo de `src/datos/ejemplo.ts`.
 */

// ---------------------------------------------------------------------------
// Comunes
// ---------------------------------------------------------------------------

/** Fecha y hora en ISO 8601, siempre UTC. Se convierte solo al mostrar. */
export type FechaHoraIso = string

export type ClaveSucursal = string // "SUC-14"
export type FolioOc = string // "OC-88213"
export type FolioBulto = string // "B00412"
export type FolioCita = string // "CITA-2026-04412"

/** Error en formato RFC 7807, como lo devuelve el mapeo del §6. */
export interface ErrorApi {
  type: string
  title: string
  status: number
  detail?: string
  /** Código estable para ramificar en la interfaz, p. ej. "uuid_cfdi_duplicado". */
  codigo?: string
}

// ---------------------------------------------------------------------------
// §6.1  POST /v1/citas
// ---------------------------------------------------------------------------

export interface BultoDeclarado {
  sku: string
  sucursal: ClaveSucursal
  piezas: number
  peso_kg: number
  volumen_m3: number
}

export interface SolicitudCita {
  folio_oc: FolioOc
  uuid_cfdi: string
  anden_preferido: number
  inicio_solicitado: FechaHoraIso
  bultos: BultoDeclarado[]
}

export type EstadoCita =
  | 'provisional'
  | 'confirmada'
  | 'en_curso'
  | 'cerrada'
  | 'no_show'
  | 'cancelada'

export interface RespuestaCita {
  folio_cita: FolioCita
  anden_asignado: number
  anden_solicitado: number
  /** true cuando el motor movió la cita por traslape. Hay que decirlo en pantalla. */
  reubicada: boolean
  motivo_reubicacion?: string
  inicio: FechaHoraIso
  fin: FechaHoraIso
  /** Lo que se reserva en el andén: bloque de 30 min. */
  duracion_min: number
  /** Lo que arrojó max(60, 12 + 0.9 * n_bultos) antes de redondear. */
  duracion_calculada_min: number
  estado: EstadoCita
  qr_pase_caseta: string
}

// ---------------------------------------------------------------------------
// §6.2  GET /v1/andenes/disponibilidad
// ---------------------------------------------------------------------------

export type TipoAnden = 'recibo' | 'embarque' | 'flex'

export interface FranjaOcupada {
  inicio: FechaHoraIso
  fin: FechaHoraIso
  proveedor: string
  folio_oc: FolioOc
}

export interface AndenDisponibilidad {
  numero: number
  tipo: TipoAnden
  /** Solo en los andenes flex: ventana en que aceptan recibo. */
  recibo_desde?: string // "08:00"
  recibo_hasta?: string // "13:00"
  ocupadas: FranjaOcupada[]
}

export interface RespuestaDisponibilidad {
  fecha: string // "2026-11-26"
  capacidad_citas: number
  reservadas: number
  andenes: AndenDisponibilidad[]
}

// ---------------------------------------------------------------------------
// §6.5  POST /v1/sync/eventos
// ---------------------------------------------------------------------------

export type EstadoBulto =
  | 'ETIQUETADO'
  | 'EN_TRANSITO'
  | 'ESCANEADO_ANDEN'
  | 'RECIBIDO'
  | 'RECHAZADO'
  | 'UBICADO'
  | 'EN_ANDEN_SALIDA'
  | 'ASIGNADO_EMBARQUE'
  | 'CARGADO'
  | 'EMBARCADO'
  | 'RECIBIDO_SUCURSAL'
  | 'NO_RECIBIDO'

/**
 * Un rechazo NO es un error HTTP: es un resultado de negocio válido.
 * El endpoint responde 200 y el detalle viene por evento.
 */
export type ResultadoEvento =
  | 'aplicado'
  | 'duplicado'
  | 'rechazado_excedente'
  | 'rechazado_sku_no_solicitado'
  | 'rechazado_firma_invalida'
  | 'rechazado_sin_registro'
  | 'transicion_invalida'

export interface DestinoAcomodo {
  tipo: 'rack' | 'zona_flex' | 'cross_dock'
  ubicacion?: string // "SUC14-N2-P05"
  anden?: number
}

export interface EventoEscaneo {
  /** Lo genera el dispositivo. Es la llave de la idempotencia (§7.3). */
  uuid_evento: string
  folio_bulto: FolioBulto
  estado_destino: EstadoBulto
  ocurrido_en: FechaHoraIso
  cadena_qr: string
}

export interface ResultadoEscaneo {
  uuid_evento: string
  resultado: ResultadoEvento
  estado_final: EstadoBulto
  destino?: DestinoAcomodo
  /** Texto para el operador cuando hubo rechazo. */
  motivo?: string
  folio_acta?: string
}

export interface RespuestaSync {
  procesados: number
  resultados: ResultadoEscaneo[]
}

// ---------------------------------------------------------------------------
// §6.7  GET /v1/consolidacion
// ---------------------------------------------------------------------------

export type ClaseUnidad = 'torton' | 'rabon' | 'camioneta_3_5'

export type DecisionConsolidacion = 'liberar' | 'excepcion' | 'acumulando'

export interface FilaConsolidacion {
  sucursal: ClaveSucursal
  nombre: string
  tarimas: number
  /** Posiciones de la unidad sugerida. El límite real es este, no el peso. */
  posiciones_unidad: number
  peso_kg: number
  volumen_m3: number
  ocupacion: number // 0 a 1
  unidad_sugerida: ClaseUnidad | null
  antiguedad_horas: number
  decision: DecisionConsolidacion
}

export interface RespuestaConsolidacion {
  generado_en: FechaHoraIso
  listas_para_salir: number
  en_alerta_36h: number
  tarimas_en_rack: number
  ocupacion_rack: number // 0 a 1
  filas: FilaConsolidacion[]
}

// ---------------------------------------------------------------------------
// §6.4  GET /v1/citas/{folio}/paquete-offline
// ---------------------------------------------------------------------------

export interface LineaAutorizada {
  sku: string
  sucursal: ClaveSucursal
  piezas_autorizadas: number
  piezas_recibidas: number
}

export interface BultoEsperado {
  folio: FolioBulto
  sku: string
  descripcion: string
  sucursal: ClaveSucursal
  piezas: number
  peso_kg: number
  volumen_m3: number
  /** La firma esperada. El handheld compara, no recalcula: la llave no viaja. */
  firma: string
}

export interface PaqueteOffline {
  folio_cita: FolioCita
  generado_en: FechaHoraIso
  vigente_hasta: FechaHoraIso
  kid_firma: string
  autorizado: LineaAutorizada[]
  bultos_esperados: BultoEsperado[]
}
