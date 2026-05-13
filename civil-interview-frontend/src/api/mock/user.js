import { mockDelay } from './index'
import { PROVINCES } from '@/utils/constants'

export async function getMockUserInfo() {
  await mockDelay(300)
  return {
    id: 'user_001',
    name: '考生A',
    avatar: '',
    province: 'national',
    role: 'user',
    isAdmin: false,
    permissions: {
      canManageQuestionBank: false,
      canAccessPremiumModules: false
    },
    billing: {
      planType: 'trial',
      remainingSeconds: 0,
      monthlyExpireAt: 0,
      activatedAt: 0,
      orderHistory: []
    },
    terms: {
      hasAgreed: false,
      agreedVersion: '',
      latestVersion: '2026-05-12',
      updatedAt: '2026-05-12',
      effectiveAt: '2026-05-12',
      agreedAt: '',
      needsUpdate: true
    }
  }
}

export async function getMockProvinces() {
  await mockDelay(200)
  return PROVINCES
}
