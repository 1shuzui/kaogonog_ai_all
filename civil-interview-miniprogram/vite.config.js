/**
 * 这个构建配置文件告诉 Vite 如何处理 Vue、自动导入和开发代理；本地调试和生产打包都依赖它。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { defineConfig } from 'vite'
import uniModule from '@dcloudio/vite-plugin-uni'

const uni = uniModule.default || uniModule

export default defineConfig({
  plugins: [uni()]
})
