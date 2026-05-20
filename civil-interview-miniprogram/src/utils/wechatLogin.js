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
