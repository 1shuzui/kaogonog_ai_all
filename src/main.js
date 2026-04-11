import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'
import router from './router'
import './styles/global.less'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// 全局错误处理
app.config.errorHandler = (err, instance, info) => {
  console.error(`[Vue Error] ${info}:`, err)
}

app.mount('#app')
