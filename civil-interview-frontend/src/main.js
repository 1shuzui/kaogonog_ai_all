/**
 * 这个入口文件创建前端应用并挂载全局插件；路由、状态仓库和全局样式都从这里接入。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'
import router from './router'
import './styles/global.less'
import { logger } from './utils/logger'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// 全局错误处理
app.config.errorHandler = (err, instance, info) => {
  logger.error('Vue runtime error', {
    event: 'vue.error',
    info,
    error: err
  })
}

app.mount('#app')
