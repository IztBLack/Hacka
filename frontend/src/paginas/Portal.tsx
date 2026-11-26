/**
 * C1 · Portal de proveedores — reserva de andén.
 *
 * Semifuncional: el motor de citas corre de verdad en
 * `src/simulacion/motorCitas.ts`. Toque una celda libre de la malla y
 * reserva; toque una ocupada y le dice con quién se traslapa y hasta qué
 * hora queda bloqueado ese andén contando la maniobra.
 *
 * En producción esto lo decide `POST /v1/citas` y la base de datos lo
 * garantiza con una restricción de exclusión.
 */

import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { horaApi, minutosDeHora } from '../api/adaptadores'
import { URL_API, esSinConexion, useReservarCita, useSlots } from '../api/cliente'
import { DISPONIBILIDAD_DEMO, OC_DEMO, PROVEEDOR_DEMO } from '../datos/ejemplo'
import type { SlotLibre } from '../tipos/api'
import {
  HORA_APERTURA,
  HORA_CIERRE,
  aHora,
  duracionMinutos,
  intentarReservar,
  minutosDe,
  primeraAlternativa,
  UUID_YA_USADOS,
  validarUuid,
  type Rechazo,
  type Reserva,
} from '../simulacion/motorCitas'
import type { AndenDisponibilidad } from '../tipos/vista'

const FILAS = (HORA_CIERRE - HORA_APERTURA) * 2

/** Slot del backend → reserva de la malla. Horas `time` sin zona → minutos. */
const aReserva = (s: SlotLibre): Reserva => ({
  ok: true,
  anden: s.anden,
  desde: minutosDeHora(s.hora_inicio),
  hasta: minutosDeHora(s.hora_fin),
})
const fila = (min: number) => (min - HORA_APERTURA * 60) / 30 + 1

function Paso({ n, texto, estado }: { n: number; texto: string; estado: 'hecho' | 'activo' | 'pendiente' }) {
  const circulo =
    estado === 'pendiente' ? 'bg-linea text-apagado-2' : estado === 'activo' ? 'bg-tinta text-white' : 'bg-azul text-white'
  const borde =
    estado === 'pendiente' ? 'border-transparent' : estado === 'activo' ? 'border-tinta' : 'border-azul'
  return (
    <div className={`flex items-center gap-2 border-b-2 py-[13px] ${borde}`}>
      <span className={`flex h-[19px] w-[19px] items-center justify-center rounded-full text-[11px] font-bold ${circulo}`}>
        {n}
      </span>
      <span className={`text-[13px] ${estado === 'pendiente' ? 'text-apagado-2' : 'font-semibold'}`}>{texto}</span>
    </div>
  )
}

export default function Portal() {
  const [uuid, setUuid] = useState(OC_DEMO.uuid_cfdi)
  const [nBultos, setNBultos] = useState(OC_DEMO.n_bultos)
  const [reserva, setReserva] = useState<Reserva | null>(null)
  const [rechazo, setRechazo] = useState<Rechazo | null>(null)
  const [confirmada, setConfirmada] = useState(false)
  /** Hora que pidió el proveedor: la alternativa se busca a partir de ahí. */
  const [intentoMin, setIntentoMin] = useState(HORA_APERTURA * 60)

  /** Folio real que devolvió POST /citas (null en modo demo). */
  const [folioCita, setFolioCita] = useState<string | null>(null)
  const [errorReserva, setErrorReserva] = useState<string | null>(null)

  const fecha = DISPONIBILIDAD_DEMO.fecha
  const consultaSlots = useSlots({ fecha, n_bultos: nBultos })
  const reservarCita = useReservarCita()

  // En vivo: la malla la decide POST /citas/slots. Sin API (o si el backend
  // falla): la simulación local de siempre. La demo de junta no se rompe.
  const slots = consultaSlots.isError ? undefined : consultaSlots.data
  const enVivo = slots !== undefined
  const cargandoSlots = consultaSlots.isPending && consultaSlots.fetchStatus === 'fetching'

  const disponibilidad = useMemo(
    () =>
      enVivo
        ? { ...DISPONIBILIDAD_DEMO, andenes: DISPONIBILIDAD_DEMO.andenes.map((a) => ({ ...a, ocupadas: [] })) }
        : DISPONIBILIDAD_DEMO,
    [enVivo],
  )

  /** `anden-minutoInicio` → slot libre real. */
  const libres = useMemo(() => {
    const m = new Map<string, SlotLibre>()
    for (const s of slots?.slots ?? []) m.set(`${s.anden}-${minutosDeHora(s.hora_inicio)}`, s)
    return m
  }, [slots])

  const { calculada, reservada: reservadaLocal } = useMemo(() => duracionMinutos(nBultos), [nBultos])
  // La duración manda el backend; la fórmula local es la misma y solo cubre la demo.
  const reservada = slots?.duracion_minutos ?? reservadaLocal
  const errorUuid = useMemo(
    () => validarUuid(uuid, enVivo ? [] : UUID_YA_USADOS),
    [uuid, enVivo],
  )

  const sugerida = useMemo(() => {
    if (!rechazo) return null
    if (enVivo) {
      const todos = slots?.slots ?? []
      const s =
        todos.find((x) => minutosDeHora(x.hora_inicio) >= intentoMin) ?? todos[0]
      return s ? aReserva(s) : null
    }
    return (
      primeraAlternativa(disponibilidad.andenes, intentoMin, reservada) ??
      primeraAlternativa(disponibilidad.andenes, HORA_APERTURA * 60, reservada)
    )
  }, [rechazo, intentoMin, disponibilidad.andenes, reservada, enVivo, slots])

  function elegir(anden: AndenDisponibilidad, inicioMin: number) {
    if (confirmada) return
    setIntentoMin(inicioMin)
    setErrorReserva(null)
    if (enVivo) {
      const s = libres.get(`${anden.numero}-${inicioMin}`)
      if (s) {
        setReserva(aReserva(s))
        setRechazo(null)
      } else {
        setReserva(null)
        setRechazo({
          ok: false,
          motivo: 'traslape',
          detalle: `El andén ${anden.numero} no tiene ${reservada} min libres a partir de las ${aHora(inicioMin)} según la agenda real del CEDIS (citas ya reservadas, 15 min de maniobra y ventana del andén flex).`,
        })
      }
      return
    }
    const r = intentarReservar(anden, inicioMin, reservada)
    if (r.ok) {
      setReserva(r)
      setRechazo(null)
    } else {
      setReserva(null)
      setRechazo(r)
    }
  }

  const horas = Array.from({ length: HORA_CIERRE - HORA_APERTURA }, (_, i) => HORA_APERTURA + i)
  const puedeConfirmar = reserva !== null && !errorUuid && !confirmada && !reservarCita.isPending

  function confirmar() {
    if (!reserva) return
    setErrorReserva(null)
    if (!enVivo) {
      setConfirmada(true)
      return
    }
    reservarCita.mutate(
      {
        proveedor: PROVEEDOR_DEMO.clave,
        orden_compra: OC_DEMO.folio,
        uuid_cfdi: uuid.trim().toUpperCase(),
        fecha,
        anden: reserva.anden,
        hora_inicio: horaApi(reserva.desde),
        n_bultos: nBultos,
      },
      {
        onSuccess: (cita) => {
          setFolioCita(cita.folio)
          setReserva({
            ok: true,
            anden: cita.anden,
            desde: minutosDeHora(cita.hora_inicio),
            hasta: minutosDeHora(cita.hora_fin),
          })
          setConfirmada(true)
        },
        onError: (e) => {
          // Se cayó la API justo al confirmar: la demo sigue, sin folio real.
          if (esSinConexion(e)) {
            setConfirmada(true)
            return
          }
          // 404/409/422: respuesta de negocio, se le dice al proveedor tal cual.
          setErrorReserva(e.message)
          setReserva(null)
          void consultaSlots.refetch()
        },
      },
    )
  }

  function reiniciar() {
    setReserva(null)
    setRechazo(null)
    setConfirmada(false)
    setFolioCita(null)
    setErrorReserva(null)
    reservarCita.reset()
  }

  return (
    <div className="flex min-h-screen flex-col bg-piso">
      <header className="flex flex-wrap items-center gap-5 bg-tinta px-7 py-3.5 text-white">
        <div className="flex min-w-0 flex-grow items-center gap-3">
          <div className="flex h-[30px] w-[30px] items-center justify-center rounded-md border-2 border-linea text-[13px] font-bold">
            CD
          </div>
          <div>
            <div className="text-sm font-semibold">CEDIS · Portal de Proveedores</div>
            <div className="mt-px text-[11px] text-linea-2">Agendamiento de entregas en andén</div>
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

      <nav aria-label="Avance del registro" className="flex flex-wrap gap-7 border-b border-linea bg-white px-7">
        <Paso n={1} texto="OC y CFDI" estado={errorUuid ? 'activo' : 'hecho'} />
        <Paso n={2} texto="Desglose por bulto" estado="hecho" />
        <Paso n={3} texto="Reservar andén" estado={confirmada ? 'hecho' : 'activo'} />
        <Paso n={4} texto="Descargar etiquetas" estado={confirmada ? 'activo' : 'pendiente'} />
      </nav>

      <div className="flex flex-grow flex-wrap items-start gap-6 px-7 pb-8 pt-6">
        <section className="flex min-w-0 flex-[1_1_360px] flex-col gap-4">
          <div className="tarjeta p-5">
            <h2 className="mb-4 text-sm font-bold">Orden de compra y comprobante fiscal</h2>
            <div className="flex flex-col gap-3.5">
              <div>
                <label htmlFor="oc" className="etiqueta-campo mb-1.5">Orden de compra</label>
                <input id="oc" type="text" value={OC_DEMO.folio} readOnly className="campo bg-piso font-mono font-medium" />
              </div>

              <div>
                <label htmlFor="uuid" className="etiqueta-campo mb-1.5">UUID del CFDI 4.0</label>
                <input
                  id="uuid"
                  type="text"
                  value={uuid}
                  onChange={(e) => setUuid(e.target.value)}
                  disabled={confirmada}
                  aria-invalid={!!errorUuid}
                  aria-describedby="uuid-estado"
                  className={`campo font-mono text-xs ${errorUuid ? 'border-rojo' : 'border-verde'}`}
                />
                <p id="uuid-estado" className={`mt-1.5 text-[11px] font-semibold ${errorUuid ? 'text-rojo' : 'text-verde'}`}>
                  {errorUuid ?? 'Vigente en el SAT · folio no duplicado en el CEDIS'}
                </p>
              </div>

              <div>
                <label htmlFor="bultos" className="etiqueta-campo mb-1.5">Bultos del desglose</label>
                <input
                  id="bultos"
                  type="number"
                  min={1}
                  max={600}
                  value={nBultos}
                  disabled={confirmada}
                  onChange={(e) => {
                    setNBultos(Math.max(1, Number(e.target.value) || 1))
                    setReserva(null)
                    setRechazo(null)
                  }}
                  className="campo num font-mono font-medium"
                />
                <p className="mt-1.5 text-[11px] text-apagado">
                  Cámbielo y verá recalcularse la duración y el bloque que ocupa en la malla.
                </p>
              </div>
            </div>
          </div>

          <div className="tarjeta p-5">
            <h2 className="mb-3 text-sm font-bold">Duración calculada por el sistema</h2>
            <div className="flex items-baseline gap-2">
              <span className="num text-3xl font-bold tracking-tight">
                {Math.floor(reservada / 60)} h {String(reservada % 60).padStart(2, '0')}
              </span>
              <span className="text-xs text-apagado">min de andén</span>
            </div>
            <p className="mt-2 font-mono text-[11px] leading-relaxed text-apagado">
              t = max(60, 12 + 0.9 × {nBultos}) = {calculada} min
              <br />→ se reserva el bloque de {reservada} min
            </p>
            <p className="mt-2.5 text-[11.5px] leading-relaxed text-apagado">
              Puede solicitar <strong className="text-tinta">más</strong> tiempo, nunca menos. Tolerancia de
              llegada: 15 min.
            </p>
          </div>

          {confirmada && reserva && (
            <div className="tarjeta border-verde-bd bg-verde-bg p-5">
              <h2 className="text-sm font-bold text-verde-osc">Cita confirmada</h2>
              <div className="mt-2 font-mono text-lg font-bold">{folioCita ?? 'CITA-2026-04412'}</div>
              <p className="mt-2 text-[12.5px] leading-relaxed text-verde-osc">
                Andén {reserva.anden} · {aHora(reserva.desde)} – {aHora(reserva.hasta)} del 26 de noviembre.
                Se liberaron las {nBultos} etiquetas QR firmadas.
              </p>
              <Link to="/etiquetas" className="boton-primario mt-3 inline-block no-underline">
                Descargar etiquetas
              </Link>
            </div>
          )}
        </section>

        <section className="tarjeta min-w-0 flex-[999_1_560px] p-5">
          <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="text-sm font-bold">Disponibilidad de andenes</h2>
            <span className="text-xs text-apagado">jueves 26 de noviembre de 2026</span>
          </div>
          <p className="mb-3.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11.5px] text-apagado">
            <span
              title={enVivo ? `POST ${URL_API}/citas/slots` : `${URL_API} no respondió: simulación local`}
              className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold text-white ${
                cargandoSlots ? 'bg-apagado-2' : enVivo ? 'bg-verde' : 'bg-ambar'
              }`}
            >
              {cargandoSlots ? 'Conectando…' : enVivo ? 'En vivo · BD' : 'Demo sin conexión'}
            </span>
            {enVivo && slots ? (
              <span>
                Capacidad del día: {slots.capacidad_dia} citas · {slots.total_slots} horarios libres de{' '}
                {slots.duracion_minutos} min.
              </span>
            ) : (
              <span>
                Capacidad del día: {disponibilidad.capacidad_citas} citas · {disponibilidad.reservadas} reservadas ·{' '}
                {disponibilidad.capacidad_citas - disponibilidad.reservadas} libres.
              </span>
            )}
            <strong className="text-tinta">Toque una celda para reservar.</strong>
          </p>

          <div className="overflow-x-auto">
            <div className="min-w-[520px]">
              <div className="mb-1.5 grid gap-1.5" style={{ gridTemplateColumns: `54px repeat(${disponibilidad.andenes.length}, minmax(0, 1fr))` }}>
                <div />
                {disponibilidad.andenes.map((a) => (
                  <div key={a.numero} className={`text-center text-[11px] font-semibold ${a.tipo === 'flex' ? 'text-azul' : ''}`}>
                    Andén {a.numero}
                    {a.tipo === 'flex' && ' flex'}
                  </div>
                ))}
              </div>

              <div
                className="grid gap-x-1.5 gap-y-0.5"
                style={{
                  gridTemplateColumns: `54px repeat(${disponibilidad.andenes.length}, minmax(0, 1fr))`,
                  gridTemplateRows: `repeat(${FILAS}, 20px)`,
                }}
              >
                {horas.map((hora, i) => (
                  <div key={hora} className="pr-1.5 text-right font-mono text-[10px] text-apagado-2" style={{ gridColumn: 1, gridRow: `${i * 2 + 1} / ${i * 2 + 3}` }}>
                    {hora}:00
                  </div>
                ))}

                {/* Celdas tocables: una por bloque de 30 min y andén */}
                {disponibilidad.andenes.flatMap((anden, idx) =>
                  Array.from({ length: FILAS }, (_, f) => {
                    const inicio = HORA_APERTURA * 60 + f * 30
                    const ocupante = anden.ocupadas.find(
                      (o) => minutosDe(o.inicio) < inicio + 30 && inicio < minutosDe(o.fin),
                    )
                    // En vivo no se sabe quién ocupa: solo si ahí arranca un slot libre.
                    const sinSlot = enVivo && !libres.has(`${anden.numero}-${inicio}`)
                    return (
                      <button
                        key={`${anden.numero}-${f}`}
                        type="button"
                        onClick={() => elegir(anden, inicio)}
                        aria-label={
                          ocupante
                            ? `Andén ${anden.numero} a las ${aHora(inicio)}: ocupado por ${ocupante.proveedor}`
                            : sinSlot
                              ? `Andén ${anden.numero} a las ${aHora(inicio)}: sin espacio para esta descarga`
                              : `Reservar andén ${anden.numero} a las ${aHora(inicio)}`
                        }
                        className={`rounded-[3px] border transition-colors hover:border-azul hover:bg-azul-bg ${
                          sinSlot ? 'border-transparent bg-linea/50' : 'border-dashed border-linea-2/70'
                        }`}
                        style={{ gridColumn: idx + 2, gridRow: `${f + 1} / ${f + 2}` }}
                      />
                    )
                  }),
                )}

                {/* Citas ya tomadas, encima de las celdas */}
                {disponibilidad.andenes.flatMap((anden, idx) =>
                  anden.ocupadas.map((o) => (
                    <div
                      key={`${anden.numero}-${o.inicio}`}
                      className="pointer-events-none overflow-hidden rounded bg-linea-2/80 px-[7px] py-[5px] text-[10px] leading-tight text-tinta-2"
                      style={{ gridColumn: idx + 2, gridRow: `${fila(minutosDe(o.inicio))} / ${fila(minutosDe(o.fin))}` }}
                    >
                      {o.proveedor}
                      <br />
                      <span className="font-mono text-[9px]">{o.folio_oc}</span>
                    </div>
                  )),
                )}

                {/* Cierre del flex */}
                {disponibilidad.andenes.map((a, idx) =>
                  a.tipo === 'flex' && a.recibo_hasta ? (
                    <div
                      key={`cierre-${a.numero}`}
                      className="pointer-events-none flex items-center justify-center rounded border border-linea-2 bg-linea/60 p-1.5 text-center text-[10px] leading-tight text-apagado"
                      style={{ gridColumn: idx + 2, gridRow: `${fila(Number(a.recibo_hasta.slice(0, 2)) * 60)} / ${FILAS + 1}` }}
                    >
                      Cerrado a recibo
                      <br />
                      {a.recibo_hasta} – {HORA_CIERRE}:00
                    </div>
                  ) : null,
                )}

                {/* La reserva en curso */}
                {reserva && (
                  <div
                    className={`pointer-events-none overflow-hidden rounded px-2 py-1.5 text-[10.5px] leading-tight text-white ${confirmada ? 'bg-verde' : 'bg-azul'}`}
                    style={{
                      gridColumn: disponibilidad.andenes.findIndex((a) => a.numero === reserva.anden) + 2,
                      gridRow: `${fila(reserva.desde)} / ${fila(reserva.hasta)}`,
                    }}
                  >
                    <strong>{confirmada ? 'Su cita' : 'Seleccionado'}</strong>
                    <br />
                    {aHora(reserva.desde)} – {aHora(reserva.hasta)}
                  </div>
                )}
              </div>
            </div>
          </div>

          {rechazo && (
            <div role="alert" className="mt-4 flex gap-2.5 rounded-md border border-l-[3px] border-rojo-bd border-l-rojo bg-rojo-bg px-3 py-3">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#C02626" strokeWidth="2.2" className="mt-px shrink-0" aria-hidden="true">
                <circle cx="12" cy="12" r="9" />
                <path d="M8.5 8.5l7 7M15.5 8.5l-7 7" />
              </svg>
              <div>
                <p className="text-xs font-semibold text-rojo-osc">No se puede reservar ahí</p>
                <p className="mt-1 text-xs leading-relaxed text-rojo-osc">{rechazo.detalle}</p>
                {sugerida && (
                  <button
                    type="button"
                    onClick={() => {
                      setReserva(sugerida)
                      setRechazo(null)
                    }}
                    className="mt-2 rounded-md bg-rojo px-3 py-2 text-[11px] font-semibold text-white"
                  >
                    Usar andén {sugerida.anden} a las {aHora(sugerida.desde)}
                  </button>
                )}
              </div>
            </div>
          )}

          {errorReserva && (
            <div role="alert" className="mt-4 rounded-md border border-l-[3px] border-rojo-bd border-l-rojo bg-rojo-bg px-3 py-3 text-xs leading-relaxed text-rojo-osc">
              <strong>El CEDIS rechazó la cita:</strong> {errorReserva}. La malla ya se actualizó; elija otro horario.
            </div>
          )}

          {reserva && !confirmada && (
            <div role="status" className="mt-4 rounded-md border border-azul-bd bg-azul-bg px-3 py-3 text-xs leading-relaxed text-azul-osc">
              Andén {reserva.anden}, {aHora(reserva.desde)} – {aHora(reserva.hasta)}. Cabe sin traslaparse
              con ninguna otra cita, contando los 15 min de maniobra.
            </div>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-linea pt-4">
            <button
              type="button"
              disabled={!puedeConfirmar}
              onClick={confirmar}
              className="boton-primario"
            >
              {confirmada
                ? 'Cita confirmada'
                : reservarCita.isPending
                  ? 'Reservando…'
                  : 'Confirmar cita y generar pase QR'}
            </button>
            <button
              type="button"
              onClick={reiniciar}
              className="boton-secundario"
            >
              Empezar de nuevo
            </button>
            <span className="text-[11.5px] text-apagado">
              {errorUuid
                ? 'Corrija el UUID para poder confirmar.'
                : reserva
                  ? `Al confirmar se liberan las ${nBultos} etiquetas QR firmadas`
                  : 'Elija un horario en la malla.'}
            </span>
          </div>
        </section>
      </div>
    </div>
  )
}
