/**
 * PC 端路由表和访问守卫，集中维护普通页面、考场页面、题库后台、管理员工作台和登录页的入口关系。
 *
 * 路由 meta 是页面权限的第一层提示，真正权限仍由后端接口校验。这里负责用户体验上的拦截：
 * 未登录跳登录页，普通用户访问 `/admin` 回首页，考试/支付/题库页面按既有 store 做必要的状态恢复。
 * 新增页面时优先在这里补齐 title、layout、requiresAuth 和 requiresAdmin，避免页面自己写跳转规则。
 *
 * @param 无；Vue Router 在浏览器导航时传入 to/from 路由对象。
 * @return 导出 router 实例供 `main.js` 挂载。
 * @raises Error: 动态组件加载失败或守卫中 store 初始化异常时由 Vue Router 抛出。
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useBillingStore } from '@/stores/billing'
import { useExamStore } from '@/stores/exam'

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
    path: '/jiangsu-jobs/:category?',
    name: 'JiangsuJobs',
    component: () => import('@/views/JiangsuJobs/JiangsuJobPage.vue'),
    meta: { title: '江苏事业单位分岗刷题', layout: 'default' }
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
    meta: { title: '全真模拟准备', layout: 'simple', requiresPayment: true, paywallSource: '完整全真模拟' }
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
    meta: { title: 'Question Bank', layout: 'default' }
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
    path: '/admin',
    name: 'AdminDashboard',
    component: () => import('@/views/Admin/AdminDashboard.vue'),
    meta: { title: '管理员工作台', layout: 'simple', requiresAdmin: true }
  },
  {
    path: '/admin/entitlements',
    name: 'EntitlementAdmin',
    component: () => import('@/views/Admin/EntitlementAdminPage.vue'),
    meta: { title: '用户权益管理', layout: 'simple', requiresAdmin: true }
  },
  {
    path: '/admin/entitlement-adjustments',
    name: 'EntitlementAdjustments',
    component: () => import('@/views/Admin/EntitlementAdjustmentsPage.vue'),
    meta: { title: '权益调整流水', layout: 'simple', requiresAdmin: true }
  },
  {
    path: '/admin/refunds',
    name: 'RefundAdmin',
    component: () => import('@/views/Billing/RefundAdminPage.vue'),
    meta: { title: '余额与退款', layout: 'simple', requiresAdmin: true }
  },
  {
    path: '/admin/invites',
    name: 'InviteAdmin',
    component: () => import('@/views/Admin/InviteAdminPage.vue'),
    meta: { title: '邀请码管理', layout: 'simple', requiresAdmin: true }
  },
  {
    path: '/admin/targeted',
    name: 'TargetedAdmin',
    component: () => import('@/views/Targeted/TargetedAdminPage.vue'),
    meta: { title: '定向入口管理', layout: 'simple', requiresAdmin: true }
  },
  {
    path: '/support',
    name: 'SupportDesk',
    component: () => import('@/views/Support/SupportDeskPage.vue'),
    meta: { title: '客服反馈中心', layout: 'simple' }
  },
  {
    path: '/legal',
    name: 'LegalDocuments',
    component: () => import('@/views/Legal/LegalDocumentsPage.vue'),
    meta: { title: '用户协议与隐私协议', layout: 'simple', requiresAuth: false }
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
  const examStore = useExamStore()
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !userStore.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.path === '/login' && userStore.isAuthenticated) {
    return { path: '/' }
  }

  if (to.name === 'ExamRoom' && (!examStore.examId || !examStore.currentQuestion)) {
    return { path: '/exam/prepare' }
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
