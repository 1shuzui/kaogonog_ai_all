/**
 * PC 端 Vue 应用启动入口，负责创建应用实例、挂载 Pinia、Vue Router、Ant Design 样式和全局运行时错误记录。
 *
 * 这里保持很薄，是为了让业务页面、接口请求和状态仓库各自独立；入口只做“把应用装起来”。
 * 全局错误处理会把 Vue 运行时异常交给 logger，避免页面静默白屏后完全没有排查线索。
 *
 * @param 无；浏览器加载打包入口后自动执行。
 * @return 挂载后的 Vue 应用实例由 Vue 内部持有，本文件不导出业务对象。
 * @raises Error: 插件注册、路由初始化或根组件加载失败时由构建产物/浏览器运行时抛出。
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
