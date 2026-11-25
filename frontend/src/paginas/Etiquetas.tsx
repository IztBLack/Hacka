/**
 * C4 · Generador de etiquetas 4" x 6".
 *
 * Diferencia con el mockup: aquí el QR es REAL y escaneable. El del mockup
 * era un patrón decorativo. Apunte el celular y va a leer la cadena firmada
 * completa — que es justo lo que el jurado va a querer probar.
 *
 * En producción el PDF lo arma Playwright del lado del servidor (§2 de la
 * arquitectura). Aquí se imprime desde el navegador, que para el prototipo
 * da el mismo resultado y no necesita backend.
 */

import { useEffect, useRef, useState } from 'react'
import QRCode from 'qrcode'
import { PAQUETE_DEMO } from '../datos/paquete'
import type { BultoEsperado } from '../tipos/api'

const OC = 'OC-88213'
const PROVEEDOR = 'PRV-0147'

const NOMBRE_SUCURSAL: Record<string, string> = {
  'SUC-14': 'Plaza Oriente',
  'SUC-07': 'Norte',
  'SUC-21': 'Las Flores',
}

function cadenaQr(b: BultoEsperado): string {
  return `v1|${b.folio}|${OC}|${PROVEEDOR}|${b.sucursal}|${b.sku}|${b.piezas}|${b.peso_kg}|${b.volumen_m3}|${b.firma}`
}

function Qr({ texto, lado }: { texto: string; lado: number }) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!ref.current) return
    // Nivel M de corrección de errores: lo que recomienda la arquitectura §8
    // para una etiqueta que va pegada en una caja y se maltrata.
    QRCode.toCanvas(ref.current, texto, {
      width: lado,
      margin: 1,
      errorCorrectionLevel: 'M',
      color: { dark: '#16181D', light: '#FFFFFF' },
    }).catch(() => {
      /* si falla, el canvas queda en blanco; el texto legible sigue abajo */
    })
  }, [texto, lado])

  return <canvas ref={ref} width={lado} height={lado} aria-label={`Código QR de ${texto}`} />
}

function Etiqueta({ b, indice, total }: { b: BultoEsperado; indice: number; total: number }) {
  const cadena = cadenaQr(b)

  return (
    <article className="etiqueta flex h-[576px] w-[384px] flex-col gap-3 border border-linea-2 bg-white p-[18px]">
      <div className="flex items-start justify-between border-b-2 border-tinta pb-2.5">
        <div>
          <div className="text-[9px] font-bold uppercase tracking-widest text-apagado">
            Sucursal destino
          </div>
          <div className="text-[38px] font-bold leading-none tracking-tighter">{b.sucursal}</div>
          <div className="mt-0.5 text-[11px] font-medium">{NOMBRE_SUCURSAL[b.sucursal] ?? ''}</div>
        </div>
        <div className="text-right">
          <div className="text-[9px] font-bold uppercase tracking-widest text-apagado">Bulto</div>
          <div className="font-mono text-xl font-bold">{b.folio}</div>
          <div className="num mt-0.5 text-[9.5px] text-apagado">
            {indice} de {total}
          </div>
        </div>
      </div>

      <div className="flex items-start gap-3">
        <div className="shrink-0">
          <Qr texto={cadena} lado={128} />
        </div>
        <div className="flex min-w-0 flex-col gap-2">
          <div>
            <div className="text-[8.5px] font-bold uppercase tracking-wider text-apagado">SKU</div>
            <div className="font-mono text-[13px] font-bold">{b.sku}</div>
            <div className="mt-0.5 text-[10px] leading-tight">{b.descripcion}</div>
          </div>
          <div className="flex gap-3.5">
            <div>
              <div className="text-[8.5px] font-bold uppercase tracking-wider text-apagado">
                Piezas
              </div>
              <div className="num font-mono text-[15px] font-bold">{b.piezas}</div>
            </div>
            <div>
              <div className="text-[8.5px] font-bold uppercase tracking-wider text-apagado">
                Peso
              </div>
              <div className="num font-mono text-[15px] font-bold">{b.peso_kg} kg</div>
            </div>
            <div>
              <div className="text-[8.5px] font-bold uppercase tracking-wider text-apagado">
                Vol.
              </div>
              <div className="num font-mono text-[15px] font-bold">{b.volumen_m3} m³</div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-1.5 border-t border-linea-2 pt-2.5 text-[10px]">
        <div className="flex justify-between">
          <span className="text-apagado">Orden de compra</span>
          <span className="font-mono font-semibold">{OC}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-apagado">Proveedor</span>
          <span className="font-mono font-semibold">{PROVEEDOR}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-apagado">Cita</span>
          <span className="font-mono font-semibold">26-nov · 10:00 · And. 5</span>
        </div>
      </div>

      <div className="rounded bg-piso px-2.5 py-2">
        <div className="mb-1 text-[8.5px] font-bold uppercase tracking-wider text-apagado">
          Contenido del QR · firmado
        </div>
        <div className="break-all font-mono text-[8.5px] leading-snug text-tinta-2">
          {cadena.slice(0, cadena.lastIndexOf('|') + 1)}
          <strong className="text-verde">{b.firma}</strong>
        </div>
      </div>

      <p className="text-[9px] leading-snug text-apagado">
        Los últimos 13 caracteres son el HMAC-SHA256 truncado. Una etiqueta fotocopiada o emitida
        fuera del sistema se rechaza en el andén.
      </p>
    </article>
  )
}

export default function Etiquetas() {
  const [filtro, setFiltro] = useState('')
  const bultos = PAQUETE_DEMO.bultos_esperados.filter(
    (b) =>
      !filtro ||
      b.folio.toLowerCase().includes(filtro.toLowerCase()) ||
      b.sucursal.toLowerCase().includes(filtro.toLowerCase()),
  )

  return (
    <div className="min-h-screen bg-piso p-6">
      <style>{`
        @media print {
          .no-imprimir { display: none !important; }
          body { background: #fff; }
          .etiqueta {
            page-break-after: always;
            border: none;
            box-shadow: none;
          }
        }
      `}</style>

      <div className="no-imprimir mx-auto mb-6 max-w-5xl">
        <h1 className="text-xl font-bold tracking-tight">Etiquetas de la cita</h1>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-apagado">
          Estos códigos QR son reales: apunte el celular y va a leer la cadena firmada completa. En
          producción el PDF lo genera el servidor; aquí se imprime desde el navegador.
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label htmlFor="filtro" className="sr-only">
            Filtrar por folio o sucursal
          </label>
          <input
            id="filtro"
            type="search"
            value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
            placeholder="Filtrar por folio o sucursal"
            className="campo max-w-xs"
          />
          <button type="button" onClick={() => window.print()} className="boton-primario">
            Imprimir las {bultos.length}
          </button>
          <span className="text-[11.5px] text-apagado">
            Tamaño 4&quot; × 6&quot; · una etiqueta por hoja
          </span>
        </div>
      </div>

      {/* La etiqueta mide 4" x 6" exactos y no se encoge: en celular se
          desplaza dentro de su caja para no romper el ancho de la página. */}
      <div className="-mx-6 overflow-x-auto px-6 print:mx-0 print:overflow-visible print:px-0">
        <div className="mx-auto flex w-fit max-w-5xl flex-wrap justify-center gap-6">
          {bultos.map((b, i) => (
          <Etiqueta
            key={b.folio}
            b={b}
            indice={i + 1}
              total={PAQUETE_DEMO.bultos_esperados.length}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
