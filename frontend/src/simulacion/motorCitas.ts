/**
 * Motor de citas — SIMULACIÓN del lado del cliente.
 *
 * En producción esto NO vive aquí: lo resuelve `POST /v1/citas` en el
 * backend, donde además la restricción de exclusión de PostgreSQL impide
 * el traslape aunque la aplicación se equivoque (arquitectura §4.1).
 *
 * Existe para que el prototipo se pueda demostrar sin backend. Cuando B
 * entregue el endpoint, este archivo se borra y `Portal.tsx` llama a la API.
 */

import type { AndenDisponibilidad, FranjaOcupada } from '../tipos/vista'

export const HORA_APERTURA = 8
export const HORA_CIERRE = 18
/** Minutos entre una cita y la siguiente en el mismo andén. */
export const MINUTOS_MANIOBRA = 15

/** t = max(60, 12 + 0.9 * n), redondeado hacia arriba al bloque de 30 min. */
export function duracionMinutos(nBultos: number): { calculada: number; reservada: number } {
  const calculada = Math.max(60, Math.ceil(12 + 0.9 * nBultos))
  const reservada = Math.ceil(calculada / 30) * 30
  return { calculada, reservada }
}

/**
 * Minutos desde medianoche, hora de PARED del CEDIS.
 *
 * Acepta el ISO de la demo ("2026-11-26T08:00:00Z") o el `time` sin zona del
 * backend ("08:00:00"). En ambos casos se leen los dígitos HH:MM tal cual: la
 * "Z" de la demo NO se interpreta como UTC (no se usa `new Date()`), porque
 * convertirla a la zona del navegador correría la malla 6 horas.
 */
export function minutosDe(valor: string): number {
  const hhmm = valor.includes('T') ? valor.slice(11, 16) : valor.slice(0, 5)
  const [hh, mm] = hhmm.split(':').map(Number)
  return hh * 60 + mm
}

export function aHora(minutos: number): string {
  const hh = String(Math.floor(minutos / 60)).padStart(2, '0')
  const mm = String(minutos % 60).padStart(2, '0')
  return `${hh}:${mm}`
}

interface Rango {
  desde: number
  hasta: number
}

/**
 * Dos franjas se traslapan si se tocan en cualquier instante. Los 15 min de
 * maniobra van DENTRO del rango reservado, así que una cita que termina a
 * las 11:30 bloquea hasta las 11:45.
 */
export function hayTraslape(nueva: Rango, existentes: Rango[]): boolean {
  return existentes.some((e) => nueva.desde < e.hasta && e.desde < nueva.hasta)
}

function ocupadasComoRangos(ocupadas: FranjaOcupada[]): Rango[] {
  return ocupadas.map((f) => ({
    desde: minutosDe(f.inicio),
    hasta: minutosDe(f.fin) + MINUTOS_MANIOBRA,
  }))
}

export type MotivoRechazo =
  | 'traslape'
  | 'fuera_de_horario'
  | 'flex_cierra_temprano'
  | 'anden_de_embarque'

export interface Reserva {
  ok: true
  anden: number
  desde: number
  hasta: number
}

export interface Rechazo {
  ok: false
  motivo: MotivoRechazo
  detalle: string
}

/**
 * Intenta reservar en un andén y hora concretos. Devuelve el porqué cuando
 * no se puede: el proveedor necesita saber qué lo bloqueó, no solo que falló.
 */
export function intentarReservar(
  anden: AndenDisponibilidad,
  inicioMin: number,
  duracionMin: number,
): Reserva | Rechazo {
  const finMin = inicioMin + duracionMin

  if (inicioMin < HORA_APERTURA * 60 || finMin > HORA_CIERRE * 60) {
    return {
      ok: false,
      motivo: 'fuera_de_horario',
      detalle: `La cita terminaría a las ${aHora(finMin)} y el CEDIS cierra a las ${HORA_CIERRE}:00.`,
    }
  }

  if (anden.tipo === 'embarque') {
    return {
      ok: false,
      motivo: 'anden_de_embarque',
      detalle: `El andén ${anden.numero} es de embarque, no recibe proveedores.`,
    }
  }

  if (anden.tipo === 'flex' && anden.recibo_hasta) {
    const cierre = Number(anden.recibo_hasta.slice(0, 2)) * 60
    if (finMin > cierre) {
      return {
        ok: false,
        motivo: 'flex_cierra_temprano',
        detalle: `El andén ${anden.numero} flex solo recibe hasta las ${anden.recibo_hasta}, y esta cita terminaría a las ${aHora(finMin)}.`,
      }
    }
  }

  const rangos = ocupadasComoRangos(anden.ocupadas)
  // La nueva también lleva su maniobra al final, igual que en el backend
  // (`franja.con_maniobra`): sin esto, una cita que termina 09:00 "cabe" antes
  // de otra que empieza 09:00.
  const finConManiobra = finMin + MINUTOS_MANIOBRA
  const idx = rangos.findIndex((e) => inicioMin < e.hasta && e.desde < finConManiobra)
  if (idx >= 0) {
    const cita = anden.ocupadas[idx]
    const libreA = aHora(minutosDe(cita.fin) + MINUTOS_MANIOBRA)
    return {
      ok: false,
      motivo: 'traslape',
      detalle: `Se traslapa con ${cita.proveedor} (${cita.inicio.slice(11, 16)}–${cita.fin.slice(11, 16)}). Contando los ${MINUTOS_MANIOBRA} min de maniobra, ese andén se libera hasta las ${libreA}.`,
    }
  }

  return { ok: true, anden: anden.numero, desde: inicioMin, hasta: finMin }
}

/** El primer andén y hora donde sí cabe, buscando desde la hora pedida. */
export function primeraAlternativa(
  andenes: AndenDisponibilidad[],
  inicioMin: number,
  duracionMin: number,
): Reserva | null {
  for (let t = inicioMin; t + duracionMin <= HORA_CIERRE * 60; t += 30) {
    for (const a of andenes) {
      const r = intentarReservar(a, t, duracionMin)
      if (r.ok) return r
    }
  }
  return null
}

export function validarUuid(valor: string, yaUsados: string[]): string | null {
  const limpio = valor.trim().toUpperCase()
  const formato = /^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$/
  if (!formato.test(limpio)) {
    return 'El UUID del CFDI no tiene el formato de 36 caracteres del SAT.'
  }
  if (yaUsados.includes(limpio)) {
    return 'Ese UUID ya está registrado en otra entrega. El folio fiscal no se puede repetir.'
  }
  return null
}

/** UUID que el CEDIS ya recibió. Simula la restricción UNIQUE de la base. */
export const UUID_YA_USADOS = ['9B1C77D2-3A4E-4F60-8D11-5E7A9C0B2F33']
