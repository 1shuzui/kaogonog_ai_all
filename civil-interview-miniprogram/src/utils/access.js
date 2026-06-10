/**
 * 小程序访问控制工具只用于决定按钮、入口和付费提示的显示，真正能否调用接口仍以后端鉴权为准。
 *
 * 审核要求用户先浏览功能再主动登录，所以这里不能在页面加载时索取手机号或头像昵称；只在用户点击训练、支付、个人数据等动作时参与拦截。
 *
 * @param 无；导出函数接收 userStore、billingStore、subscriptionStore 等调用方已有状态。
 * @return 导出登录、管理员和付费入口判断函数，供页面按钮与菜单复用。
 * @raises 参数异常通常返回兜底值；需要阻断流程的错误交由调用方处理。
 */
export function hasPremiumAccess(userStore, billingStore, subscriptionStore) {
  return !!(
    userStore?.isAdmin
    || billingStore?.isPaid
    || subscriptionStore?.hasPremiumAccess
    || userStore?.userInfo?.billing?.isPaid === true
    || userStore?.userInfo?.permissions?.canAccessPremiumModules === true
  )
}
