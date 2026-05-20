export function hasPremiumAccess(userStore, billingStore, subscriptionStore) {
  return !!(
    userStore?.isAdmin
    || billingStore?.isPaid
    || subscriptionStore?.hasPremiumAccess
    || userStore?.userInfo?.billing?.isPaid === true
    || userStore?.userInfo?.permissions?.canAccessPremiumModules === true
  )
}
