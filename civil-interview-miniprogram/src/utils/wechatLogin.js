/**
 * 微信登录工具只封装用户主动触发后的 code 获取，避免小程序打开首页时就索取登录、手机号、头像或昵称。
 *
 * 支付、试用、开始练习等动作需要账号时由页面先走登录拦截，再调用这里获取临时 code；这样更符合微信审核的“先浏览后登录”要求。
 *
 * @param 无；导出函数在用户动作触发后调用 uni.login。
 * @return 导出微信登录 code 获取函数，供登录页和虚拟支付前置流程复用。
 * @raises 参数异常通常返回兜底值；需要阻断流程的错误交由调用方处理。
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
