import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:5050' },
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('echarts')) return 'charts'
          if (id.includes('@tiptap') || id.includes('prosemirror')) return 'editor'
          if (id.includes('@mui') || id.includes('@emotion') || id.includes('react') || id.includes('redux')) return 'ui-vendor'
          return undefined
        },
      },
    },
  },
  test: { environment: 'jsdom' },
})
