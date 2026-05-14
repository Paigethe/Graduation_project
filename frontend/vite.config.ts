import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:52517',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    // Work around Node 23 + esbuild prebundle issue on lodash-es in dev mode.
    exclude: ['lodash-es'],
  },
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return

          if (id.includes('node_modules/element-plus')) return 'vendor-element-plus'

          if (id.includes('node_modules/@vue')) return 'vendor-vue'
          if (id.includes('node_modules/vue-router')) return 'vue-router'
          if (id.includes('node_modules/pinia')) return 'pinia'
          if (id.includes('node_modules/lucide-vue-next')) return 'lucide'
          if (id.includes('node_modules/dayjs')) return 'dayjs'
          if (id.includes('node_modules/axios')) return 'axios'

          return 'vendor'
        },
      },
    },
  },
})
