import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '^/documents/[^/]+/download$': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/reports.csv': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '^/plans/[^/]+/(json|validation\\.csv)$': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '^/experiments/[^/]+/json$': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
