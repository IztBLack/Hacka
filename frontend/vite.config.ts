import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  resolve: {
    // Sin esto, Vite le entrega a react-router-dom su propia copia de React
    // y revienta con "Invalid hook call" en el servidor de desarrollo.
    // La compilación de producción no lo sufre, así que el error solo aparece
    // trabajando: justo donde más estorba.
    dedupe: ['react', 'react-dom'],
  },

  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom'],
  },
})
