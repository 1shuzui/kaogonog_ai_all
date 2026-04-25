import { mergeConfig } from 'vite'
import baseConfig from './vite.config.js'

export default mergeConfig(baseConfig, {
  server: {
    host: '127.0.0.1',
    port: 3003,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8051',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/uploads': {
        target: 'http://127.0.0.1:8051',
        changeOrigin: true,
      },
    },
  },
})
