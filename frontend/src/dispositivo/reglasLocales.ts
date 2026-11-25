/**
 * Reglas que corren EN EL DISPOSITIVO, sin red.
 *
 * Esto NO duplica `backend/app/dominio/`. La arquitectura (§7) dice que el
 * handheld valida contra su copia local para poder operar con el enlace
 * caído: hay dos implementaciones a propósito, una en Kotlin sobre Room y
 * otra aquí, que es la que simula al dispositivo en el prototipo.
 *
 * El servidor vuelve a validar al sincronizar y su palabra es la final.
 * Esta capa existe para que el operador tenga una respuesta en menos de
 * 150 ms y para que la descarga no se detenga si se cae el Wi-Fi.
 */

import type { PaqueteOffline, ResultadoEscaneo, ResultadoEvento } from '../tipos/api'

export interface CamposQr {
  version: string
  folio: string
  oc: string
  proveedor: string
  sucursal: string
  sku: string
  piezas: number
  peso_kg: number
  volumen_m3: number
  firma: string
}

/** Cadena sin el último campo: es sobre esto que se calcula el HMAC. */
export function cuerpoSinFirma(cadena: string): string {
  return cadena.split('|').slice(0, -1).join('|')
}

export function parsearQr(cadena: string): CamposQr | null {
  const p = cadena.split('|')
  if (p.length !== 10 || p[0] !== 'v1') return null
  const piezas = Number(p[6])
  const peso = Number(p[7])
  const volumen = Number(p[8])
  if (!Number.isFinite(piezas) || !Number.isFinite(peso) || !Number.isFinite(volumen)) return null
  return {
    version: p[0],
    folio: p[1],
    oc: p[2],
    proveedor: p[3],
    sucursal: p[4],
    sku: p[5],
    piezas,
    peso_kg: peso,
    volumen_m3: volumen,
    firma: p[9],
  }
}

/** Estado que el dispositivo lleva durante la descarga. */
export interface EstadoLocal {
  /** Folios ya aceptados. Base de la idempotencia del lado del equipo. */
  recibidos: Set<string>
  /** Piezas acumuladas por "sku|sucursal". */
  acumulado: Map<string, number>
  /** Ocupación del embarque abierto de cada sucursal, 0 a 1. */
  ocupacionEmbarque: Record<string, number>
}

export function estadoInicial(paquete: PaqueteOffline): EstadoLocal {
  const acumulado = new Map<string, number>()
  for (const linea of paquete.autorizado) {
    acumulado.set(`${linea.sku}|${linea.sucursal}`, linea.piezas_recibidas)
  }
  return {
    recibidos: new Set(),
    acumulado,
    // Viene en el paquete en producción; aquí fijo para la demo.
    ocupacionEmbarque: { 'SUC-14': 0.83, 'SUC-07': 0.42, 'SUC-21': 0.15 },
  }
}

/** Umbral de cross-dock de la propuesta §B.5. */
const UMBRAL_CROSS_DOCK = 0.7

/**
 * El orden de las comprobaciones importa y es el del §5 de la arquitectura:
 * primero si la etiqueta es legible, luego si pertenece a esta orden, luego
 * si es auténtica, y hasta el final si la cantidad cabe.
 *
 * Devuelve el resultado y el estado nuevo. No muta el que recibe.
 */
export function evaluarEscaneo(
  cadena: string,
  paquete: PaqueteOffline,
  estado: EstadoLocal,
): { resultado: ResultadoEscaneo; estado: EstadoLocal } {
  const uuid_evento = crypto.randomUUID()

  const rechazo = (resultado: ResultadoEvento, motivo: string) => ({
    resultado: { uuid_evento, resultado, estado_final: 'RECHAZADO' as const, motivo },
    estado,
  })

  const campos = parsearQr(cadena)
  if (!campos) {
    return rechazo('rechazado_sin_registro', 'La etiqueta no tiene el formato del sistema.')
  }

  const esperado = paquete.bultos_esperados.find((b) => b.folio === campos.folio)

  // 1. ¿Pertenece a esta cita?
  if (!esperado) {
    return rechazo(
      'rechazado_sin_registro',
      `El bulto ${campos.folio} no está en el desglose de esta orden de compra.`,
    )
  }

  // 2. ¿La firma corresponde? El equipo compara contra la esperada, no recalcula.
  if (campos.firma !== esperado.firma || campos.piezas !== esperado.piezas) {
    return rechazo(
      'rechazado_firma_invalida',
      'La etiqueta no coincide con la que emitió el sistema. Puede estar alterada o fotocopiada.',
    )
  }

  // 3. ¿Ya se escaneó? Repetir no es error: es duplicado.
  if (estado.recibidos.has(campos.folio)) {
    return {
      resultado: {
        uuid_evento,
        resultado: 'duplicado',
        estado_final: 'RECIBIDO',
        motivo: `El bulto ${campos.folio} ya se había recibido. No se cuenta dos veces.`,
      },
      estado,
    }
  }

  // 4. ¿El SKU está autorizado para esa sucursal?
  const llave = `${campos.sku}|${campos.sucursal}`
  const linea = paquete.autorizado.find(
    (l) => l.sku === campos.sku && l.sucursal === campos.sucursal,
  )
  if (!linea) {
    return rechazo(
      'rechazado_sku_no_solicitado',
      `El SKU ${campos.sku} no fue solicitado para ${campos.sucursal}.`,
    )
  }

  // 5. ¿Cabe en lo autorizado?
  const yaRecibido = estado.acumulado.get(llave) ?? 0
  if (yaRecibido + campos.piezas > linea.piezas_autorizadas) {
    const excedente = yaRecibido + campos.piezas - linea.piezas_autorizadas
    return rechazo(
      'rechazado_excedente',
      `La OC autoriza ${linea.piezas_autorizadas} piezas y ya se recibieron ${yaRecibido}. Este bulto agrega ${excedente} no solicitadas.`,
    )
  }

  // Aceptado. Decide dónde va.
  const ocupacion = estado.ocupacionEmbarque[campos.sucursal] ?? 0
  const haceCrossDock = ocupacion >= UMBRAL_CROSS_DOCK

  const nuevo: EstadoLocal = {
    recibidos: new Set(estado.recibidos).add(campos.folio),
    acumulado: new Map(estado.acumulado).set(llave, yaRecibido + campos.piezas),
    ocupacionEmbarque: estado.ocupacionEmbarque,
  }

  return {
    resultado: {
      uuid_evento,
      resultado: 'aplicado',
      estado_final: 'RECIBIDO',
      destino: haceCrossDock
        ? { tipo: 'cross_dock', anden: 2 }
        : { tipo: 'rack', ubicacion: `${campos.sucursal.replace('-', '')}-N2-P05` },
    },
    estado: nuevo,
  }
}

export const ES_RECHAZO: Record<ResultadoEvento, boolean> = {
  aplicado: false,
  duplicado: false,
  rechazado_excedente: true,
  rechazado_sku_no_solicitado: true,
  rechazado_firma_invalida: true,
  rechazado_sin_registro: true,
  transicion_invalida: true,
}
