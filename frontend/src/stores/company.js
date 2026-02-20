import { defineStore } from 'pinia'
import { useAuthStore } from './auth'

export const useCompanyStore = defineStore('company', {
  state: () => ({ companyId: null }),
  getters: {
    companyId: (s) => s.companyId ?? useAuthStore().companyId,
  },
  actions: {
    setCompany(id) {
      this.companyId = id
      useAuthStore().setCompany(id)
    },
  },
})
