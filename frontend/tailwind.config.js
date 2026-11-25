/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      // Paleta tomada del mockup. No inventar colores nuevos:
      // si hace falta uno, se agrega aquí y se documenta.
      colors: {
        tinta: { DEFAULT: '#16181D', 2: '#2B2F38' },
        apagado: { DEFAULT: '#5B6170', 2: '#6B7280' },
        linea: { DEFAULT: '#DFE1E6', 2: '#C9CDD4' },
        piso: '#F2F2F0',
        azul: { DEFAULT: '#1F5FD0', osc: '#17479C', bg: '#EAF1FD', bd: '#B9CFF4' },
        verde: { DEFAULT: '#0F7B4F', osc: '#0B5A3A', bg: '#E9F5EF', bd: '#A8D5BF' },
        rojo: { DEFAULT: '#C02626', osc: '#8A1A1A', bg: '#FCEDED', bd: '#F0BDBD' },
        ambar: { DEFAULT: '#B45309', osc: '#4A3410', bg: '#FDF6EC', bd: '#E8C89A' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      minHeight: {
        // RNF de usabilidad en andén: objetivo táctil mínimo
        toque: '44px',
      },
    },
  },
  plugins: [],
}
