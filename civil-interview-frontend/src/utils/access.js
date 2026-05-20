export function hasPremiumAccess(userStore, billingStore) {
  return !!(
    userStore?.isAdmin
    || billingStore?.isPaid
    || userStore?.userInfo?.billing?.isPaid === true
    || userStore?.userInfo?.permissions?.canAccessPremiumModules === true
  )
}
