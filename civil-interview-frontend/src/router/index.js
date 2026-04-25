import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useBillingStore } from '@/stores/billing'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Auth/LoginPage.vue'),
    meta: { title: 'Login', layout: 'blank', requiresAuth: false }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home/HomePage.vue'),
    meta: { title: 'Home', layout: 'default' }
  },
  {
    path: '/pricing',
    name: 'Pricing',
    component: () => import('@/views/Billing/PricingPage.vue'),
    meta: { title: '套餐中心', layout: 'default', requiresAuth: false }
  },
  {
    path: '/exam/prepare',
    name: 'ExamPrepare',
    component: () => import('@/views/Exam/ExamPrepare.vue'),
    meta: { title: '模拟面试准备', layout: 'simple', requiresPayment: true, paywallSource: '完整模拟面试' }
  },
  {
    path: '/exam/room',
    name: 'ExamRoom',
    component: () => import('@/views/Exam/ExamRoom.vue'),
    meta: { title: 'Exam Room', layout: 'fullscreen' }
  },
  {
    path: '/exam/complete/:examId',
    name: 'ExamComplete',
    component: () => import('@/views/Exam/ExamComplete.vue'),
    meta: { title: 'Exam Complete', layout: 'simple' }
  },
  {
    path: '/result/:examId',
    name: 'Result',
    component: () => import('@/views/Result/ResultPage.vue'),
    meta: { title: 'Result', layout: 'simple' }
  },
  {
    path: '/bank',
    name: 'BankList',
    component: () => import('@/views/QuestionBank/BankList.vue'),
    meta: { title: 'Question Bank', layout: 'default', requiresAdmin: true }
  },
  {
    path: '/bank/import',
    name: 'BankImport',
    component: () => import('@/views/QuestionBank/BankImport.vue'),
    meta: { title: 'Import Questions', layout: 'default', requiresAdmin: true }
  },
  {
    path: '/bank/edit/:id?',
    name: 'BankEditor',
    component: () => import('@/views/QuestionBank/BankEditor.vue'),
    meta: { title: 'Question Editor', layout: 'default', requiresAdmin: true }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/History/HistoryPage.vue'),
    meta: { title: 'History', layout: 'default' }
  },
  {
    path: '/favorites',
    name: 'Favorites',
    component: () => import('@/views/Favorites/FavoritesPage.vue'),
    meta: { title: 'Favorites', layout: 'default' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile/ProfilePage.vue'),
    meta: { title: 'Profile', layout: 'default' }
  },
  {
    path: '/targeted',
    name: 'Targeted',
    component: () => import('@/views/Targeted/TargetedPage.vue'),
    meta: { title: '定向备考', layout: 'default', requiresPayment: true, paywallSource: '定向备考' }
  },
  {
    path: '/targeted/focus',
    name: 'TargetedFocus',
    component: () => import('@/views/Targeted/FocusAnalysisPage.vue'),
    meta: { title: '重点分析', layout: 'simple', requiresPayment: true, paywallSource: '定向备考' }
  },
  {
    path: '/training',
    name: 'Training',
    component: () => import('@/views/Training/TrainingPage.vue'),
    meta: { title: '专项训练', layout: 'default', requiresPayment: true, paywallSource: '专项训练' }
  },
  {
    path: '/training/:dimension',
    name: 'DimensionTraining',
    component: () => import('@/views/Training/DimensionTraining.vue'),
    meta: { title: '维度训练', layout: 'simple', requiresPayment: true, paywallSource: '专项训练' }
  },
  {
    path: '/profile/account',
    name: 'Account',
    component: () => import('@/views/Profile/AccountPage.vue'),
    meta: { title: 'Account', layout: 'simple' }
  },
  {
    path: '/profile/analysis',
    name: 'Analysis',
    component: () => import('@/views/Profile/AnalysisPage.vue'),
    meta: { title: 'Analysis', layout: 'simple' }
  },
  {
    path: '/profile/orders',
    name: 'BillingOrders',
    component: () => import('@/views/Billing/BillingOrdersPage.vue'),
    meta: { title: '订单记录', layout: 'simple' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: 'Not Found', layout: 'blank' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || 'Civil Interview'} - Civil Interview AI`

  const userStore = useUserStore()
  const billingStore = useBillingStore()
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !userStore.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.path === '/login' && userStore.isAuthenticated) {
    return { path: '/' }
  }

  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    return { path: '/' }
  }

  billingStore.syncPlanState()
  if (userStore.isAdmin) {
    return true
  }

  if (!billingStore.canAccessRoute(to)) {
    const source = String(to.meta.paywallSource || to.meta.title || '付费功能')
    billingStore.openPaywall(to.fullPath, source)
    return { path: '/' }
  }

  return true
})

export default router
