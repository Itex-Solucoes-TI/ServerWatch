<script setup>
import { inject } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import CompanySwitcher from '../ui/CompanySwitcher.vue'
import { LogOut, Menu } from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()
const sidebarOpenRef = inject('sidebarOpen')

function openMenu() {
  if (sidebarOpenRef && typeof sidebarOpenRef === 'object' && 'value' in sidebarOpenRef) {
    sidebarOpenRef.value = true
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <header class="bg-white border-b border-gray-100 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-2 shadow-sm">
    <div class="flex items-center gap-2 min-w-0">
      <button
        @click="openMenu"
        class="lg:hidden p-2 -ml-2 rounded-lg hover:bg-gray-100 text-gray-600 shrink-0"
        title="Menu"
        aria-label="Abrir menu"
      >
        <Menu class="w-5 h-5" />
      </button>
      <h1 class="text-lg sm:text-xl font-semibold text-brand-800 truncate">ServerWatch</h1>
    </div>
    <div class="flex items-center gap-2 sm:gap-4 shrink-0">
      <CompanySwitcher />
      <span class="hidden md:inline text-gray-500 text-sm truncate max-w-[120px]">{{ auth.user?.email }}</span>
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
