// Native custom-tab-bar sits outside the page's root-portal layer. A sheet holds
// only its owning page; never keep a tabBar instance across page transitions.
export function holdSheetNavigation(page) {
  if (!page) return () => {}
  page.__learnerSheetCount = (page.__learnerSheetCount || 0) + 1
  page.getTabBar?.()?.setSheetOpen?.(true)
  let released = false
  return () => {
    if (released) return
    released = true
    page.__learnerSheetCount = Math.max(0, (page.__learnerSheetCount || 0) - 1)
    page.getTabBar?.()?.setSheetOpen?.(page.__learnerSheetCount > 0)
  }
}
