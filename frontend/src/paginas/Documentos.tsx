/**
 * C5 · Relación de Embarque y Acta de Faltante.
 *
 * Los dos documentos de salida, tamaño carta, listos para imprimir o
 * guardar como PDF desde el navegador.
 *
 * El QR maestro es real: la sucursal lo escanea y da entrada al lote
 * completo de un golpe, que es el punto del §6.9 de la arquitectura.
 */

import { useEffect, useRef } from 'react'
import QRCode from 'qrcode'

const REL = 'REL-2026-01184'
const ACTA = 'ACT-2026-0392'

/** Lo que la sucursal escanea al recibir. */
const QR_MAESTRO = `v1m|${REL}|SUC-14|11|164|SL-0099781`

interface Tarima {
  id: string
  origen: string
  bultos: number
  sku: string
  piezas: number
  peso: number
  oc: string
}

const TARIMAS: Tarima[] = [
  { id: 'T-0441', origen: 'SUC14-N1-P02', bultos: 16, sku: 'SKU-993201', piezas: 384, peso: 1012, oc: 'OC-88213' },
  { id: 'T-0442', origen: 'SUC14-N1-P03', bultos: 15, sku: 'SKU-993201', piezas: 360, peso: 984, oc: 'OC-88213' },
  { id: 'T-0443', origen: 'SUC14-N1-P06', bultos: 14, sku: 'SKU-771045', piezas: 336, peso: 1105, oc: 'OC-88213' },
  { id: 'T-0444', origen: 'SUC14-N2-P01', bultos: 16, sku: 'SKU-771045', piezas: 384, peso: 1142, oc: 'OC-88198' },
  { id: 'T-0445', origen: 'SUC14-N2-P05', bultos: 15, sku: 'SKU-883417', piezas: 360, peso: 897, oc: 'OC-88198' },
  { id: 'T-0446', origen: 'SUC14-N2-P07', bultos: 14, sku: 'SKU-883417', piezas: 336, peso: 921, oc: 'OC-88198' },
  { id: 'T-0447', origen: 'SUC14-N3-P02', bultos: 16, sku: 'SKU-610238', piezas: 384, peso: 1068, oc: 'OC-88176' },
  { id: 'T-0448', origen: 'SUC14-N3-P04', bultos: 15, sku: 'SKU-610238', piezas: 360, peso: 1004, oc: 'OC-88176' },
  { id: 'T-0449', origen: 'SUC14-N3-P08', bultos: 14, sku: 'SKU-452190', piezas: 336, peso: 876, oc: 'OC-88176' },
  { id: 'T-0450', origen: 'cross-dock · And. 2', bultos: 15, sku: 'SKU-993201', piezas: 360, peso: 942, oc: 'OC-88213' },
  { id: 'T-0451', origen: 'cross-dock · And. 2', bultos: 14, sku: 'SKU-452190', piezas: 336, peso: 889, oc: 'OC-88213' },
]

const FALTANTES = [
  { sku: 'SKU-771045', desc: 'Frijol bayo en salmuera 560 g', suc: 'SUC-07', pedido: 240, recibido: 192, importe: 2976 },
  { sku: 'SKU-883417', desc: 'Chiles jalapeños rebanados 380 g', suc: 'SUC-14', pedido: 180, recibido: 156, importe: 1488 },
  { sku: 'SKU-610238', desc: 'Salsa de tomate 1 kg', suc: 'SUC-21', pedido: 300, recibido: 264, importe: 2232 },
  { sku: 'SKU-452190', desc: 'Elote dorado en grano 410 g', suc: 'SUC-28', pedido: 220, recibido: 184, importe: 2268 },
]

function Qr({ texto, lado }: { texto: string; lado: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    if (!ref.current) return
    QRCode.toCanvas(ref.current, texto, {
      width: lado,
      margin: 1,
      errorCorrectionLevel: 'M',
      color: { dark: '#16181D', light: '#FFFFFF' },
    }).catch(() => {})
  }, [texto, lado])
  return <canvas ref={ref} width={lado} height={lado} aria-label={`Código QR maestro ${texto}`} />
}

function Dato({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex justify-between border-b border-dotted border-linea-2 pb-1">
      <span className="text-apagado">{k}</span>
      <strong className={`font-bold ${mono ? 'font-mono' : ''}`}>{v}</strong>
    </div>
  )
}

function Metrica({ k, v, sub, tono }: { k: string; v: string; sub?: string; tono?: string }) {
  return (
    <div className={`flex-1 rounded-md border p-2.5 ${tono ?? 'border-linea bg-piso/60'}`}>
      <div className="text-[9px] font-bold uppercase tracking-wider text-apagado">{k}</div>
      <div className="num text-[19px] font-bold">{v}</div>
      {sub && <div className="text-[9.5px] text-apagado">{sub}</div>}
    </div>
  )
}

function RelacionEmbarque() {
  const totalBultos = TARIMAS.reduce((s, t) => s + t.bultos, 0)
  const totalPiezas = TARIMAS.reduce((s, t) => s + t.piezas, 0)
  const totalPeso = TARIMAS.reduce((s, t) => s + t.peso, 0)

  return (
    <article className="hoja w-[816px] bg-white px-[52px] py-[54px] text-[11.5px] leading-relaxed">
      <div className="flex items-start justify-between border-b-[3px] border-tinta pb-3.5">
        <div>
          <h2 className="text-[21px] font-bold tracking-tight">RELACIÓN DE EMBARQUE</h2>
          <div className="mt-1 text-[11px] text-apagado">
            Centro de Distribución · Salida a sucursal
          </div>
          <div className="mt-2 font-mono text-[15px] font-bold">{REL}</div>
        </div>
        <div className="text-center">
          <Qr texto={QR_MAESTRO} lado={104} />
          <div className="mt-1 text-[8.5px] font-semibold tracking-wide text-apagado">
            QR MAESTRO
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-7 gap-y-2">
        <Dato k="Sucursal destino" v="SUC-14 · Plaza Oriente" />
        <Dato k="Placas" v="AB-472-TR" mono />
        <Dato k="Fecha y hora de salida" v="26-nov-2026 · 15:48" />
        <Dato k="Operador" v="J. Martínez Ruiz" />
        <Dato k="Andén de embarque" v="Salida 2" />
        <Dato k="Sello de seguridad" v="SL-0099781" mono />
        <Dato k="Clase de unidad" v="Tortón · 12 posiciones" />
        <Dato k="Kilometraje de salida" v="148,206 km" mono />
      </div>

      <div className="mt-4 flex gap-2.5">
        <Metrica k="Posiciones" v="11 / 12" sub="91.7%" />
        <Metrica k="Peso" v={totalPeso.toLocaleString('es-MX')} sub="de 12,000 kg" />
        <Metrica k="Volumen" v="26.2" sub="de 28.6 m³" />
        <Metrica
          k="Regla 90%"
          v="CUMPLE"
          sub="sin excepción"
          tono="border-verde-bd bg-verde-bg text-verde"
        />
      </div>

      <div className="mt-5">
        <h3 className="mb-2 text-xs font-bold">
          Detalle por tarima — {TARIMAS.length} tarimas · {totalBultos} bultos
        </h3>
        <table className="w-full border-collapse text-[10px]">
          <thead>
            <tr className="border-b-[1.5px] border-tinta">
              {['Tarima', 'Posición origen', 'Bultos', 'SKU principal', 'Piezas', 'Peso kg', 'OC'].map(
                (h, i) => (
                  <th
                    key={h}
                    className={`px-1 py-1.5 font-bold ${i === 2 || i === 4 || i === 5 ? 'text-right' : 'text-left'}`}
                  >
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {TARIMAS.map((t) => {
              const cd = t.origen.startsWith('cross-dock')
              return (
                <tr key={t.id} className={`border-b border-linea/60 ${cd ? 'bg-azul-bg/50' : ''}`}>
                  <td className="px-1 py-1.5 font-mono font-semibold">{t.id}</td>
                  <td
                    className={`px-1 py-1.5 font-mono ${cd ? 'font-semibold text-azul-osc' : 'text-apagado'}`}
                  >
                    {t.origen}
                  </td>
                  <td className="num px-1 py-1.5 text-right">{t.bultos}</td>
                  <td className="px-1 py-1.5 font-mono">{t.sku}</td>
                  <td className="num px-1 py-1.5 text-right">{t.piezas}</td>
                  <td className="num px-1 py-1.5 text-right">{t.peso.toLocaleString('es-MX')}</td>
                  <td className="px-1 py-1.5 font-mono text-apagado">{t.oc}</td>
                </tr>
              )
            })}
          </tbody>
          <tfoot>
            <tr className="border-t-[1.5px] border-tinta font-bold">
              <td colSpan={2} className="px-1 py-1.5">
                Total
              </td>
              <td className="num px-1 py-1.5 text-right">{totalBultos}</td>
              <td />
              <td className="num px-1 py-1.5 text-right">{totalPiezas.toLocaleString('es-MX')}</td>
              <td className="num px-1 py-1.5 text-right">{totalPeso.toLocaleString('es-MX')}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="mt-4 rounded-md border border-linea bg-piso/60 px-3 py-2.5">
        <div className="mb-1 text-[9px] font-bold uppercase tracking-wider text-apagado">
          Complemento Carta Porte 3.1
        </div>
        <div className="flex flex-wrap gap-x-5 text-[10px] leading-loose">
          <span className="text-apagado">
            Permiso SICT: <strong className="font-mono text-tinta">TPAF01 / 0412-2024</strong>
          </span>
          <span className="text-apagado">
            Config. vehicular: <strong className="font-mono text-tinta">C3</strong>
          </span>
          <span className="text-apagado">
            Aseguradora: <strong className="text-tinta">Qualitas</strong>
          </span>
          <span className="text-apagado">
            Póliza: <strong className="font-mono text-tinta">4471-889-02</strong>
          </span>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-3 gap-6">
        {['Jefe de embarques', 'Operador de la unidad', 'Recibe en sucursal'].map((f) => (
          <div
            key={f}
            className="border-t border-tinta pt-1.5 text-center text-[9.5px] text-apagado"
          >
            {f}
          </div>
        ))}
      </div>

      <p className="mt-4 text-[9px] leading-snug text-apagado">
        La sucursal da entrada al lote completo escaneando el QR maestro. Cada bulto conserva su
        propio QR firmado para conciliación individual.
      </p>
    </article>
  )
}

function ActaFaltante() {
  const totalImporte = FALTANTES.reduce((s, f) => s + f.importe, 0)
  const totalDelta = FALTANTES.reduce((s, f) => s + (f.recibido - f.pedido), 0)

  return (
    <article className="hoja w-[816px] bg-white px-[52px] py-[54px] text-[11.5px] leading-relaxed">
      <div className="flex items-start justify-between border-b-[3px] border-ambar pb-3.5">
        <div>
          <h2 className="text-[21px] font-bold tracking-tight">ACTA DE FALTANTE</h2>
          <div className="mt-1 text-[11px] text-apagado">Cierre parcial de orden de compra</div>
          <div className="mt-2 font-mono text-[15px] font-bold">{ACTA}</div>
        </div>
        <div className="rounded-md border border-ambar-bd bg-ambar-bg px-3 py-2 text-right">
          <div className="text-[9px] font-bold uppercase tracking-wider text-ambar-osc">
            Estado de la OC
          </div>
          <div className="mt-0.5 text-sm font-bold text-ambar">CERRADA PARCIAL</div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-7 gap-y-2">
        <Dato k="Orden de compra" v="OC-88213" mono />
        <Dato k="Cita" v="26-nov · 10:00 · And. 5" />
        <Dato k="Proveedor" v="Alimentos del Golfo" />
        <Dato k="Cierre de recepción" v="26-nov-2026 · 12:38" />
        <Dato k="UUID del CFDI" v="3F2A9C41-…-C6D80F4B1E77" mono />
        <Dato k="Operador de recibo" v="R. Ibarra Cruz" />
      </div>

      <div className="mt-4 flex gap-2.5">
        <Metrica k="Bultos en OC" v="148" />
        <Metrica k="Recibidos" v="141" tono="border-verde-bd bg-verde-bg text-verde" />
        <Metrica k="Faltantes" v="6" tono="border-rojo-bd bg-rojo-bg text-rojo" />
        <Metrica k="Rechazados" v="1" tono="border-rojo-bd bg-rojo-bg text-rojo" />
      </div>

      <div className="mt-5">
        <h3 className="mb-2 text-xs font-bold">Detalle del faltante</h3>
        <table className="w-full border-collapse text-[10px]">
          <thead>
            <tr className="border-b-[1.5px] border-tinta">
              {['SKU', 'Descripción', 'Sucursal', 'Pedido', 'Recibido', 'Delta', 'Importe'].map(
                (h, i) => (
                  <th
                    key={h}
                    className={`px-1 py-1.5 font-bold ${i >= 3 ? 'text-right' : 'text-left'}`}
                  >
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {FALTANTES.map((f) => (
              <tr key={f.sku} className="border-b border-linea/60">
                <td className="px-1 py-1.5 font-mono font-semibold">{f.sku}</td>
                <td className="px-1 py-1.5 text-tinta-2">{f.desc}</td>
                <td className="px-1 py-1.5 font-mono text-apagado">{f.suc}</td>
                <td className="num px-1 py-1.5 text-right">{f.pedido}</td>
                <td className="num px-1 py-1.5 text-right">{f.recibido}</td>
                <td className="num px-1 py-1.5 text-right font-semibold text-rojo">
                  {f.recibido - f.pedido}
                </td>
                <td className="num px-1 py-1.5 text-right">
                  ${f.importe.toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-[1.5px] border-tinta font-bold">
              <td colSpan={5} className="px-1 py-2">
                Importe no surtido — base para nota de crédito
              </td>
              <td className="num px-1 py-2 text-right text-rojo">{totalDelta} pz</td>
              <td className="num px-1 py-2 text-right">
                ${totalImporte.toLocaleString('es-MX', { minimumFractionDigits: 2 })}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="mt-4 rounded-md border border-rojo-bd bg-rojo-bg px-3.5 py-3">
        <div className="mb-1 text-[11px] font-bold text-rojo-osc">
          Bulto rechazado en el mismo acto
        </div>
        <p className="text-[10.5px] leading-relaxed text-rojo-osc">
          <span className="font-mono font-semibold">B00447</span> · SKU-993201 · 24 pz · excedente
          de 24 piezas sobre las 480 autorizadas. Devuelto al proveedor en el andén. Acta{' '}
          <span className="font-mono">ACT-2026-0391</span>.
        </p>
      </div>

      <div className="mt-4">
        <h3 className="mb-2 text-[11px] font-bold">Acciones disparadas automáticamente</h3>
        <ol className="list-decimal space-y-1 pl-5 text-[10.5px] leading-relaxed text-tinta-2">
          <li>
            La OC-88213 se cierra como <strong>parcial</strong>; las 144 piezas faltantes quedan
            liberadas para reorden.
          </li>
          <li>Se notifica a Compras y al comprador responsable de la categoría.</li>
          <li>
            Se solicita <strong>nota de crédito</strong> al proveedor por $
            {totalImporte.toLocaleString('es-MX', { minimumFractionDigits: 2 })} contra el CFDI
            timbrado.
          </li>
          <li>
            Las 4 sucursales afectadas reciben aviso de surtido incompleto antes del embarque.
          </li>
          <li>
            El score del proveedor PRV-0147 baja de <strong>94 a 91</strong> por exactitud
            documental.
          </li>
        </ol>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-6">
        {['Operador de recibo', 'Representante del proveedor'].map((f) => (
          <div
            key={f}
            className="border-t border-tinta pt-1.5 text-center text-[9.5px] text-apagado"
          >
            {f}
          </div>
        ))}
      </div>

      <p className="mt-4 text-[9px] leading-snug text-apagado">
        Documento generado por el sistema al cerrar la cita. El reto señala que «los faltantes y
        excedentes se detectan tarde»: aquí quedan asentados antes de que la unidad salga del patio.
      </p>
    </article>
  )
}

export default function Documentos() {
  return (
    <div className="min-h-screen bg-piso p-6">
      <style>{`
        @media print {
          .no-imprimir { display: none !important; }
          body { background: #fff; }
          .hoja { page-break-after: always; box-shadow: none; }
        }
      `}</style>

      <div className="no-imprimir mx-auto mb-6 max-w-[816px]">
        <h1 className="text-xl font-bold tracking-tight">Documentos de salida</h1>
        <p className="mt-1 text-sm leading-relaxed text-apagado">
          Tamaño carta, listos para imprimir o guardar como PDF. El QR maestro es real: la sucursal
          lo escanea y da entrada al lote completo.
        </p>
        <button type="button" onClick={() => window.print()} className="boton-primario mt-4">
          Imprimir o guardar como PDF
        </button>
      </div>

      {/* En pantalla chica la hoja carta no cabe. Se desplaza dentro de su
          caja en vez de romper el ancho de la página; al imprimir no aplica,
          porque ahí la hoja sí mide carta de verdad. */}
      <div className="-mx-6 overflow-x-auto px-6 print:mx-0 print:overflow-visible print:px-0">
        <div className="mx-auto flex w-[816px] flex-col gap-8">
          <RelacionEmbarque />
          <ActaFaltante />
        </div>
      </div>
    </div>
  )
}
