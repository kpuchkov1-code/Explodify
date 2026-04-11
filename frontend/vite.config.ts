import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    tailwindcss(),
    react(),
  ],
  server: {
    proxy: {
      '/jobs': 'http://localhost:8000',
      '/preview': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
    // /jobs already covers /jobs/{id}/frames — no extra entry needed
  },
})
