<script setup>
import { ref, computed, onMounted } from 'vue'
import { list as listServers } from '../api/servers'
import { listContainers, syncServer, startContainer, stopContainer, restartContainer, removeContainer } from '../api/docker'
import { toast } from 'vue-sonner'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const servers = ref([])
const selectedServerId = ref(null)
const containers = ref([])
const loading = ref(false)
const syncing = ref(false)
const syncError = ref(null)

onMounted(async () => {
  try {
    const { data } = await listServers()
    servers.value = data
    const withDocker = data.filter((x) => x.has_docker)
    if (withDocker.length) {
      selectedServerId.value = withDocker[0].id
      loadContainers(withDocker[0].id)
    }
  } catch (e) {
    toast.error('Erro ao carregar servidores')
  }
})

const selectedServer = computed(() => servers.value.find((s) => s.id === selectedServerId.value))

const sortedContainers = computed(() => {
  const list = [...containers.value]
  return list.sort((a, b) => (a.status === 'running' ? 0 : 1) - (b.status === 'running' ? 0 : 1))
})

const runningCount = computed(() => containers.value.filter((c) => c.status === 'running').length)
const stoppedCount = computed(() => containers.value.filter((c) => c.status !== 'running').length)

async function loadContainers(serverId) {
  loading.value = true
  try {
    const { data } = await listContainers(serverId)
    containers.value = data
  } catch (e) {
    toast.error('Erro ao carregar containers')
    containers.value = []
  } finally {
    loading.value = false
  }
}

function getErrorMessage(e) {
  const d = e?.response?.data?.detail
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg
  if (typeof d === 'string') return d
  if (e?.message) return e.message
  return 'Erro ao sincronizar'
}

async function sync() {
  if (!selectedServerId.value) return
  syncing.value = true
  syncError.value = null
  try {
    await syncServer(selectedServerId.value)
    await loadContainers(selectedServerId.value)
    toast.success('Sincronizado')
  } catch (e) {
    const msg = getErrorMessage(e)
    syncError.value = msg
    toast.error(msg)
  } finally {
    syncing.value = false
  }
}

async function start(c) {
  try {
    await startContainer(selectedServerId.value, c.container_id)
    loadContainers(selectedServerId.value)
    toast.success('Container iniciado')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function stop(c) {
  try {
    await stopContainer(selectedServerId.value, c.container_id)
    loadContainers(selectedServerId.value)
    toast.success('Container parado')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function restart(c) {
  try {
    await restartContainer(selectedServerId.value, c.container_id)
    loadContainers(selectedServerId.value)
    toast.success('Container reiniciado')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function remove(c) {
  const msg = c.status === 'running'
    ? `Remover "${c.name}"? Ele será parado e removido.`
    : `Remover o container "${c.name}"?`
  if (!confirm(msg)) return
  try {
    await removeContainer(selectedServerId.value, c.container_id, c.status === 'running')
    loadContainers(selectedServerId.value)
    toast.success('Container removido')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}
</script>

<template>
  <div>
    <h2 class="text-xl font-bold text-brand-800 mb-6">Docker</h2>
    <div class="flex gap-4 mb-6">
      <select
        v-model="selectedServerId"
        @change="selectedServerId && loadContainers(selectedServerId)"
        class="border rounded px-4 py-2"
      >
        <option v-for="s in servers.filter((x) => x.has_docker)" :key="s.id" :value="s.id">
          {{ s.name }}
        </option>
        <option v-if="!servers.filter((x) => x.has_docker).length" disabled>Nenhum servidor com Docker</option>
      </select>
      <button
        v-if="auth.isOperator && selectedServerId"
        @click="sync"
        :disabled="loading || syncing"
        class="px-4 py-2 bg-brand-500 text-white rounded-lg disabled:opacity-50"
      >
        {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
      </button>
    </div>
    <div v-if="syncError" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
      {{ syncError }}
    </div>
    <p class="mb-2 text-sm text-gray-600">Sincronização automática a cada 30s.</p>
    <details open class="mb-6 p-4 bg-brand-50 rounded-lg border border-brand-200">
      <summary class="cursor-pointer font-medium text-brand-800">Como configurar Docker remoto</summary>
      <div class="mt-3 text-sm text-gray-700 space-y-2">
        <p>No servidor remoto que deseja monitorar:</p>
        <ol class="list-decimal ml-4 space-y-1">
          <li>Edite <code class="bg-white px-1 rounded">/etc/docker/daemon.json</code> e adicione <code class="bg-white px-1 rounded">"hosts"</code> (com vírgula se já tiver outras opções):</li>
        </ol>
        <pre class="bg-white p-3 rounded text-xs overflow-x-auto">{
  "hosts": ["tcp://0.0.0.0:2375", "unix:///var/run/docker.sock"]
}</pre>
        <ol class="list-decimal ml-4 space-y-1" start="2">
          <li>Crie override do systemd (obrigatório): <code class="bg-white px-1 rounded text-xs">sudo mkdir -p /etc/systemd/system/docker.service.d</code>. Arquivo <code class="bg-white px-1 rounded text-xs">override.conf</code>:
            <pre class="bg-white p-2 rounded text-xs mt-1">[Service]
ExecStart=
ExecStart=/usr/bin/dockerd</pre></li>
          <li><code class="bg-white px-1 rounded">sudo systemctl daemon-reload && sudo systemctl restart docker</code></li>
          <li>Abra a porta 2375 no firewall.</li>
          <li><strong>Segurança:</strong> Sem TLS, qualquer um na rede pode acessar. Use em redes internas.</li>
        </ol>
        <p class="pt-2">Na interface: <code class="bg-white px-1 rounded">docker_host = tcp://IP_DO_SERVIDOR:2375</code> ou use <strong>Docker via SSH</strong> (host, porta 22, usuário, senha) — sem expor portas.</p>
        <p class="pt-2 text-amber-700"><strong>Permissão:</strong> Sincronizar e controlar containers requer perfil <strong>Operador</strong> ou <strong>Admin</strong>. Configure em <strong>Usuários</strong> → editar usuário → Função.</p>
      </div>
    </details>
    <div v-if="loading" class="text-gray-500">Carregando...</div>
    <div v-else>
      <p v-if="containers.length" class="mb-4 text-sm text-gray-600">
        {{ runningCount }} em execução · {{ stoppedCount }} parados
      </p>
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="c in sortedContainers"
          :key="c.container_id"
          class="bg-white rounded-lg shadow-sm border p-4"
          :class="c.status !== 'running' ? 'opacity-75 border-gray-200' : 'border-emerald-200'"
        >
          <div class="flex items-start justify-between gap-2">
            <p class="font-medium truncate flex-1">{{ c.name }}</p>
            <span
              :class="c.status === 'running'
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-gray-100 text-gray-600'"
              class="shrink-0 text-xs px-2 py-0.5 rounded"
            >
              {{ c.status === 'running' ? 'Rodando' : 'Parado' }}
            </span>
          </div>
          <p class="text-sm text-gray-500 truncate mt-1">{{ c.image }}</p>
          <div v-if="auth.isOperator" class="mt-3 flex flex-wrap gap-2">
            <button v-if="c.status !== 'running'" @click="start(c)" class="text-sm px-2 py-1 bg-emerald-500 text-white rounded hover:bg-emerald-600">Iniciar</button>
            <button v-if="c.status === 'running'" @click="stop(c)" class="text-sm px-2 py-1 bg-amber-500 text-white rounded hover:bg-amber-600">Parar</button>
            <button v-if="c.status === 'running'" @click="restart(c)" class="text-sm px-2 py-1 bg-brand-500 text-white rounded hover:bg-brand-600">Reiniciar</button>
            <button v-if="auth.isAdmin" @click="remove(c)" class="text-sm px-2 py-1 bg-red-500 text-white rounded hover:bg-red-600">Excluir</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
