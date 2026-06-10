/**
 * PC 访问控制工具只决定页面入口是否展示或是否弹出付费墙，不能替代后端鉴权。
 *
 * 管理员、套餐权益和试用状态可能来自不同接口快照，因此这里做宽松聚合；真正能否读取题库、生成题目或调整权益仍以后端返回为准。
 *
 * @param 无；导出函数接收 userStore、billingStore 等调用方已有状态。
 * @return 导出登录、管理员和付费入口判断函数，供路由守卫、页面按钮和弹窗复用。
 * @raises 参数异常通常返回兜底值；需要阻断流程的错误交由调用方处理。
 */
export function hasPremiumAccess(userStore, billingStore) {
  return !!(
    userStore?.isAdmin
    || billingStore?.isPaid
    || userStore?.userInfo?.billing?.isPaid === true
    || userStore?.userInfo?.permissions?.canAccessPremiumModules === true
  )
}
