/**
 * 这个 Vite 代理配置固定使用 3003 端口；它用于本地自动化检查，避免和常规开发服务抢端口。
 *
 * @param 无；Vite 在启动时读取该配置对象。
 * @return 返回合并后的开发服务器配置，保持基础构建配置不分叉。
 * @raises Error 当基础 Vite 配置不可导入或端口被占用且 strictPort 生效时由工具链抛出。
 */
import { mergeConfig } from 'vite'
import baseConfig from './vite.config.js'

export default mergeConfig(baseConfig, {
  server: {
    host: '127.0.0.1',
    port: 3003,
    strictPort: true,
  },
})
