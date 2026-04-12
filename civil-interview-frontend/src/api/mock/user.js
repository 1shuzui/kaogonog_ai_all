import { mockDelay } from './index'
import { PROVINCES } from '@/utils/constants'

export async function getMockUserInfo() {
  await mockDelay(300)
  return {
    id: 'user_001',
    name: '考生A',
    avatar: '',
    province: 'national'
  }
}

export async function getMockProvinces() {
  await mockDelay(200)
  return PROVINCES
}
