<script setup>
import { onMounted, onUnmounted, ref, provide, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import TerminalPip from '../TerminalPip.vue'
import { connectWebSocket, closeWebSocket } from '../../api/websocket'
import { useAuthStore } from '../../stores/auth'
import { status as licenseStatus } from '../../api/license'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const checkInterval = ref(null)
const sidebarOpen = ref(false)

provide('sidebarOpen', sidebarOpen)

watch(() => route.path, () => { sidebarOpen.value = false })
watch(sidebarOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

function closeSidebar() {
  sidebarOpen.value = false
}

async function checkLicense() {
  try {
    const { data } = await licenseStatus()
    if (data.needs_license) {
      auth.needsLicense = true
      router.push('/login')
    }
  } catch {
    // 401 = sessão inválida, router trata
  }
}

onMounted(() => {
  connectWebSocket()
  checkLicense()
  checkInterval.value = setInterval(checkLicense, 60 * 60 * 1000) // a cada hora
})
onUnmounted(() => {
  closeWebSocket()
  if (checkInterval.value) clearInterval(checkInterval.value)
})
</script>

<template>
  <div class="flex min-h-screen bg-gray-50">
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 bg-black/40 z-40 lg:hidden"
      @click="closeSidebar"
      aria-hidden="true"
    />
    <AppSidebar />
    <div class="flex-1 flex flex-col min-w-0">
      <AppHeader />
      <main class="flex-1 p-4 sm:p-6 overflow-auto bg-gray-50">
        <router-view :key="auth.companyId" />
      </main>
    </div>
    <TerminalPip />
  </div>
</template>
