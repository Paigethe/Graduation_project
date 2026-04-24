import { defineStore } from 'pinia'

import { api } from '../api/client'
import type { UserMe } from '../api/types'

type TokenResponse = { access: string; refresh: string }

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem('bs001_access_token') || '',
    refreshToken: localStorage.getItem('bs001_refresh_token') || '',
    me: null as UserMe | null,
    loading: false,
  }),
  actions: {
    async login(username: string, password: string) {
      this.loading = true
      try {
        const { data } = await api.post<TokenResponse>('/api/auth/token/', { username, password })
        this.accessToken = data.access
        this.refreshToken = data.refresh
        localStorage.setItem('bs001_access_token', data.access)
        localStorage.setItem('bs001_refresh_token', data.refresh)
        await this.fetchMe()
      } finally {
        this.loading = false
      }
    },
    async fetchMe() {
      const { data } = await api.get<UserMe>('/api/auth/me/')
      this.me = data
    },
    logout() {
      this.accessToken = ''
      this.refreshToken = ''
      this.me = null
      localStorage.removeItem('bs001_access_token')
      localStorage.removeItem('bs001_refresh_token')
    },
  },
})

