<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

function selectCompany(company) {
  auth.setCompany(company.id, company.role)
  router.push('/dashboard')
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-brand-100 flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-xl p-8 w-full max-w-md">
      <h1 class="text-xl font-bold text-brand-800 mb-2">Selecione a empresa</h1>
      <p class="text-gray-600 mb-6">{{ auth.user?.name }}</p>
      <div class="space-y-2">
        <button
          v-for="c in auth.companies"
          :key="c.id"
          @click="selectCompany(c)"
          class="w-full py-3 px-4 text-left rounded-lg border border-gray-200 hover:border-brand-500 hover:bg-brand-50 transition"
        >
          {{ c.name }}
          <span class="text-gray-400 text-sm">({{ c.slug }})</span>
        </button>
      </div>
      <button
        @click="logout"
        class="mt-6 w-full py-2 text-gray-600 hover:text-gray-800"
      >
        Sair
      </button>
    </div>
  </div>
</template>
