<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import CompanySwitcher from '../ui/CompanySwitcher.vue'
import { LogOut } from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <header class="bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between shadow-sm">
    <h1 class="text-xl font-semibold text-brand-800">ServerWatch</h1>
    <div class="flex items-center gap-4">
      <CompanySwitcher />
      <span class="text-gray-500 text-sm">{{ auth.user?.email }}</span>
      <button
        @click="logout"
        class="p-2 rounded-lg hover:bg-gray-100 text-gray-600"
        title="Sair"
      >
        <LogOut class="w-5 h-5" />
      </button>
    </div>
  </header>
</template>
