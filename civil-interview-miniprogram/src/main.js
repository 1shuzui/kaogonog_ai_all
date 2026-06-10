/**
 * 小程序端 Vue/uni-app 启动入口，负责创建 SSR 应用实例并挂载 Pinia 状态仓库。
 *
 * 小程序页面生命周期分散在各 page 内，这里只做最小装配，避免首屏启动时触发登录、请求个人数据或支付能力。
 * 审核要求用户先浏览后登录，因此任何需要账号的动作都应在页面或 navigation 工具里主动拦截。
 *
 * @param 无；uni-app 编译后的运行时会调用 `createApp`。
 * @return 返回 `{ app }` 给 uni-app 挂载。
 * @raises Error: 根组件、Pinia 或运行时依赖加载失败时由 uni-app/Vue 抛出。
 */
import { createSSRApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

export function createApp() {
  const app = createSSRApp(App)
  app.use(createPinia())
  return {
    app
  }
}
