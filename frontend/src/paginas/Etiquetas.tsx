/**
 * C4 · Etiquetas 4" x 6" de una cita.
 *
 * Con API: las etiquetas salen de `GET /citas/{folio}/etiquetas`, que el
 * servidor genera al reservar la cita en C1 (bultos con su QR firmado en la
 * base). El QR es real: apunte el celular y lee la cadena firmada completa.
 * Sin API: se muestra el paquete demo para que la presentación no se rompa.
 *
 * La etiqueta reproduce el mockup al pixel (`mockups/mockups-cedis.html`).
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import QRCode from 'qrcode'
import { URL_API, useCitas, useEtiquetasCita } from '../api/cliente'
import { PAQUETE_DEMO } from '../datos/paquete'
import type { ResumenCita } from '../tipos/api'

// ---------------------------------------------------------------------------
// Modelo de la vista (común a API y demo)
// ---------------------------------------------------------------------------

interface VistaEtiqueta {
  id_bulto: string
  sku: string
  descripcion: string
  sucursal: string
  nombre_sucursal: string
  cantidad: number
  peso_kg: number
  volumen_m3: number
  cadena_qr: string
}

interface VistaCita {
  folio: string
  orden_compra: string
  proveedor: string
  razon_social: string
  fecha: string
  anden: number
  hora_inicio: string
  hora_fin: string
}

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

/** "2026-11-26" + "10:00:00" + 5  ->  "26-nov · 10:00 · And. 5" */
function textoCita(c: VistaCita): string {
  const [, mes, dia] = c.fecha.split('-').map(Number)
  return `${dia}-${MESES[mes - 1]} · ${c.hora_inicio.slice(0, 5)} · And. ${c.anden}`
}

function fechaLarga(fecha: string): string {
  const [anio, mes, dia] = fecha.split('-').map(Number)
  return new Date(anio, mes - 1, dia).toLocaleDateString('es-MX', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}

const NOMBRE_SUCURSAL_DEMO: Record<string, string> = {
  'SUC-14': 'Plaza Oriente',
  'SUC-07': 'Norte',
  'SUC-21': 'Las Flores',
}

const CITA_DEMO: VistaCita = {
  folio: PAQUETE_DEMO.folio_cita,
  orden_compra: 'OC-88213',
  proveedor: 'PRV-0147',
  razon_social: 'Alimentos del Golfo, S.A. de C.V.',
  fecha: '2026-11-26',
  anden: 5,
  hora_inicio: '10:00:00',
  hora_fin: '12:30:00',
}

const ETIQUETAS_DEMO: VistaEtiqueta[] = PAQUETE_DEMO.bultos_esperados.map((b) => ({
  id_bulto: b.folio,
  sku: b.sku,
  descripcion: b.descripcion,
  sucursal: b.sucursal,
  nombre_sucursal: NOMBRE_SUCURSAL_DEMO[b.sucursal] ?? '',
  cantidad: b.piezas,
  peso_kg: b.peso_kg,
  volumen_m3: b.volumen_m3,
  cadena_qr: `v1|${b.folio}|${CITA_DEMO.orden_compra}|${CITA_DEMO.proveedor}|${b.sucursal}|${b.sku}|${b.piezas}|${b.peso_kg}|${b.volumen_m3}|${b.firma}`,
}))

function citaDeResumen(c: ResumenCita): VistaCita {
  return {
    folio: c.folio,
    orden_compra: c.orden_compra,
    proveedor: c.proveedor,
    razon_social: c.razon_social,
    fecha: c.fecha,
    anden: c.anden,
    hora_inicio: c.hora_inicio,
    hora_fin: c.hora_fin,
  }
}

// ---------------------------------------------------------------------------
// Piezas visuales
// ---------------------------------------------------------------------------

function Qr({ texto, lado }: { texto: string; lado: number }) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!ref.current) return
    // Nivel M de corrección: lo que pide la arquitectura §8 para una
    // etiqueta que va pegada en una caja y se maltrata.
    QRCode.toCanvas(ref.current, texto, {
      width: lado,
      margin: 1,
      errorCorrectionLevel: 'M',
      color: { dark: '#16181D', light: '#FFFFFF' },
    }).catch(() => {
      /* si falla, el canvas queda en blanco; el texto legible sigue abajo */
    })
  }, [texto, lado])

  return <canvas ref={ref} width={lado} height={lado} aria-label={`Código QR del bulto`} />
}

function Dato({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <div>
      <div className="text-[8.5px] font-bold uppercase tracking-wider text-apagado">{titulo}</div>
      <div className="num font-mono text-[15px] font-bold">{valor}</div>
    </div>
  )
}

function Etiqueta({
  e,
  cita,
  indice,
  total,
}: {
  e: VistaEtiqueta
  cita: VistaCita
  indice: number
  total: number
}) {
  const corte = e.cadena_qr.lastIndexOf('|') + 1
  return (
    <article
      aria-label={`Etiqueta del bulto ${e.id_bulto}`}
      className="etiqueta flex h-[576px] w-[384px] shrink-0 flex-col gap-3 border border-linea-2 bg-white p-[18px]"
    >
      <div className="flex items-start justify-between border-b-2 border-tinta pb-[9px]">
        <div className="min-w-0">
          <div className="text-[9px] font-bold uppercase tracking-widest text-apagado">
            Sucursal destino
          </div>
          <div className="text-[38px] font-bold leading-none tracking-tighter">{e.sucursal}</div>
          <div className="mt-px truncate text-[11px] font-medium">{e.nombre_sucursal}</div>
        </div>
        <div className="text-right">
          <div className="text-[9px] font-bold uppercase tracking-widest text-apagado">Bulto</div>
          <div className="font-mono text-xl font-bold">{e.id_bulto}</div>
          <div className="num mt-0.5 text-[9.5px] text-apagado">
            {indice} de {total}
          </div>
        </div>
      </div>

      <div className="flex items-start gap-[13px]">
        <div className="shrink-0">
          <Qr texto={e.cadena_qr} lado={128} />
        </div>
        <div className="flex min-w-0 flex-col gap-2">
          <div>
            <div className="text-[8.5px] font-bold uppercase tracking-wider text-apagado">SKU</div>
            <div className="font-mono text-[13px] font-bold">{e.sku}</div>
            <div className="mt-px text-[10px] leading-tight">{e.descripcion}</div>
          </div>
          <div className="flex gap-3.5">
            <Dato titulo="Piezas" valor={String(e.cantidad)} />
            <Dato titulo="Peso" valor={`${e.peso_kg} kg`} />
            <Dato titulo="Vol." valor={`${e.volumen_m3} m³`} />
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-[5px] border-t border-linea-2 pt-[9px] text-[10px]">
        <div className="flex justify-between">
          <span className="text-apagado">Orden de compra</span>
          <span className="font-mono font-semibold">{cita.orden_compra}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-apagado">Proveedor</span>
          <span className="font-mono font-semibold">{cita.proveedor}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-apagado">Cita</span>
          <span className="font-mono font-semibold">{textoCita(cita)}</span>
        </div>
      </div>

      <div className="rounded-[5px] bg-[#F4F5F7] px-[9px] py-2">
        <div className="mb-[3px] text-[8.5px] font-bold uppercase tracking-wider text-apagado">
          Contenido del QR · firmado
        </div>
        <div className="break-all font-mono text-[8.5px] leading-[1.45] text-tinta-2">
          {e.cadena_qr.slice(0, corte)}
          <strong className="text-verde">{e.cadena_qr.slice(corte)}</strong>
        </div>
      </div>

      <p className="mt-auto text-[9px] leading-[1.4] text-apagado">
        Los últimos {e.cadena_qr.length - corte} caracteres son el HMAC-SHA256 truncado. Una
        etiqueta fotocopiada o emitida fuera del sistema se rechaza en el andén.
      </p>
    </article>
  )
}

function OrigenDatos({ enVivo, cargando }: { enVivo: boolean; cargando: boolean }) {
  const [texto, clase, titulo] = cargando
    ? ['Conectando…', 'bg-tinta-2 text-linea-2', `Consultando ${URL_API}`]
    : enVivo
      ? ['En vivo · BD', 'bg-verde text-white', `GET ${URL_API}/citas`]
      : ['Demo sin conexión', 'bg-ambar text-white', `${URL_API} no respondió: datos de ejemplo`]
  return (
    <span title={titulo} className={`rounded-full px-2.5 py-1 text-[10.5px] font-semibold ${clase}`}>
      {texto}
    </span>
  )
}

function Indicador({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <div>
      <div className="text-[10.5px] text-linea-2">{titulo}</div>
      <div className="num text-xl font-bold">{valor}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Página
// ---------------------------------------------------------------------------

export default function Etiquetas() {
  const [params, setParams] = useSearchParams()
  const [filtro, setFiltro] = useState('')
  const [sucursal, setSucursal] = useState<string | null>(null)

  const citas = useCitas()
  const folioPedido = params.get('cita')
  // Sin ?cita= en la URL se toma la más reciente: es la que acaban de crear.
  const folio = folioPedido ?? citas.data?.[0]?.folio ?? null
  const etiquetas = useEtiquetasCita(folio)

  const sinApi = citas.isError || etiquetas.isError
  const cargando =
    !sinApi && (citas.isPending || (folio !== null && etiquetas.isPending))
  const enVivo = !sinApi && etiquetas.data !== undefined

  const cita: VistaCita = enVivo ? citaDeResumen(etiquetas.data.cita) : CITA_DEMO
  const todas: VistaEtiqueta[] = useMemo(
    () => (enVivo ? etiquetas.data.bultos : sinApi ? ETIQUETAS_DEMO : []),
    [enVivo, sinApi, etiquetas.data],
  )

  const porSucursal = useMemo(() => {
    const cuenta = new Map<string, number>()
    for (const e of todas) cuenta.set(e.sucursal, (cuenta.get(e.sucursal) ?? 0) + 1)
    return [...cuenta.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [todas])

  const visibles = useMemo(() => {
    const f = filtro.trim().toLowerCase()
    return todas.filter(
      (e) =>
        (!sucursal || e.sucursal === sucursal) &&
        (!f ||
          e.id_bulto.toLowerCase().includes(f) ||
          e.sku.toLowerCase().includes(f) ||
          e.sucursal.toLowerCase().includes(f)),
    )
  }, [todas, filtro, sucursal])

  const piezas = todas.reduce((s, e) => s + e.cantidad, 0)
  const pesoTotal = todas.reduce((s, e) => s + e.peso_kg, 0)
  const indiceDe = useMemo(() => new Map(todas.map((e, i) => [e.id_bulto, i + 1])), [todas])

  function elegirCita(nuevo: string) {
    setFiltro('')
    setSucursal(null)
    setParams(nuevo ? { cita: nuevo } : {})
  }

  return (
    <div className="flex min-h-screen flex-col bg-piso">
      <style>{`
        @page { size: 4in 6in; margin: 0; }
        @media print {
          .no-imprimir { display: none !important; }
          body, .bg-piso { background: #fff !important; }
          .hoja { display: block !important; padding: 0 !important; }
          .etiqueta { page-break-after: always; break-after: page; border: none !important; }
        }
      `}</style>

      <header className="no-imprimir flex flex-wrap items-center gap-5 bg-tinta px-7 py-4 text-white">
        <div className="min-w-0 flex-grow">
          <div className="flex items-center gap-2.5">
            <h1 className="text-[15px] font-semibold">Etiquetas de la cita</h1>
            <OrigenDatos enVivo={enVivo} cargando={cargando} />
          </div>
          <div className="mt-0.5 text-[11.5px] text-linea-2">
            {cargando
              ? 'Cargando…'
              : `${cita.razon_social} · ${cita.orden_compra} · ${fechaLarga(cita.fecha)}, ${cita.hora_inicio.slice(0, 5)}–${cita.hora_fin.slice(0, 5)} · andén ${cita.anden}`}
          </div>
        </div>
        <div className="flex flex-wrap gap-6">
          <Indicador titulo="Bultos" valor={String(todas.length)} />
          <Indicador titulo="Piezas" valor={piezas.toLocaleString('es-MX')} />
          <Indicador titulo="Sucursales" valor={String(porSucursal.length)} />
          <Indicador titulo="Peso total" valor={`${Math.round(pesoTotal).toLocaleString('es-MX')} kg`} />
        </div>
      </header>

      <div className="no-imprimir border-b border-linea bg-white px-7 py-3.5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[240px]">
            <label htmlFor="cita" className="etiqueta-campo mb-1.5">
              Cita
            </label>
            <select
              id="cita"
              value={folio ?? ''}
              onChange={(ev) => elegirCita(ev.target.value)}
              disabled={sinApi || !citas.data?.length}
              className="campo font-mono text-[13px] disabled:bg-piso"
            >
              {sinApi && <option value="">{CITA_DEMO.folio} · demo</option>}
              {citas.data?.map((c) => (
                <option key={c.folio} value={c.folio}>
                  {c.folio} · {c.proveedor} · And. {c.anden} {c.hora_inicio.slice(0, 5)}
                </option>
              ))}
            </select>
          </div>
          <div className="min-w-[220px] flex-grow sm:flex-grow-0">
            <label htmlFor="filtro" className="etiqueta-campo mb-1.5">
              Buscar
            </label>
            <input
              id="filtro"
              type="search"
              value={filtro}
              onChange={(ev) => setFiltro(ev.target.value)}
              placeholder="Bulto, SKU o sucursal"
              className="campo"
            />
          </div>
          <div className="ml-auto flex items-center gap-3">
            <span className="text-[11.5px] text-apagado">4″ × 6″ · una etiqueta por hoja</span>
            <button
              type="button"
              onClick={() => window.print()}
              disabled={!visibles.length}
              className="boton-primario"
            >
              {visibles.length === todas.length
                ? `Imprimir las ${visibles.length}`
                : `Imprimir ${visibles.length} de ${todas.length}`}
            </button>
          </div>
        </div>

        {porSucursal.length > 1 && (
          <div className="mt-3 flex flex-wrap gap-1.5" role="group" aria-label="Filtrar por sucursal">
            <button
              type="button"
              onClick={() => setSucursal(null)}
              aria-pressed={sucursal === null}
              className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                sucursal === null
                  ? 'border-tinta bg-tinta text-white'
                  : 'border-linea-2 bg-white text-apagado hover:bg-piso'
              }`}
            >
              Todas · {todas.length}
            </button>
            {porSucursal.map(([clave, n]) => (
              <button
                key={clave}
                type="button"
                onClick={() => setSucursal(sucursal === clave ? null : clave)}
                aria-pressed={sucursal === clave}
                className={`num rounded-full border px-2.5 py-1 font-mono text-[11px] font-semibold transition-colors ${
                  sucursal === clave
                    ? 'border-azul bg-azul text-white'
                    : 'border-linea-2 bg-white text-tinta-2 hover:bg-azul-bg'
                }`}
              >
                {clave} · {n}
              </button>
            ))}
          </div>
        )}
      </div>

      {sinApi && (
        <div className="no-imprimir border-b border-ambar-bd bg-ambar-bg px-7 py-2.5 text-[12px] text-ambar-osc">
          <strong>Sin conexión con {URL_API}.</strong> Se muestran las etiquetas de ejemplo. Al
          reservar una cita en el Portal con la API arriba, aquí aparecen sus etiquetas reales.
        </div>
      )}

      <main className="hoja flex-grow px-7 pb-10 pt-6">
        {cargando ? (
          <p className="no-imprimir py-16 text-center text-sm text-apagado">Cargando etiquetas…</p>
        ) : !visibles.length ? (
          <div className="no-imprimir tarjeta mx-auto max-w-md p-6 text-center">
            <h2 className="text-sm font-bold">
              {todas.length ? 'Ninguna etiqueta coincide' : 'Esta cita no tiene etiquetas'}
            </h2>
            <p className="mt-1.5 text-[12.5px] leading-relaxed text-apagado">
              {todas.length
                ? 'Cambie la búsqueda o el filtro de sucursal.'
                : 'La orden de compra ya no tiene piezas pendientes: todo su desglose quedó en citas anteriores.'}
            </p>
          </div>
        ) : (
          // La etiqueta mide 4" x 6" exactos y no se encoge: en celular se
          // desplaza dentro de su caja para no romper el ancho de la página.
          <div className="-mx-7 overflow-x-auto px-7 print:mx-0 print:overflow-visible print:px-0">
            <div className="mx-auto flex w-fit max-w-[1260px] flex-wrap justify-center gap-6 print:block">
              {visibles.map((e) => (
                <Etiqueta
                  key={e.id_bulto}
                  e={e}
                  cita={cita}
                  indice={indiceDe.get(e.id_bulto) ?? 0}
                  total={todas.length}
                />
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
