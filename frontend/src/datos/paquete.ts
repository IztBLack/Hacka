/**
 * Paquete offline de la cita — arquitectura §6.4.
 *
 * Esto es lo que el handheld descarga al confirmarse la cita. Pesa poco
 * (unos 40 KB para 148 bultos) y es lo único que necesita para operar
 * una jornada entera sin red.
 *
 * Nótese lo que NO trae: la llave HMAC. Trae las FIRMAS ESPERADAS. El
 * dispositivo compara, no recalcula. Si se pierde el equipo, no se pierde
 * la llave.
 */

import type { PaqueteOffline } from '../tipos/api'

export const PAQUETE_DEMO: PaqueteOffline = {
  folio_cita: 'CITA-2026-04412',
  generado_en: '2026-11-26T15:40:00Z',
  vigente_hasta: '2026-11-27T03:00:00Z',
  kid_firma: 'k-2026-11',
  autorizado: [
    { sku: 'SKU-993201', sucursal: 'SUC-14', piezas_autorizadas: 480, piezas_recibidas: 456 },
    { sku: 'SKU-771045', sucursal: 'SUC-07', piezas_autorizadas: 240, piezas_recibidas: 0 },
    { sku: 'SKU-883417', sucursal: 'SUC-14', piezas_autorizadas: 180, piezas_recibidas: 0 },
  ],
  bultos_esperados: [
    { folio: 'B00412', sku: 'SKU-993201', descripcion: 'Atún aleta amarilla en agua 140 g', sucursal: 'SUC-14', piezas: 24, peso_kg: 18.4, volumen_m3: 0.42, firma: 'SOKQGK7HEFRKI' },
    { folio: 'B00447', sku: 'SKU-993201', descripcion: 'Atún aleta amarilla en agua 140 g', sucursal: 'SUC-14', piezas: 24, peso_kg: 18.4, volumen_m3: 0.42, firma: 'TM4XQ2PJWNDLA' },
    { folio: 'B00448', sku: 'SKU-771045', descripcion: 'Frijol bayo en salmuera 560 g', sucursal: 'SUC-07', piezas: 18, peso_kg: 22.1, volumen_m3: 0.38, firma: 'R7HZK4MQX3BVE' },
    { folio: 'B00449', sku: 'SKU-883417', descripcion: 'Chiles jalapeños rebanados 380 g', sucursal: 'SUC-14', piezas: 30, peso_kg: 16.8, volumen_m3: 0.45, firma: 'J2WPLC6NTYQ4A' },
  ],
}

/**
 * Las etiquetas que el operador se va encontrando al bajar la mercancía.
 * Son cadenas de QR tal como vienen impresas: el simulador no "sabe" nada
 * de ellas, las lee igual que el escáner.
 *
 * Tres de las cinco son legítimas. Una viene alterada y otra pertenece
 * a una OC distinta: ese es el punto de la demostración.
 */
export interface EtiquetaFisica {
  id: string
  cadena: string
  nota: string
}

const qr = (
  folio: string,
  sku: string,
  suc: string,
  pz: number,
  kg: number,
  m3: number,
  firma: string,
) => `v1|${folio}|OC-88213|PRV-0147|${suc}|${sku}|${pz}|${kg}|${m3}|${firma}`

export const ETIQUETAS_EN_CAMION: EtiquetaFisica[] = [
  {
    id: 'ok-1',
    cadena: qr('B00412', 'SKU-993201', 'SUC-14', 24, 18.4, 0.42, 'SOKQGK7HEFRKI'),
    nota: 'Etiqueta normal',
  },
  {
    id: 'ok-2',
    cadena: qr('B00448', 'SKU-771045', 'SUC-07', 18, 22.1, 0.38, 'R7HZK4MQX3BVE'),
    nota: 'Otro SKU, también autorizado',
  },
  {
    id: 'excedente',
    cadena: qr('B00447', 'SKU-993201', 'SUC-14', 24, 18.4, 0.42, 'TM4XQ2PJWNDLA'),
    nota: 'Rebasa las 480 piezas autorizadas',
  },
  {
    id: 'alterada',
    cadena: qr('B00449', 'SKU-883417', 'SUC-14', 60, 16.8, 0.45, 'J2WPLC6NTYQ4A'),
    nota: 'Piezas cambiadas de 30 a 60 sobre la etiqueta impresa',
  },
  {
    id: 'ajena',
    cadena: qr('B07781', 'SKU-610238', 'SUC-21', 12, 9.4, 0.26, 'XK3MPQ7RLVZ2D'),
    nota: 'De otra orden de compra',
  },
]
