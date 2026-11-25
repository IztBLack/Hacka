/**
 * C1 · Portal de proveedores — reserva de andén.
 *
 * Traduce el mockup `mockups/mockups-cedis.html` a componentes reales.
 * Los datos vienen de `src/datos/ejemplo.ts` mientras B no entregue
 * `GET /v1/andenes/disponibilidad` y `POST /v1/citas`.
 */

import { useMemo, useState } from 'react'
import { CITA_DEMO, DISPONIBILIDAD_DEMO, OC_DEMO, PROVEEDOR_DEMO } from '../datos/ejemplo'
import type { AndenDisponibilidad, FranjaOcupada } from '../tipos/api'

const HORA_APERTURA = 8
const HORA_CIERRE = 18
/** Una fila por bloque de 30 min, que es la malla del motor de citas. */
const FILAS = (HORA_CIERRE - HORA_APERTURA) * 2

/** "2026-11-26T10:30:00Z" -> 630 (minutos desde medianoche) */
function minutosDe(iso: string): number {
  const [hh, mm] = iso.slice(11, 16).split(':').map(Number)
  return hh * 60 + mm
}

/** Convierte una franja en su rango de filas de la malla, base 1. */
function filasDe(franja: { inicio: string; fin: string }) {
  const inicio = (minutosDe(franja.inicio) - HORA_APERTURA * 60) / 30
  const fin = (minutosDe(franja.fin) - HORA_APERTURA * 60) / 30
  return { desde: Math.max(1, inicio + 1), hasta: Math.min(FILAS + 1, fin + 1) }
}

function hhmm(iso: string) {
  return iso.slice(11, 16)
}

function Paso({
  n,
  texto,
  estado,
}: {
  n: number
  texto: string
  estado: 'hecho' | 'activo' | 'pendiente'
}) {
  const circulo =
    estado === 'pendiente'
      ? 'bg-linea text-apagado-2'
      : estado === 'activo'
        ? 'bg-tinta text-white'
        : 'bg-azul text-white'
  const borde =
    estado === 'pendiente'
      ? 'border-transparent'
      : estado === 'activo'
        ? 'border-tinta'
        : 'border-azul'

  return (
    <div className={`flex items-center gap-2 border-b-2 py-[13px] ${borde}`}>
      <span
        className={`flex h-[19px] w-[19px] items-center justify-center rounded-full text-[11px] font-bold ${circulo}`}
      >
        {n}
      </span>
      <span
        className={`text-[13px] ${estado === 'pendiente' ? 'text-apagado-2' : 'font-semibold'}`}
      >
        {texto}
      </span>
    </div>
  )
}

function BloqueOcupado({ franja, columna }: { franja: FranjaOcupada; columna: number }) {
  const { desde, hasta } = filasDe(franja)
  return (
    <div
      className="overflow-hidden rounded bg-linea-2/70 px-[7px] py-[5px] text-[10px] leading-tight text-tinta-2"
      style={{ gridColumn: columna, gridRow: `${desde} / ${hasta}` }}
    >
      {franja.proveedor}
      <br />
      <span className="font-mono text-[9px]">{franja.folio_oc}</span>
    </div>
  )
}

function MallaAndenes({ andenes }: { andenes: AndenDisponibilidad[] }) {
  const cita = filasDe(CITA_DEMO)
  const horas = useMemo(
    () => Array.from({ length: HORA_CIERRE - HORA_APERTURA }, (_, i) => HORA_APERTURA + i),
    [],
  )
  const columnaCita = andenes.findIndex((a) => a.numero === CITA_DEMO.anden_asignado) + 2

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[520px]">
        <div
          className="mb-1.5 grid gap-1.5"
          style={{ gridTemplateColumns: `54px repeat(${andenes.length}, minmax(0, 1fr))` }}
        >
          <div />
          {andenes.map((a) => (
            <div
              key={a.numero}
              className={`text-center text-[11px] font-semibold ${a.tipo === 'flex' ? 'text-azul' : ''}`}
            >
              Andén {a.numero}
              {a.tipo === 'flex' && ' flex'}
            </div>
          ))}
        </div>

        <div
          className="grid gap-x-1.5 gap-y-0.5"
          style={{
            gridTemplateColumns: `54px repeat(${andenes.length}, minmax(0, 1fr))`,
            gridTemplateRows: `repeat(${FILAS}, 20px)`,
          }}
        >
          {horas.map((hora, i) => (
            <div
              key={hora}
              className="pr-1.5 text-right font-mono text-[10px] text-apagado-2"
              style={{ gridColumn: 1, gridRow: `${i * 2 + 1} / ${i * 2 + 3}` }}
            >
              {hora}:00
            </div>
          ))}

          {andenes.flatMap((anden, idx) =>
            anden.ocupadas.map((f) => (
              <BloqueOcupado key={`${anden.numero}-${f.inicio}`} franja={f} columna={idx + 2} />
            )),
          )}

          <div
            className="overflow-hidden rounded bg-azul px-2 py-1.5 text-[10.5px] leading-tight text-white"
            style={{ gridColumn: columnaCita, gridRow: `${cita.desde} / ${cita.hasta}` }}
          >
            <strong>Su cita</strong>
            <br />
            {hhmm(CITA_DEMO.inicio)} – {hhmm(CITA_DEMO.fin)}
            <br />
            <span className="font-mono text-[9px] opacity-85">{OC_DEMO.folio}</span>
          </div>

          {andenes.map((a, idx) =>
            a.tipo === 'flex' && a.recibo_hasta ? (
              <div
                key={`cierre-${a.numero}`}
                className="flex items-center justify-center rounded border border-linea-2 bg-linea/40 p-1.5 text-center text-[10px] leading-tight text-apagado"
                style={{
                  gridColumn: idx + 2,
                  gridRow: `${(Number(a.recibo_hasta.slice(0, 2)) - HORA_APERTURA) * 2 + 1} / ${FILAS + 1}`,
                }}
              >
                Cerrado a recibo
                <br />
                {a.recibo_hasta} – {HORA_CIERRE}:00
                <br />
                uso: embarque
              </div>
            ) : null,
          )}
        </div>
      </div>
    </div>
  )
}

export default function Portal() {
  const [uuid, setUuid] = useState(OC_DEMO.uuid_cfdi)
  const disponibilidad = DISPONIBILIDAD_DEMO

  return (
    <div className="flex min-h-screen flex-col bg-piso">
      <header className="flex flex-wrap items-center gap-5 bg-tinta px-7 py-3.5 text-white">
        <div className="flex min-w-0 flex-grow items-center gap-3">
          <div className="flex h-[30px] w-[30px] items-center justify-center rounded-md border-2 border-linea text-[13px] font-bold">
            CD
          </div>
          <div>
            <div className="text-sm font-semibold">CEDIS · Portal de Proveedores</div>
            <div className="mt-px text-[11px] text-linea-2">
              Agendamiento de entregas en andén
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-xs font-medium">{PROVEEDOR_DEMO.razon_social}</div>
            <div className="mt-px font-mono text-[10px] text-linea-2">{PROVEEDOR_DEMO.clave}</div>
          </div>
          <div className="whitespace-nowrap rounded-full bg-verde px-[11px] py-[5px] text-[11px] font-semibold">
            Score {PROVEEDOR_DEMO.score} · Preferente
          </div>
        </div>
      </header>

      <nav
        aria-label="Avance del registro"
        className="flex flex-wrap gap-7 border-b border-linea bg-white px-7"
      >
        <Paso n={1} texto="OC y CFDI" estado="hecho" />
        <Paso n={2} texto="Desglose por bulto" estado="hecho" />
        <Paso n={3} texto="Reservar andén" estado="activo" />
        <Paso n={4} texto="Descargar etiquetas" estado="pendiente" />
      </nav>

      <div className="flex flex-grow flex-wrap items-start gap-6 px-7 pb-8 pt-6">
        <section className="flex min-w-0 flex-[1_1_360px] flex-col gap-4">
          <div className="tarjeta p-5">
            <h2 className="mb-4 text-sm font-bold">Orden de compra y comprobante fiscal</h2>

            <div className="flex flex-col gap-3.5">
              <div>
                <label htmlFor="oc" className="etiqueta-campo mb-1.5">
                  Orden de compra
                </label>
                <input
                  id="oc"
                  type="text"
                  value={OC_DEMO.folio}
                  readOnly
                  className="campo bg-piso font-mono font-medium"
                />
                <p className="mt-1.5 text-[11px] text-apagado">
                  {OC_DEMO.n_bultos} bultos esperados · {OC_DEMO.n_sku} SKU · destino{' '}
                  {OC_DEMO.n_sucursales} sucursales
                </p>
              </div>

              <div>
                <label htmlFor="uuid" className="etiqueta-campo mb-1.5">
                  UUID del CFDI 4.0
                </label>
                <input
                  id="uuid"
                  type="text"
                  value={uuid}
                  onChange={(e) => setUuid(e.target.value)}
                  className="campo border-verde font-mono text-xs"
                />
                <p className="mt-1.5 text-[11px] font-semibold text-verde">
                  Vigente en el SAT · folio no duplicado en el CEDIS
                </p>
              </div>
            </div>
          </div>

          <div className="tarjeta p-5">
            <h2 className="mb-3 text-sm font-bold">Duración calculada por el sistema</h2>
            <div className="flex items-baseline gap-2">
              <span className="num text-3xl font-bold tracking-tight">
                {Math.floor(CITA_DEMO.duracion_min / 60)} h {CITA_DEMO.duracion_min % 60}
              </span>
              <span className="text-xs text-apagado">min de andén</span>
            </div>
            <p className="mt-2 font-mono text-[11px] leading-relaxed text-apagado">
              t = max(60, 12 + 0.9 × {OC_DEMO.n_bultos}) = {CITA_DEMO.duracion_calculada_min} min
              <br />→ se reserva el bloque de {CITA_DEMO.duracion_min} min
            </p>
            <p className="mt-2.5 text-[11.5px] leading-relaxed text-apagado">
              Puede solicitar <strong className="text-tinta">más</strong> tiempo, nunca menos.
              Tolerancia de llegada: 15 min.
            </p>
          </div>
        </section>

        <section className="tarjeta min-w-0 flex-[999_1_560px] p-5">
          <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="text-sm font-bold">Disponibilidad de andenes</h2>
            <span className="text-xs text-apagado">jueves 26 de noviembre de 2026</span>
          </div>
          <p className="mb-3.5 text-[11.5px] text-apagado">
            Capacidad del día: {disponibilidad.capacidad_citas} citas · {disponibilidad.reservadas}{' '}
            reservadas · {disponibilidad.capacidad_citas - disponibilidad.reservadas} libres
          </p>

          <MallaAndenes andenes={disponibilidad.andenes} />

          {CITA_DEMO.reubicada && (
            <div className="mt-4 flex gap-2.5 rounded-md border border-l-[3px] border-ambar-bd border-l-ambar bg-ambar-bg px-3 py-3">
              <svg
                width="17"
                height="17"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#B45309"
                strokeWidth="2.2"
                className="mt-px shrink-0"
                aria-hidden="true"
              >
                <path d="M12 4v10" />
                <circle cx="12" cy="19" r="1.4" fill="#B45309" stroke="none" />
              </svg>
              <p className="text-xs leading-relaxed text-ambar-osc">
                El horario que solicitó originalmente (
                <strong>
                  Andén {CITA_DEMO.anden_solicitado}, {hhmm(CITA_DEMO.inicio)}
                </strong>
                ) se traslapa con otra cita. El sistema reubicó su entrega en el{' '}
                <strong>Andén {CITA_DEMO.anden_asignado} flex</strong>, disponible a recibo de 8:00
                a 13:00.
              </p>
            </div>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-linea pt-4">
            <button type="button" className="boton-primario">
              Confirmar cita y generar pase QR
            </button>
            <button type="button" className="boton-secundario">
              Ver otro día
            </button>
            <span className="text-[11.5px] text-apagado">
              Al confirmar se liberan las {OC_DEMO.n_bultos} etiquetas QR firmadas
            </span>
          </div>
        </section>
      </div>
    </div>
  )
}
