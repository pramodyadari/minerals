import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/analyze': 'http://127.0.0.1:8001',
      '/api': 'http://127.0.0.1:8001',
      '/health': 'http://127.0.0.1:8001',
      '/evidence': 'http://127.0.0.1:8001',
      '/candidate-zones': 'http://127.0.0.1:8001',
      '/satellite-scenes': 'http://127.0.0.1:8001',
      '/production-forecast': 'http://127.0.0.1:8001',
      '/classify-image': 'http://127.0.0.1:8001'
    }
  }
})
