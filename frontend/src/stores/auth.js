import { defineStore } from 'pinia'
import { login as apiLogin } from '../api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: null,
    refreshToken: null,
    user: null,
    companies: [],
    companyId: null,
    currentRole: null, // role do usuário na empresa selecionada
  }),
  persist: true,
  getters: {
    isLoggedIn: (s) => !!s.token,
    currentCompany: (s) => s.companies.find((c) => c.id === s.companyId),
    isAdmin: (s) => s.user?.is_superadmin || s.currentRole === 'ADMIN',
    isOperator: (s) => s.user?.is_superadmin || ['ADMIN', 'OPERATOR'].includes(s.currentRole),
    isViewer: (s) => !!s.currentRole || s.user?.is_superadmin,
  },
  actions: {
    async login(email, password) {
      const { data } = await apiLogin(email, password)
      this.token = data.access_token
      this.refreshToken = data.refresh_token
      this.user = data.user
      this.companies = data.companies
      this.companyId = data.companies[0]?.id ?? null
      this.currentRole = data.companies[0]?.role ?? null
    },
    setCompany(id, role) {
      this.companyId = id
      // role pode vir do switch ou da lista de companies
      this.currentRole = role ?? this.companies.find((c) => c.id === id)?.role ?? null
    },
    updateCompany(id, data) {
      const c = this.companies.find((x) => x.id === id)
      if (c) {
        if (data.name != null) c.name = data.name
        if (data.slug != null) c.slug = data.slug
      }
    },
    logout() {
      this.token = null
      this.refreshToken = null
      this.user = null
      this.companies = []
      this.companyId = null
      this.currentRole = null
    },
  },
})
