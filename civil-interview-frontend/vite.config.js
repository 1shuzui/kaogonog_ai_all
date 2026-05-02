import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import Components from 'unplugin-vue-components/vite'
import { AntDesignVueResolver } from 'unplugin-vue-components/resolvers'

const devApiTarget = process.env.VITE_DEV_API_TARGET || process.env.DEV_API_TARGET || 'http://127.0.0.1:8003'
const devServerPort = Number(process.env.VITE_DEV_SERVER_PORT || process.env.DEV_SERVER_PORT || 3003)

export default defineConfig({
  plugins: [
    vue(),
    Components({
      resolvers: [AntDesignVueResolver({ importStyle: 'less' })],
      dts: false
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  css: {
    preprocessorOptions: {
      less: {
        modifyVars: {
          'primary-color': '#1B5FAA',
          'border-radius-base': '8px',
          'font-size-base': '15px'
        },
        additionalData: `@import "${resolve(__dirname, 'src/styles/variables.less').replace(/\\/g, '/')}";`,
        javascriptEnabled: true
      }
    }
  },
  server: {
    port: devServerPort,
    proxy: {
      '/api': {
        target: devApiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/uploads': {
        target: devApiTarget,
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'ant-design-vue': ['ant-design-vue', '@ant-design/icons-vue'],
          'echarts': ['echarts/core', 'echarts/charts', 'echarts/components', 'echarts/renderers'],
          xlsx: ['xlsx'],
          vendor: ['vue', 'vue-router', 'pinia', 'axios']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
})
