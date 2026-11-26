/**
 * C3 · Tablero de consolidación por sucursal.
 *
 * Semifuncional: los botones cambian el estado de verdad y los indicadores
 * de arriba se recalculan. Liberar por excepción abre un panel que EXIGE
 * quién autoriza — no es el mismo acto que programar un embarque que cumple
 * la regla, y la interfaz no lo disfraza de rutina.
 *
 * Lo ve el jefe de embarques de pie y de lejos: números grandes y el color
 * hace el trabajo antes que el texto.
 */

import { useMemo, useState } from 'react'
import { tableroAVista } from '../api/adaptadores'
import { URL_API, useTablero } from '../api/cliente'
import { CONSOLIDACION_DEMO, NOMBRE_UNIDAD } from '../datos/ejemplo'
import type { DecisionConsolidacion, FilaConsolidacion } from '../tipos/vista'

/** Nombres de sucursal: el tablero real solo manda la clave. */
const NOMBRES_SUCURSAL: Record<string, string> = Object.fromEntries(
  CONSOLIDACION_DEMO.filas.map((f) => [f.sucursal, f.nombre]),
)

function OrigenDatos({ enVivo, cargando }: { enVivo: boolean; cargando: boolean }) {
  const [texto, clase, titulo] = cargando
    ? ['Conectando…', 'bg-tinta-2 text-linea-2', `Consultando ${URL_API}`]
    : enVivo
      ? ['En vivo · BD', 'bg-verde text-white', `GET ${URL_API}/consolidacion/tablero`]
      : ['Demo sin conexión', 'bg-ambar text-white', `${URL_API} no respondió: datos de ejemplo`]
  return (
    <span title={titulo} className={`rounded-full px-2.5 py-1 text-[10.5px] font-semibold ${clase}`}>
      {texto}
    </span>
  )
}

type Estado = 'pendiente' | 'programada'

interface Despachada {
  estado: Estado
  anden?: number
  folio?: string
  acta?: string
  autorizo?: string
}

const ESTILO: Record<
  DecisionConsolidacion,
  { barra: string; fondo: string; texto: string; etiqueta: string }
> = {
  liberar: { barra: 'bg-verde', fondo: 'bg-verde-bg', texto: 'text-verde-osc', etiqueta: 'Liberar' },
  excepcion: { barra: 'bg-ambar', fondo: 'bg-ambar-bg', texto: 'text-ambar-osc', etiqueta: 'Excepción' },
  acumulando: { barra: 'bg-azul-bd', fondo: 'bg-white', texto: 'text-apagado', etiqueta: 'Acumulando' },
}

function Indicador({ titulo, valor, acento }: { titulo: string; valor: string; acento?: string }) {
  return (
    <div>
      <div className="text-[10.5px] text-linea-2">{titulo}</div>
      <div className={`num text-xl font-bold ${acento ?? ''}`}>{valor}</div>
    </div>
  )
}

export default function Tablero() {
  // Con API: datos de la BD. Sin API (error de red o de servidor): la demo.
  // La junta nunca ve una pantalla rota.
  const consulta = useTablero()
  const enVivo = consulta.data !== undefined
  const cargando = consulta.isPending && consulta.fetchStatus === 'fetching'
  const d = useMemo(
    () => (consulta.data ? tableroAVista(consulta.data, NOMBRES_SUCURSAL) : CONSOLIDACION_DEMO),
    [consulta.data],
  )
  const [despacho, setDespacho] = useState<Record<string, Despachada>>({})
  const [pidiendoActa, setPidiendoActa] = useState<string | null>(null)
  const [autorizo, setAutorizo] = useState('')
  const [andenLibre, setAndenLibre] = useState(3)
  const [consecutivo, setConsecutivo] = useState(1185)
  const [consecutivoActa, setConsecutivoActa] = useState(393)

  const pendientes = useMemo(
    () => d.filas.filter((f) => despacho[f.sucursal]?.estado !== 'programada'),
    [d.filas, despacho],
  )

  const listas = pendientes.filter((f) => f.decision === 'liberar').length
  const enAlerta = pendientes.filter((f) => f.decision === 'excepcion').length
  const programados = Object.values(despacho).filter((x) => x.estado === 'programada')
  const conExcepcion = programados.filter((x) => x.acta).length
  const pctExcepcion = programados.length ? Math.round((conExcepcion / programados.length) * 100) : 0

  // El rack guarda tarimas de las 32 sucursales, no solo de las 9 que caben
  // en pantalla: se parte del total real y se descuenta lo que ya salió.
  const tarimasDespachadas = d.filas.reduce(
    (s, f) => s + (despacho[f.sucursal]?.estado === 'programada' ? f.tarimas : 0),
    0,
  )
  const tarimasEnRack = d.tarimas_en_rack - tarimasDespachadas

  function programar(f: FilaConsolidacion) {
    const folio = `REL-2026-0${consecutivo}`
    setConsecutivo((c) => c + 1)
    setDespacho((p) => ({ ...p, [f.sucursal]: { estado: 'programada', anden: andenLibre, folio } }))
    setAndenLibre((a) => (a >= 3 ? 1 : a + 1))
  }

  function liberarConActa(f: FilaConsolidacion) {
    if (!autorizo.trim()) return
    const folio = `REL-2026-0${consecutivo}`
    const acta = `ACT-2026-0${consecutivoActa}`
    setConsecutivo((c) => c + 1)
    setConsecutivoActa((c) => c + 1)
    setDespacho((p) => ({
      ...p,
      [f.sucursal]: { estado: 'programada', anden: andenLibre, folio, acta, autorizo: autorizo.trim() },
    }))
    setAndenLibre((a) => (a >= 3 ? 1 : a + 1))
    setPidiendoActa(null)
    setAutorizo('')
  }

  return (
    <div className="flex min-h-screen flex-col bg-piso">
      <header className="flex flex-wrap items-center gap-5 bg-tinta px-7 py-4 text-white">
        <div className="min-w-0 flex-grow">
          <div className="flex items-center gap-2.5">
            <span className="text-[15px] font-semibold">Consolidación por sucursal</span>
            <OrigenDatos enVivo={enVivo} cargando={cargando} />
          </div>
          <div className="mt-0.5 text-[11.5px] text-linea-2">
            {enVivo
              ? new Date(consulta.dataUpdatedAt).toLocaleString('es-MX', {
                  dateStyle: 'long',
                  timeStyle: 'short',
                })
              : '26 de noviembre de 2026 · 15:20'}{' '}
            · 3 andenes de embarque
          </div>
        </div>
        <div className="flex flex-wrap gap-6">
          <Indicador titulo="Listas para salir" valor={String(listas)} />
          <Indicador titulo="Alerta 36 h" valor={String(enAlerta)} acento={enAlerta ? 'text-[#F0A35C]' : ''} />
          <Indicador titulo="Programadas hoy" valor={String(programados.length)} />
          <Indicador titulo="Tarimas en rack" valor={String(tarimasEnRack)} />
          <Indicador
            titulo="Con excepción"
            valor={`${pctExcepcion}%`}
            acento={pctExcepcion > 8 ? 'text-[#F0A35C]' : ''}
          />
        </div>
      </header>

      {/* Con uno o dos embarques el porcentaje no significa nada: 1 de 1 es
          100% y no es una señal. El aviso espera a tener muestra. */}
      {programados.length >= 3 && pctExcepcion > 8 && (
        <div className="border-b border-ambar-bd bg-ambar-bg px-7 py-2.5 text-[12px] text-ambar-osc">
          <strong>La meta es ≤ 8% de embarques con excepción de antigüedad</strong> y hoy va en{' '}
          {pctExcepcion}%. Si se sostiene, el problema no es el tablero: es que falta capacidad de
          consolidación o sobra espera.
        </div>
      )}

      <div className="flex-grow px-7 pb-8 pt-5">
        <div className="mb-4 flex flex-wrap items-center gap-4 text-[11.5px] text-apagado">
          <span className="font-semibold text-tinta">Regla de liberación:</span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-verde" />≥ 90% — liberar
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-ambar" />&lt; 90% pero ≥ 36 h — excepción
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-azul-bd" />acumulando
          </span>
        </div>

        <div className="tarjeta overflow-x-auto">
          <table className="w-full min-w-[920px] border-collapse text-xs">
            <thead>
              <tr className="border-b border-linea bg-piso/60">
                {['Sucursal', 'Tarimas', 'Peso kg', 'Ocupación', 'Unidad', 'Antigüedad', 'Acción'].map(
                  (h, i) => (
                    <th
                      key={h}
                      className={`px-3 py-3 text-[10.5px] font-semibold uppercase tracking-wide text-apagado ${
                        i === 0 || i === 3 || i === 4 ? 'text-left' : 'text-right'
                      }`}
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {cargando && (
                <tr>
                  <td colSpan={7} className="px-3.5 py-6 text-center text-[12px] text-apagado">
                    Consultando el tablero del CEDIS…
                  </td>
                </tr>
              )}
              {enVivo && d.filas.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3.5 py-6 text-center text-[12px] text-apagado">
                    No hay tarimas pendientes de embarque en la base.
                  </td>
                </tr>
              )}
              {!cargando && d.filas.map((f) => {
                const e = ESTILO[f.decision]
                const pct = Math.round(f.ocupacion * 100)
                const yaSalio = despacho[f.sucursal]
                const pidiendo = pidiendoActa === f.sucursal

                return (
                  <tr
                    key={f.sucursal}
                    className={`border-b border-linea/60 ${yaSalio ? 'bg-piso/70 opacity-70' : e.fondo}`}
                  >
                    <td className="px-3.5 py-3">
                      <div className="font-mono font-semibold">{f.sucursal}</div>
                      <div className="text-[10.5px] text-apagado-2">{f.nombre}</div>
                    </td>
                    <td className="num px-2.5 py-3 text-right font-mono font-semibold">
                      {f.tarimas} / {f.posiciones_unidad}
                    </td>
                    <td className="num px-2.5 py-3 text-right font-mono text-apagado">
                      {f.peso_kg === null ? '—' : f.peso_kg.toLocaleString('es-MX')}
                    </td>
                    <td className="w-[210px] px-3.5 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="h-2 flex-grow overflow-hidden rounded-full bg-linea">
                          <div className={`h-full ${yaSalio ? 'bg-apagado-2' : e.barra}`} style={{ width: `${pct}%` }} />
                        </div>
                        <span className={`num w-9 text-right text-[11px] font-bold ${e.texto}`}>{pct}%</span>
                      </div>
                      <div className={`mt-1 text-[10px] font-semibold ${e.texto}`}>
                        {yaSalio ? 'Programada' : e.etiqueta}
                      </div>
                    </td>
                    <td className="px-2.5 py-3 font-semibold">
                      {f.unidad_sugerida ? NOMBRE_UNIDAD[f.unidad_sugerida] : '—'}
                    </td>
                    <td
                      className={`num px-2.5 py-3 text-right font-mono ${
                        f.decision === 'excepcion' && !yaSalio ? 'font-bold text-ambar' : 'text-apagado'
                      }`}
                    >
                      {f.antiguedad_horas} h
                    </td>
                    <td className="px-3.5 py-3 text-right">
                      {yaSalio ? (
                        <div className="text-right">
                          <div className="font-mono text-[10.5px] font-semibold">{yaSalio.folio}</div>
                          <div className="text-[10px] text-apagado">
                            Salida {yaSalio.anden}
                            {yaSalio.acta && ` · ${yaSalio.acta}`}
                          </div>
                          {yaSalio.autorizo && (
                            <div className="text-[10px] text-ambar">Autorizó {yaSalio.autorizo}</div>
                          )}
                        </div>
                      ) : pidiendo ? (
                        <div className="flex flex-col items-end gap-1.5">
                          <label htmlFor={`aut-${f.sucursal}`} className="sr-only">
                            Quién autoriza la excepción
                          </label>
                          <input
                            id={`aut-${f.sucursal}`}
                            value={autorizo}
                            onChange={(ev) => setAutorizo(ev.target.value)}
                            placeholder="Quién autoriza"
                            className="w-36 rounded border border-ambar-bd px-2 py-1.5 text-[11px]"
                          />
                          <div className="flex gap-1.5">
                            <button
                              type="button"
                              disabled={!autorizo.trim()}
                              onClick={() => liberarConActa(f)}
                              className="rounded bg-ambar px-2.5 py-1.5 text-[10.5px] font-semibold text-white disabled:opacity-40"
                            >
                              Firmar y liberar
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setPidiendoActa(null)
                                setAutorizo('')
                              }}
                              className="rounded border border-linea-2 px-2.5 py-1.5 text-[10.5px]"
                            >
                              Cancelar
                            </button>
                          </div>
                        </div>
                      ) : f.decision === 'liberar' ? (
                        <button
                          type="button"
                          onClick={() => programar(f)}
                          className="min-h-[36px] rounded-md bg-azul px-3 py-2 text-[11px] font-semibold text-white hover:bg-azul-osc"
                        >
                          Programar
                        </button>
                      ) : f.decision === 'excepcion' ? (
                        <button
                          type="button"
                          onClick={() => {
                            setPidiendoActa(f.sucursal)
                            setAutorizo('')
                          }}
                          className="min-h-[36px] rounded-md bg-ambar px-3 py-2 text-[11px] font-semibold text-white hover:brightness-110"
                        >
                          Liberar c/acta
                        </button>
                      ) : (
                        <span className="text-[11px] text-apagado-2">—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-5 flex flex-wrap items-stretch gap-4">
          <div className="tarjeta min-w-0 flex-[1_1_320px] p-5">
            <h2 className="mb-2.5 text-[13px] font-bold">Por qué la unidad cambia</h2>
            <p className="mb-3 text-[11.5px] leading-relaxed text-apagado">
              El 90% no se alcanza esperando, se alcanza eligiendo la unidad más chica que acomode
              lo acumulado. Así la sucursal de bajo volumen sale en 2 días y no en 4.
            </p>
            <div className="grid grid-cols-3 gap-2.5">
              {[
                ['Tortón', 12, 11],
                ['Rabón', 6, 6],
                ['3.5 t', 3, 3],
              ].map(([n, cap, min]) => (
                <div key={String(n)} className="rounded-md border border-linea bg-piso/60 p-2.5">
                  <div className="text-[11px] font-bold">{n}</div>
                  <div className="num mt-0.5 font-mono text-base font-bold">{cap}</div>
                  <div className="text-[10px] text-apagado">tarimas · 90% = {min}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="tarjeta min-w-0 flex-[1_1_320px] p-5">
            <h2 className="mb-2.5 text-[13px] font-bold">Embarques programados hoy</h2>
            {programados.length === 0 ? (
              <p className="text-[11.5px] leading-relaxed text-apagado">
                Todavía ninguno. Programe una sucursal en verde, o libere una ámbar con acta, y
                aparece aquí.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {Object.entries(despacho).map(([suc, x]) => (
                  <li
                    key={suc}
                    className={`flex items-center gap-3 rounded-md border px-3 py-2.5 ${
                      x.acta ? 'border-ambar-bd bg-ambar-bg' : 'border-linea bg-piso/60'
                    }`}
                  >
                    <span className="w-[58px] font-mono text-[11px] font-bold">{suc}</span>
                    <span className="flex-grow font-mono text-[10.5px]">{x.folio}</span>
                    <span className="text-[10.5px] text-apagado">Salida {x.anden}</span>
                    {x.acta && (
                      <span className="rounded bg-ambar px-1.5 py-0.5 text-[9.5px] font-semibold text-white">
                        excepción
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-[11px] leading-relaxed text-apagado">
              De 8:00 a 13:00 la Salida 3 opera como{' '}
              <strong className="text-tinta">Andén 5 flex</strong> para recibo, lo que sube la
              capacidad de 32 a 36 citas diarias.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
