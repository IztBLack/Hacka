/**
 * Datos de ejemplo — bloque C trabaja contra esto desde el día 1.
 *
 * Regla del plan de trabajo: C NUNCA espera a que B tenga el endpoint vivo.
 * Cuando B entregue, se cambia el origen en `src/api/cliente.ts` y estos
 * datos quedan solo para pruebas y para la demo de respaldo.
 *
 * Todo aquí es sintético. Los folios y claves son los mismos que usan los
 * mockups y los documentos, para que una pantalla y un documento se puedan
 * comparar lado a lado.
 */

import type {
  RespuestaCita,
  RespuestaConsolidacion,
  RespuestaDisponibilidad,
} from '../tipos/api'

export const PROVEEDOR_DEMO = {
  clave: 'PRV-0147',
  razon_social: 'Alimentos del Golfo, S.A. de C.V.',
  score: 94,
}

export const OC_DEMO = {
  folio: 'OC-88213',
  uuid_cfdi: '3F2A9C41-7B8D-4E55-9A12-C6D80F4B1E77',
  n_bultos: 148,
  n_sku: 32,
  n_sucursales: 6,
  peso_kg: 11840,
  volumen_m3: 26.1,
  tarimas_equivalentes: 62,
}

/** Jueves 26 de noviembre de 2026. */
const DIA = '2026-11-26'
const h = (hora: string) => `${DIA}T${hora}:00Z`

export const DISPONIBILIDAD_DEMO: RespuestaDisponibilidad = {
  fecha: DIA,
  capacidad_citas: 36,
  reservadas: 31,
  andenes: [
    {
      numero: 1,
      tipo: 'recibo',
      ocupadas: [
        { inicio: h('08:00'), fin: h('10:00'), proveedor: 'Grupo Lala', folio_oc: 'OC-88102' },
        { inicio: h('10:30'), fin: h('12:00'), proveedor: 'Bimbo', folio_oc: 'OC-88140' },
        { inicio: h('13:00'), fin: h('15:30'), proveedor: 'Sabritas', folio_oc: 'OC-88155' },
        { inicio: h('16:00'), fin: h('18:00'), proveedor: 'Coca FEMSA', folio_oc: 'OC-88161' },
      ],
    },
    {
      numero: 2,
      tipo: 'recibo',
      ocupadas: [
        { inicio: h('08:00'), fin: h('09:30'), proveedor: 'Nestlé', folio_oc: 'OC-88110' },
        { inicio: h('10:00'), fin: h('13:00'), proveedor: 'Kimberly Clark', folio_oc: 'OC-88133' },
        { inicio: h('14:00'), fin: h('16:00'), proveedor: 'Colgate', folio_oc: 'OC-88158' },
      ],
    },
    {
      numero: 3,
      tipo: 'recibo',
      ocupadas: [
        { inicio: h('08:30'), fin: h('11:00'), proveedor: 'Procter & Gamble', folio_oc: 'OC-88118' },
        { inicio: h('11:30'), fin: h('13:30'), proveedor: 'Danone', folio_oc: 'OC-88142' },
        { inicio: h('15:00'), fin: h('17:30'), proveedor: 'Herdez', folio_oc: 'OC-88160' },
      ],
    },
    {
      numero: 4,
      tipo: 'recibo',
      ocupadas: [
        { inicio: h('09:00'), fin: h('11:00'), proveedor: 'La Costeña', folio_oc: 'OC-88121' },
        { inicio: h('11:30'), fin: h('14:00'), proveedor: 'Sigma Alimentos', folio_oc: 'OC-88147' },
        { inicio: h('15:30'), fin: h('18:00'), proveedor: 'Jumex', folio_oc: 'OC-88163' },
      ],
    },
    {
      numero: 5,
      tipo: 'flex',
      recibo_desde: '08:00',
      recibo_hasta: '13:00',
      ocupadas: [],
    },
  ],
}

/**
 * La cita que el motor devuelve para la OC de demo.
 * Nótese `reubicada: true`: el proveedor pidió el andén 2 a las 10:00 y ahí
 * ya estaba Kimberly Clark. La pantalla tiene que explicarlo, no esconderlo.
 */
export const CITA_DEMO: RespuestaCita = {
  folio_cita: 'CITA-2026-04412',
  anden_asignado: 5,
  anden_solicitado: 2,
  reubicada: true,
  motivo_reubicacion: 'traslape_en_anden_solicitado',
  inicio: h('10:00'),
  fin: h('12:30'),
  duracion_min: 150,
  duracion_calculada_min: 146,
  estado: 'confirmada',
  qr_pase_caseta: '/v1/citas/CITA-2026-04412/pase.png',
}

export const CONSOLIDACION_DEMO: RespuestaConsolidacion = {
  generado_en: h('15:20'),
  listas_para_salir: 6,
  en_alerta_36h: 3,
  tarimas_en_rack: 312,
  ocupacion_rack: 0.3,
  filas: [
    { sucursal: 'SUC-03', nombre: 'Centro', tarimas: 11, posiciones_unidad: 12, peso_kg: 11240, volumen_m3: 26.8, ocupacion: 1, unidad_sugerida: 'torton', antiguedad_horas: 14, decision: 'liberar' },
    { sucursal: 'SUC-14', nombre: 'Plaza Oriente', tarimas: 11, posiciones_unidad: 12, peso_kg: 10840, volumen_m3: 26.2, ocupacion: 1, unidad_sugerida: 'torton', antiguedad_horas: 9, decision: 'liberar' },
    { sucursal: 'SUC-07', nombre: 'Norte', tarimas: 9, posiciones_unidad: 12, peso_kg: 8960, volumen_m3: 21.4, ocupacion: 0.82, unidad_sugerida: null, antiguedad_horas: 22, decision: 'acumulando' },
    { sucursal: 'SUC-21', nombre: 'Las Flores', tarimas: 6, posiciones_unidad: 6, peso_kg: 5720, volumen_m3: 14.3, ocupacion: 1, unidad_sugerida: 'rabon', antiguedad_horas: 17, decision: 'liberar' },
    { sucursal: 'SUC-28', nombre: 'Industrial', tarimas: 5, posiciones_unidad: 6, peso_kg: 4810, volumen_m3: 11.9, ocupacion: 0.83, unidad_sugerida: 'rabon', antiguedad_horas: 41, decision: 'excepcion' },
    { sucursal: 'SUC-11', nombre: 'Sur', tarimas: 4, posiciones_unidad: 6, peso_kg: 3900, volumen_m3: 9.5, ocupacion: 0.67, unidad_sugerida: 'rabon', antiguedad_horas: 38, decision: 'excepcion' },
    { sucursal: 'SUC-19', nombre: 'Valle', tarimas: 3, posiciones_unidad: 3, peso_kg: 2740, volumen_m3: 7.1, ocupacion: 1, unidad_sugerida: 'camioneta_3_5', antiguedad_horas: 12, decision: 'liberar' },
    { sucursal: 'SUC-32', nombre: 'Lomas', tarimas: 2, posiciones_unidad: 3, peso_kg: 1880, volumen_m3: 4.8, ocupacion: 0.67, unidad_sugerida: 'camioneta_3_5', antiguedad_horas: 37, decision: 'excepcion' },
    { sucursal: 'SUC-25', nombre: 'Poniente', tarimas: 2, posiciones_unidad: 6, peso_kg: 1910, volumen_m3: 4.8, ocupacion: 0.33, unidad_sugerida: null, antiguedad_horas: 6, decision: 'acumulando' },
  ],
}

export const NOMBRE_UNIDAD: Record<string, string> = {
  torton: 'Tortón',
  rabon: 'Rabón',
  camioneta_3_5: 'Camioneta 3.5 t',
}
