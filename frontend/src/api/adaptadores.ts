/**
 * Traducción API (tipos/api.ts) → modelo de vista (tipos/vista.ts).
 *
 * Las pantallas se escribieron contra la vista; con esto pueden pintar datos
 * reales sin reescribirse, y la demo offline sigue usando la misma forma.
 */

import type { HoraLocal, RespuestaTablero, SemaforoSucursal } from '../tipos/api'
import type {
  ClaseUnidad,
  DecisionConsolidacion,
  FilaConsolidacion,
  RespuestaConsolidacion,
} from '../tipos/vista'

// ---------------------------------------------------------------------------
// Horas: el backend manda `time` SIN zona ("08:00:00"). Es hora de pared del
// CEDIS; se trata como minutos desde medianoche, nunca con `new Date()`.
// ---------------------------------------------------------------------------

/** "08:30:00" | "08:30" → 510. */
export function minutosDeHora(hora: HoraLocal): number {
  const [hh, mm] = hora.split(':').map(Number)
  return hh * 60 + mm
}

/** 510 → "08:30:00", el formato que acepta `time` de Pydantic. */
export function horaApi(minutos: number): HoraLocal {
  const hh = String(Math.floor(minutos / 60)).padStart(2, '0')
  const mm = String(minutos % 60).padStart(2, '0')
  return `${hh}:${mm}:00`
}

// ---------------------------------------------------------------------------
// Consolidación
// ---------------------------------------------------------------------------

/** Posiciones por clase: espejo de `CATALOGO_UNIDADES` en dominio/consolidacion.py. */
const POSICIONES: Record<string, number> = { CAMIONETA_3_5: 3, RABON: 6, TORTON: 12 }

const CLASE_VISTA: Record<string, ClaseUnidad> = {
  CAMIONETA_3_5: 'camioneta_3_5',
  RABON: 'rabon',
  TORTON: 'torton',
}

function decisionDe(f: SemaforoSucursal): DecisionConsolidacion {
  if (!f.liberar) return 'acumulando'
  return f.motivo === 'EXCEPCION_ANTIGUEDAD' ? 'excepcion' : 'liberar'
}

/**
 * Sin unidad asignada (ACUMULANDO) se muestra contra la unidad más chica que
 * acomoda lo acumulado: es la meta a la que la sucursal se está llenando.
 */
function posicionesDe(f: SemaforoSucursal): number {
  if (f.clase_unidad && POSICIONES[f.clase_unidad]) return POSICIONES[f.clase_unidad]
  const meta = Object.values(POSICIONES)
    .sort((a, b) => a - b)
    .find((p) => p >= f.tarimas_acumuladas)
  return meta ?? 12
}

export function filaAVista(
  f: SemaforoSucursal,
  nombres: Record<string, string> = {},
): FilaConsolidacion {
  const posiciones = posicionesDe(f)
  return {
    sucursal: f.sucursal,
    nombre: nombres[f.sucursal] ?? '',
    tarimas: f.tarimas_acumuladas,
    posiciones_unidad: posiciones,
    peso_kg: f.peso_kg ?? null,
    volumen_m3: f.volumen_m3 ?? 0,
    ocupacion: f.ocupacion ?? Math.min(1, f.tarimas_acumuladas / posiciones),
    unidad_sugerida: f.clase_unidad ? (CLASE_VISTA[f.clase_unidad] ?? null) : null,
    antiguedad_horas: f.antiguedad_horas,
    decision: decisionDe(f),
  }
}

export function tableroAVista(
  t: RespuestaTablero,
  nombres: Record<string, string> = {},
): RespuestaConsolidacion {
  const filas = t.filas.map((f) => filaAVista(f, nombres))
  return {
    generado_en: new Date().toISOString(),
    listas_para_salir: filas.filter((f) => f.decision === 'liberar').length,
    en_alerta_36h: t.en_alerta_antiguedad,
    tarimas_en_rack: filas.reduce((s, f) => s + f.tarimas, 0),
    ocupacion_rack: 0,
    filas,
  }
}
