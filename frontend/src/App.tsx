import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import Handheld from './paginas/Handheld'
import Portal from './paginas/Portal'

/**
 * Barra de navegación del prototipo. No es parte del producto: existe para
 * moverse entre pantallas durante la demo. En producción cada pantalla vive
 * en un dispositivo distinto.
 */
function BarraDemo() {
  const clases = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-1.5 text-[12.5px] font-medium transition-colors ${
      isActive ? 'bg-white text-tinta' : 'text-linea-2 hover:text-white'
    }`

  return (
    <nav
      aria-label="Pantallas del prototipo"
      className="flex items-center gap-2 bg-tinta-2 px-4 py-2"
    >
      <span className="mr-2 text-[11px] font-semibold uppercase tracking-wide text-apagado-2">
        Prototipo
      </span>
      <NavLink to="/" className={clases} end>
        Portal · C1
      </NavLink>
      <NavLink to="/handheld" className={clases}>
        Handheld · C2
      </NavLink>
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
      </Routes>
    </BrowserRouter>
  )
}
