/**
 * 这个工具文件处理 `wechatLogin` 这类跨页面规则；集中维护可以避免 PC、小程序或不同页面各自写一份判断。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
export function getWechatLoginCode() {
  return new Promise((resolve, reject) => {
    uni.login({
      provider: 'weixin',
      success(res) {
        if (res.code) resolve(res.code)
        else reject(new Error('微信登录未返回 code'))
      },
      fail(error) {
        reject(new Error(error?.errMsg || '微信登录失败'))
      }
    })
  })
}
