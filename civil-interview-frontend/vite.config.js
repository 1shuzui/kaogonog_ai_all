/**
 * 这个构建配置文件告诉 Vite 如何处理 Vue、自动导入和开发代理；本地调试和生产打包都依赖它。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
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
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'ant-design-vue': ['ant-design-vue', '@ant-design/icons-vue'],
          'echarts': ['echarts/core', 'echarts/charts', 'echarts/components', 'echarts/renderers'],
          vendor: ['vue', 'vue-router', 'pinia', 'axios']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
})
