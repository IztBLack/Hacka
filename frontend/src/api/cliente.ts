/**
 * Cliente HTTP del backend CEDIS + hooks de react-query.
 *
 * Base URL: `VITE_API_URL` (frontend/.env), por defecto http://localhost:8000.
 *
 * Regla de la demo: si la API no responde, las pantallas caen a los datos de
 * `src/datos/ejemplo.ts`. Por eso aquí NO hay reintentos: un fallo de red
 * tiene que verse rápido (timeout corto) para que el respaldo entre de una.
 */

import { QueryClient, useMutation, useQuery } from '@tanstack/react-query'
import type {
  ErrorFastApi,
  RespuestaCapacidad,
  RespuestaCatalogo,
  RespuestaCierreCita,
  RespuestaCita,
  RespuestaEscaneo,
  RespuestaEtiquetasCita,
  ResumenCita,
  RespuestaSalud,
  RespuestaSlots,
  RespuestaTablero,
  SolicitudCita,
  SolicitudEscaneo,
  SolicitudSlots,
} from '../tipos/api'

export const URL_API: string = (
  (import.meta.env.VITE_API_URL as string | undefined) || 'http://localhost:8000'
).replace(/\/+$/, '')

/** Lo que tarda en rendirse una llamada antes de usar la demo. */
const TIMEOUT_MS = 3000

/**
 * Error de la API. `status` 0 = no hubo respuesta (red caída, CORS, timeout):
 * es el único caso en que conviene caer a la demo. Un 404/409/422 es una
 * respuesta de negocio y se muestra tal cual.
 */
export class ErrorApi extends Error {
  readonly status: number

  constructor(status: number, mensaje: string) {
    super(mensaje)
    this.name = 'ErrorApi'
    this.status = status
  }

  get sinConexion(): boolean {
    return this.status === 0
  }
}

export function esSinConexion(error: unknown): boolean {
  return !(error instanceof ErrorApi) || error.sinConexion
}

function mensajeDe(cuerpo: ErrorFastApi | null, status: number): string {
  const detalle = cuerpo?.detail
  if (typeof detalle === 'string') return detalle
  if (Array.isArray(detalle) && detalle.length) {
    return detalle.map((d) => `${d.loc.slice(1).join('.')}: ${d.msg}`).join('; ')
  }
  return `HTTP ${status}`
}

async function pedir<T>(ruta: string, init?: RequestInit & { cuerpo?: unknown }): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(`${URL_API}${ruta}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
      body: init?.cuerpo !== undefined ? JSON.stringify(init.cuerpo) : init?.body,
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })
  } catch (e) {
    throw new ErrorApi(0, e instanceof Error ? e.message : 'sin conexión con la API')
  }
  if (!resp.ok) {
    const cuerpo = (await resp.json().catch(() => null)) as ErrorFastApi | null
    throw new ErrorApi(resp.status, mensajeDe(cuerpo, resp.status))
  }
  return (await resp.json()) as T
}

const post = <T>(ruta: string, cuerpo: unknown) => pedir<T>(ruta, { method: 'POST', cuerpo })

// ---------------------------------------------------------------------------
// Endpoints (rutas reales, sin /v1)
// ---------------------------------------------------------------------------

export const api = {
  salud: () => pedir<RespuestaSalud>('/salud'),

  capacidad: () => pedir<RespuestaCapacidad>('/citas/capacidad'),
  slots: (s: SolicitudSlots) => post<RespuestaSlots>('/citas/slots', s),
  reservarCita: (s: SolicitudCita) => post<RespuestaCita>('/citas', s),
  citas: (fecha?: string) =>
    pedir<ResumenCita[]>(fecha ? `/citas?fecha=${encodeURIComponent(fecha)}` : '/citas'),
  etiquetasCita: (folio: string) =>
    pedir<RespuestaEtiquetasCita>(`/citas/${encodeURIComponent(folio)}/etiquetas`),

  escanear: (s: SolicitudEscaneo) => post<RespuestaEscaneo>('/recepcion/escaneo', s),
  cerrarCita: (folio: string) =>
    post<RespuestaCierreCita>(`/recepcion/cierre/${encodeURIComponent(folio)}`, {}),

  tablero: () => pedir<RespuestaTablero>('/consolidacion/tablero'),
  catalogo: () => pedir<RespuestaCatalogo>('/consolidacion/catalogo'),
}

// ---------------------------------------------------------------------------
// React Query
// ---------------------------------------------------------------------------

export const clienteQuery = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false, staleTime: 15_000 },
    mutations: { retry: false },
  },
})

export const claves = {
  tablero: ['consolidacion', 'tablero'] as const,
  slots: (s: SolicitudSlots) =>
    ['citas', 'slots', s.fecha, s.n_bultos, s.incluir_anden_flex ?? true] as const,
}

/** Tablero de consolidación. Refresca cada 30 s: es una pantalla de pared. */
export function useTablero() {
  return useQuery({
    queryKey: claves.tablero,
    queryFn: api.tablero,
    refetchInterval: (q) => (q.state.status === 'error' ? false : 30_000),
  })
}

export function useSlots(s: SolicitudSlots, habilitado = true) {
  return useQuery({
    queryKey: claves.slots(s),
    queryFn: () => api.slots(s),
    enabled: habilitado,
    placeholderData: (previo) => previo,
  })
}

export function useReservarCita() {
  return useMutation({
    mutationFn: api.reservarCita,
    onSuccess: (cita) => {
      void clienteQuery.invalidateQueries({ queryKey: ['citas', 'slots', cita.fecha] })
      // La cita nueva aparece de inmediato en el selector de etiquetas (C4).
      void clienteQuery.invalidateQueries({ queryKey: ['citas', 'lista'] })
    },
  })
}

/** Citas registradas, las más recientes primero (selector de C4). */
export function useCitas() {
  return useQuery({ queryKey: ['citas', 'lista'] as const, queryFn: () => api.citas() })
}

/** Etiquetas firmadas de una cita: lo que C4 imprime y C2 escanea. */
export function useEtiquetasCita(folio: string | null) {
  return useQuery({
    queryKey: ['citas', 'etiquetas', folio] as const,
    queryFn: () => api.etiquetasCita(folio as string),
    enabled: folio !== null,
  })
}
