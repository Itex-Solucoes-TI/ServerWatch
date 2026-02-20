<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { list as listServers } from '../api/servers'
import { useTerminalStore } from '../stores/terminal'

const route = useRoute()
const router = useRouter()
const store = useTerminalStore()
const servers = ref([])
const selectedId = ref(null)

const sshServers = computed(() => servers.value.filter((s) => s.ssh_host))

async function loadServers() {
  const { data } = await listServers()
  servers.value = data
  if (!selectedId.value && route.params.serverId) {
    selectedId.value = parseInt(route.params.serverId, 10)
  }
  if (!selectedId.value && sshServers.value.length) {
    selectedId.value = sshServers.value[0].id
  }
}

function connect() {
  if (!selectedId.value) return
  const srv = sshServers.value.find((s) => s.id === selectedId.value)
  store.connectToNew(selectedId.value, srv?.name)
  router.replace({ path: `/terminal/${selectedId.value}` }).catch(() => {})
}

watch(selectedId, (id) => {
  if (id && sshServers.value.some((s) => s.id === id)) {
    router.replace({ path: `/terminal/${id}` }).catch(() => {})
  }
})

watch(
  () => route.params.serverId,
  (id) => {
    const n = parseInt(id, 10)
    if (n && n !== selectedId.value) selectedId.value = n
  }
)

onMounted(loadServers)
</script>

<template>
  <div class="flex flex-col">
    <div class="flex items-center gap-4 mb-6">
      <router-link to="/servers" class="text-brand-500 hover:underline">← Servidores</router-link>
      <select
        v-model="selectedId"
        class="border rounded px-3 py-2 max-w-xs"
        :disabled="!sshServers.length"
      >
        <option :value="null">— Selecione um servidor —</option>
        <option v-for="s in sshServers" :key="s.id" :value="s.id">{{ s.name }} ({{ s.ssh_host }})</option>
      </select>
      <button
        v-if="selectedId"
        @click="connect"
        :disabled="store.sessions.some((s) => s.status === 'connecting')"
        class="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 disabled:opacity-50"
      >
        {{ store.sessions.some((s) => s.status === 'connecting') ? 'Conectando...' : 'Conectar' }}
      </button>
      <span
        v-if="store.activeSession?.status === 'error'"
        class="text-sm text-red-600"
      >
        {{ store.activeSession?.errorMsg }}
      </span>
    </div>
    <div
      v-if="!sshServers.length"
      class="flex items-center justify-center py-16 bg-gray-100 rounded-lg text-gray-500"
    >
      Nenhum servidor com SSH configurado
    </div>
    <div
      v-else-if="!store.hasConnected"
      class="flex items-center justify-center py-16 bg-gray-50 rounded-lg border border-dashed border-gray-300 text-gray-500"
    >
      Selecione um servidor e clique em Conectar
    </div>
    <p v-else class="text-sm text-gray-500 mb-2">
      Use os controles do header para minimizar, maximizar ou fechar.
    </p>
  </div>
</template>
