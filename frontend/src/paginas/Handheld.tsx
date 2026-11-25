/**
 * C2 · Simulador de handheld.
 *
 * No es una maqueta: las reglas corren de verdad en
 * `src/dispositivo/reglasLocales.ts`, igual que correrían en el equipo
 * Zebra sobre su copia local. Escanear la misma etiqueta dos veces da
 * duplicado, alterar las piezas da firma inválida, y pasarse de las 480
 * autorizadas da excedente — sin servidor de por medio.
 *
 * El interruptor de red apaga la sincronización, no la recepción: ese es
 * el punto de la arquitectura edge-first.
 */

import { useMemo, useState } from 'react'
import { ETIQUETAS_EN_CAMION, PAQUETE_DEMO } from '../datos/paquete'
import {
  ES_RECHAZO,
  estadoInicial,
  evaluarEscaneo,
  parsearQr,
  type EstadoLocal,
} from '../dispositivo/reglasLocales'
import type { ResultadoEscaneo } from '../tipos/api'

interface EnCola {
  uuid_evento: string
  folio: string
  estado_destino: string
  sincronizado: boolean
}

const TOTAL_BULTOS = 148

export default function Handheld() {
  const [enLinea, setEnLinea] = useState(true)
  const [estado, setEstado] = useState<EstadoLocal>(() => estadoInicial(PAQUETE_DEMO))
  const [ultimo, setUltimo] = useState<ResultadoEscaneo | null>(null)
  const [ultimoFolio, setUltimoFolio] = useState<string | null>(null)
  const [cola, setCola] = useState<EnCola[]>([])

  const recibidos = estado.recibidos.size
  const rechazados = cola.filter((e) => e.estado_destino === 'RECHAZADO').length
  const pendientes = cola.filter((e) => !e.sincronizado).length

  function escanear(cadena: string) {
    const { resultado, estado: nuevo } = evaluarEscaneo(cadena, PAQUETE_DEMO, estado)
    const folio = parsearQr(cadena)?.folio ?? '—'

    setEstado(nuevo)
    setUltimo(resultado)
    setUltimoFolio(folio)

    // Un duplicado no se vuelve a encolar: ya se mandó una vez.
    if (resultado.resultado !== 'duplicado') {
      setCola((c) => [
        {
          uuid_evento: resultado.uuid_evento,
          folio,
          estado_destino: resultado.estado_final,
          sincronizado: enLinea,
        },
        ...c,
      ])
    }
  }

  function alternarRed() {
    const vuelve = !enLinea
    setEnLinea(vuelve)
    // Al reconectar, WorkManager vacía la cola.
    if (vuelve) setCola((c) => c.map((e) => ({ ...e, sincronizado: true })))
  }

  const banner = useMemo(() => {
    if (!ultimo) return null
    if (ultimo.resultado === 'aplicado') return { tono: 'verde', titulo: 'RECIBIDO' } as const
    if (ultimo.resultado === 'duplicado') return { tono: 'azul', titulo: 'YA RECIBIDO' } as const
    return { tono: 'rojo', titulo: 'NO SE RECIBE' } as const
  }, [ultimo])

  const fondoBanner =
    banner?.tono === 'verde' ? 'bg-verde' : banner?.tono === 'azul' ? 'bg-azul' : 'bg-rojo'

  return (
    <div className="min-h-screen bg-piso p-6">
      <div className="mx-auto flex max-w-5xl flex-wrap items-start gap-8">
        {/* --- El equipo --- */}
        <div className="w-[390px] shrink-0 rounded-[26px] bg-tinta p-[9px] shadow-xl">
          <div className="flex h-[760px] flex-col overflow-hidden rounded-[18px] bg-piso">
            <div
              className={`flex items-center gap-2.5 px-4 py-3 text-xs text-white ${enLinea ? 'bg-tinta' : 'bg-ambar'}`}
            >
              <span className={`h-2 w-2 rounded-full ${enLinea ? 'bg-[#3FBF86]' : 'bg-white'}`} />
              <span className={`flex-grow ${enLinea ? '' : 'font-semibold'}`}>
                {enLinea ? 'En línea · Andén 5' : 'Sin red · operando local'}
              </span>
              <span className="font-mono">10:42</span>
            </div>

            <div className="border-b border-linea bg-white px-4 py-3">
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-[13px] font-bold">OC-88213</span>
                <span className="text-xs text-apagado">PRV-0147</span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-linea">
                <div
                  className="h-full bg-azul transition-all"
                  style={{ width: `${Math.min(100, (recibidos / TOTAL_BULTOS) * 100 + 28)}%` }}
                />
              </div>
              <div className="mt-1.5 flex justify-between text-[11.5px] text-apagado">
                <span className="num">
                  {41 + recibidos} de {TOTAL_BULTOS} bultos
                </span>
                <span className={rechazados ? 'font-semibold text-rojo' : ''}>
                  {rechazados} rechazado{rechazados === 1 ? '' : 's'}
                </span>
              </div>
            </div>

            {banner && ultimo ? (
              <div className={`px-4 py-7 text-center text-white ${fondoBanner}`}>
                {banner.tono === 'rojo' ? (
                  <svg
                    width="58"
                    height="58"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#fff"
                    strokeWidth="2.6"
                    className="mx-auto"
                    aria-hidden="true"
                  >
                    <circle cx="12" cy="12" r="9.2" />
                    <path d="M8.3 8.3l7.4 7.4M15.7 8.3l-7.4 7.4" />
                  </svg>
                ) : (
                  <svg
                    width="58"
                    height="58"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#fff"
                    strokeWidth="2.6"
                    className="mx-auto"
                    aria-hidden="true"
                  >
                    <circle cx="12" cy="12" r="9.2" />
                    <path d="M7.5 12.4l3.2 3.2L16.8 9" />
                  </svg>
                )}
                <div className="mt-2.5 text-[26px] font-bold tracking-tight">{banner.titulo}</div>
                <div className="mt-1 font-mono text-[15px] opacity-90">{ultimoFolio}</div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center bg-white px-4 py-10 text-center">
                <svg
                  width="48"
                  height="48"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#C9CDD4"
                  strokeWidth="1.8"
                  aria-hidden="true"
                >
                  <path d="M3 7V4h3M21 7V4h-3M3 17v3h3M21 17v3h-3M3 12h18" />
                </svg>
                <p className="mt-3 text-sm text-apagado">Escanee una etiqueta</p>
              </div>
            )}

            <div className="flex-grow space-y-3 overflow-y-auto p-4">
              {ultimo?.motivo && (
                <div
                  className={`rounded-[9px] border p-3.5 ${
                    ES_RECHAZO[ultimo.resultado]
                      ? 'border-rojo-bd bg-rojo-bg'
                      : 'border-azul-bd bg-azul-bg'
                  }`}
                >
                  <div
                    className={`mb-1.5 text-[11px] font-semibold uppercase tracking-wide ${
                      ES_RECHAZO[ultimo.resultado] ? 'text-rojo-osc' : 'text-azul-osc'
                    }`}
                  >
                    {ultimo.resultado.replaceAll('_', ' ')}
                  </div>
                  <p
                    className={`text-[12.5px] leading-relaxed ${
                      ES_RECHAZO[ultimo.resultado] ? 'text-rojo-osc' : 'text-azul-osc'
                    }`}
                  >
                    {ultimo.motivo}
                  </p>
                </div>
              )}

              {ultimo?.destino && (
                <div className="tarjeta p-3.5">
                  <div className="etiqueta-campo mb-2">
                    {ultimo.destino.tipo === 'cross_dock' ? 'Cross-dock' : 'Acomodo dirigido'}
                  </div>
                  {ultimo.destino.tipo === 'cross_dock' ? (
                    <p className="text-[12.5px] leading-relaxed">
                      El embarque de esta sucursal va al <strong>83%</strong>. Lleve el bulto
                      directo al <strong>andén de salida {ultimo.destino.anden}</strong>, no al
                      rack.
                    </p>
                  ) : (
                    <div className="font-mono text-[19px] font-bold tracking-tight">
                      {ultimo.destino.ubicacion}
                    </div>
                  )}
                </div>
              )}

              <div className="tarjeta p-3.5">
                <div className="mb-2.5 flex items-baseline justify-between">
                  <span className="etiqueta-campo">Cola de sincronización</span>
                  <span className="num text-[17px] font-bold">{pendientes}</span>
                </div>
                {cola.length === 0 ? (
                  <p className="text-[11.5px] text-apagado">Sin eventos todavía.</p>
                ) : (
                  <ul className="space-y-2">
                    {cola.slice(0, 5).map((e) => (
                      <li
                        key={e.uuid_evento}
                        className="flex items-center justify-between gap-2 text-[11.5px]"
                      >
                        <span className="truncate font-mono">
                          {e.folio} · {e.estado_destino}
                        </span>
                        <span
                          className={`shrink-0 font-semibold ${e.sincronizado ? 'text-verde' : 'text-ambar'}`}
                        >
                          {e.sincronizado ? 'sincronizado' : 'pendiente'}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
                <p className="mt-2.5 text-[11px] leading-relaxed text-apagado">
                  Cada evento lleva su propio identificador. Al reconectar no se duplica nada.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* --- Controles del simulador --- */}
        <div className="min-w-0 flex-1 space-y-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight">Simulador de handheld</h1>
            <p className="mt-1 text-sm leading-relaxed text-apagado">
              Las reglas corren en el navegador, igual que correrían en el equipo sin red. Toque una
              etiqueta para escanearla.
            </p>
          </div>

          <div className="tarjeta flex items-center justify-between gap-4 p-4">
            <div>
              <div className="text-sm font-semibold">Red del CEDIS</div>
              <p className="mt-0.5 text-[12px] text-apagado">
                Apagarla no detiene la recepción, solo la sincronización.
              </p>
            </div>
            <button
              type="button"
              onClick={alternarRed}
              aria-pressed={!enLinea}
              className={`min-h-toque shrink-0 rounded-[7px] px-4 py-2 text-[13px] font-semibold text-white ${
                enLinea ? 'bg-tinta' : 'bg-ambar'
              }`}
            >
              {enLinea ? 'Cortar la red' : 'Reconectar'}
            </button>
          </div>

          <div className="tarjeta overflow-hidden">
            <div className="border-b border-linea bg-white px-4 py-3 text-sm font-semibold">
              Etiquetas en el camión
            </div>
            <ul className="divide-y divide-linea">
              {ETIQUETAS_EN_CAMION.map((e) => (
                <li key={e.id}>
                  <button
                    type="button"
                    onClick={() => escanear(e.cadena)}
                    className="min-h-toque w-full px-4 py-3 text-left transition-colors hover:bg-azul-bg focus-visible:bg-azul-bg focus-visible:outline-none"
                  >
                    <div className="break-all font-mono text-[11px] text-tinta-2">{e.cadena}</div>
                    <div className="mt-1 text-[11.5px] text-apagado">{e.nota}</div>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div className="tarjeta p-4">
            <div className="etiqueta-campo mb-2">Qué demostrar al jurado</div>
            <ol className="list-decimal space-y-1.5 pl-5 text-[12.5px] leading-relaxed text-tinta-2">
              <li>Escanee la primera etiqueta: entra, y el sistema la manda a cross-dock.</li>
              <li>Escanéela otra vez: responde duplicado y no la cuenta dos veces.</li>
              <li>
                Escanee la del excedente: la OC autoriza 480 piezas, ya hay 456, y 24 más no caben.
              </li>
              <li>Escanee la alterada: la firma no corresponde y se rechaza.</li>
              <li>Corte la red y siga escaneando: la cola crece y la recepción no se detiene.</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  )
}
