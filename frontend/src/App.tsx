import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import Documentos from './paginas/Documentos'
import Etiquetas from './paginas/Etiquetas'
import Handheld from './paginas/Handheld'
import Portal from './paginas/Portal'
import Tablero from './paginas/Tablero'

const PANTALLAS = [
  { a: '/', texto: 'Portal · C1', exacta: true },
  { a: '/handheld', texto: 'Handheld · C2' },
  { a: '/tablero', texto: 'Tablero · C3' },
  { a: '/etiquetas', texto: 'Etiquetas · C4' },
  { a: '/documentos', texto: 'Documentos · C5' },
]

/**
 * Barra de navegación del prototipo. No es parte del producto: existe para
 * moverse entre pantallas durante la demo. En producción cada pantalla vive
 * en un dispositivo distinto.
 *
 * Se oculta al imprimir, porque C4 y C5 se imprimen.
 */
function BarraDemo() {
  const clases = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-1.5 text-[12.5px] font-medium transition-colors ${
      isActive ? 'bg-white text-tinta' : 'text-linea-2 hover:text-white'
    }`

  return (
    <nav
      aria-label="Pantallas del prototipo"
      className="no-imprimir flex flex-wrap items-center gap-2 bg-tinta-2 px-4 py-2 print:hidden"
    >
      <span className="mr-2 text-[11px] font-semibold uppercase tracking-wide text-apagado-2">
        Prototipo
      </span>
      {PANTALLAS.map((p) => (
        <NavLink key={p.a} to={p.a} className={clases} end={p.exacta}>
          {p.texto}
        </NavLink>
      ))}
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <BarraDemo />
      <Routes>
        <Route path="/" element={<Portal />} />
        <Route path="/handheld" element={<Handheld />} />
        <Route path="/tablero" element={<Tablero />} />
        <Route path="/etiquetas" element={<Etiquetas />} />
        <Route path="/documentos" element={<Documentos />} />
      </Routes>
    </BrowserRouter>
  )
}
