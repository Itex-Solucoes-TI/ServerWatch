<script setup>
import { onMounted, onUnmounted } from 'vue'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import TerminalPip from '../TerminalPip.vue'
import { connectWebSocket, closeWebSocket } from '../../api/websocket'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()

onMounted(connectWebSocket)
onUnmounted(closeWebSocket)
</script>

<template>
  <div class="flex min-h-screen bg-gray-50">
    <AppSidebar />
    <div class="flex-1 flex flex-col min-w-0">
      <AppHeader />
      <main class="flex-1 p-6 overflow-auto bg-gray-50">
        <router-view :key="auth.companyId" />
      </main>
    </div>
    <TerminalPip />
  </div>
</template>
