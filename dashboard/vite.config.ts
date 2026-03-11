import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/',
  define: {
    'import.meta.env.VITE_USE_MOCK': JSON.stringify(process.env.VITE_USE_MOCK || 'true'),
  },
  server: {
    port: 5173,
    proxy: {
      '/dashboard': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
