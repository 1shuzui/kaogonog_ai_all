import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Auth/LoginPage.vue'),
    meta: { title: '登录', layout: 'blank', requiresAuth: false }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home/HomePage.vue'),
    meta: { title: '首页', layout: 'default' }
  },
  {
    path: '/exam/prepare',
    name: 'ExamPrepare',
    component: () => import('@/views/Exam/ExamPrepare.vue'),
    meta: { title: '设备检测', layout: 'simple' }
  },
  {
    path: '/exam/room',
    name: 'ExamRoom',
    component: () => import('@/views/Exam/ExamRoom.vue'),
    meta: { title: '考场', layout: 'fullscreen' }
  },
  {
    path: '/exam/complete/:examId',
    name: 'ExamComplete',
    component: () => import('@/views/Exam/ExamComplete.vue'),
    meta: { title: '答题完成', layout: 'simple' }
  },
  {
    path: '/result/:examId',
    name: 'Result',
    component: () => import('@/views/Result/ResultPage.vue'),
    meta: { title: '测评结果', layout: 'simple' }
  },
  {
    path: '/bank',
    name: 'BankList',
    component: () => import('@/views/QuestionBank/BankList.vue'),
    meta: { title: '题库管理', layout: 'default' }
  },
  {
    path: '/bank/import',
    name: 'BankImport',
    component: () => import('@/views/QuestionBank/BankImport.vue'),
    meta: { title: '批量导入', layout: 'default' }
  },
  {
    path: '/bank/edit/:id?',
    name: 'BankEditor',
    component: () => import('@/views/QuestionBank/BankEditor.vue'),
    meta: { title: '编辑题目', layout: 'default' }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/History/HistoryPage.vue'),
    meta: { title: '历史记录', layout: 'default' }
  },
  {
    path: '/favorites',
    name: 'Favorites',
    component: () => import('@/views/Favorites/FavoritesPage.vue'),
    meta: { title: '错题本', layout: 'default' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile/ProfilePage.vue'),
    meta: { title: '个人中心', layout: 'default' }
  },
  {
    path: '/targeted',
    name: 'Targeted',
    component: () => import('@/views/Targeted/TargetedPage.vue'),
    meta: { title: '定向备面', layout: 'default' }
  },
  {
    path: '/targeted/focus',
    name: 'TargetedFocus',
    component: () => import('@/views/Targeted/FocusAnalysisPage.vue'),
    meta: { title: '面试重点分析', layout: 'simple' }
  },
  {
    path: '/training',
    name: 'Training',
    component: () => import('@/views/Training/TrainingPage.vue'),
    meta: { title: '专项训练', layout: 'default' }
  },
  {
    path: '/training/:dimension',
    name: 'DimensionTraining',
    component: () => import('@/views/Training/DimensionTraining.vue'),
    meta: { title: '维度训练', layout: 'simple' }
  },
  {
    path: '/profile/account',
    name: 'Account',
    component: () => import('@/views/Profile/AccountPage.vue'),
    meta: { title: '账号管理', layout: 'simple' }
  },
  {
    path: '/profile/analysis',
    name: 'Analysis',
    component: () => import('@/views/Profile/AnalysisPage.vue'),
    meta: { title: '个人分析', layout: 'simple' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面未找到', layout: 'blank' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || ''} - 公考面试AI智能测评`

  const userStore = useUserStore()
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !userStore.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && userStore.isAuthenticated) {
    return { path: '/' }
  }
})

export default router
