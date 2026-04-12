import { defineStore } from 'pinia'
import { getUserInfo, updatePreferences, getProvinces } from '@/api/user'
import { login as loginApi, register as registerApi } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    username: localStorage.getItem('username') || '',
    email: '',
    userInfo: { id: '', name: '', avatar: '', province: 'national' },
    selectedProvince: 'national',
    provinces: [],
    preferences: {
      defaultPrepTime: 90,
      defaultAnswerTime: 180,
      enableVideo: true
    }
  }),

  getters: {
    isAuthenticated(state) {
      return !!state.token
    },
    provinceName(state) {
      const p = state.provinces.find(p => p.code === state.selectedProvince)
      return p ? p.name : '国考'
    }
  },

  actions: {
    async login(username, password) {
      const res = await loginApi(username, password)
      this.token = res.access_token
      this.username = username
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('username', username)
      return res
    },
    logout() {
      this.token = ''
      this.username = ''
      this.email = ''
      this.userInfo = { id: '', name: '', avatar: '', province: 'national' }
      localStorage.removeItem('token')
      localStorage.removeItem('username')
    },
    async register(form) {
      return registerApi(form)
    },
    async loadUserInfo() {
      this.userInfo = await getUserInfo()
      this.selectedProvince = this.userInfo.province || 'national'
    },
    async loadProvinces() {
      this.provinces = await getProvinces()
    },
    setProvince(code) {
      this.selectedProvince = code
    },
    async savePreferences(prefs) {
      Object.assign(this.preferences, prefs)
      await updatePreferences(this.preferences)
    }
  }
})
