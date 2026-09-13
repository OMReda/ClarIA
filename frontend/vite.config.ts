import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'


export default defineConfig({
  plugins: [
    react(),
    basicSsl()
  ],
  server: {
    host: '0.0.0.0',
    port: 5173,
    https: true,
    allowedHosts: true,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws':  { target: 'ws://localhost:8000', ws: true },
      '/realms': { target: 'http://localhost:8080', xfwd: true },
      '/resources': { target: 'http://localhost:8080', xfwd: true },
      '/admin': { target: 'http://localhost:8080', xfwd: true },
      '/js': { target: 'http://localhost:8080', xfwd: true },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    allowedHosts: true,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws':  { target: 'ws://localhost:8000', ws: true },
      '/realms': { target: 'http://localhost:8080', xfwd: true },
      '/resources': { target: 'http://localhost:8080', xfwd: true },
      '/admin': { target: 'http://localhost:8080', xfwd: true },
      '/js': { target: 'http://localhost:8080', xfwd: true },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('echarts')) return 'echarts'
          if (id.includes('ag-grid')) return 'ag-grid'
          if (
            id.includes('node_modules/react') ||
            id.includes('node_modules/react-dom') ||
            id.includes('node_modules/zustand') ||
            id.includes('node_modules/axios') ||
            id.includes('node_modules/zod')
          ) return 'vendor'
        },
      },
    },
  },
})
