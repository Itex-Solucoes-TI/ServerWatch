<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get, create, update, getResults } from '../api/checks'
import { list as listServers } from '../api/servers'
import { list as listRouters } from '../api/routers'
import { toast } from 'vue-sonner'

const route = useRoute()
const router = useRouter()
const check = ref(null)
const results = ref([])
const servers = ref([])
const routers = ref([])
const isNew = computed(() => route.params.id === 'new')
const selectedServer = computed(() => servers.value.find((s) => s.id === check.value?.server_id))

onMounted(async () => {
  const [srv, rtr] = await Promise.all([listServers(), listRouters()])
  servers.value = srv.data
  routers.value = rtr.data
  if (isNew.value) {
    check.value = { name: '', check_type: 'URL', target: '', interval_sec: 60, timeout_sec: 10, server_id: null, use_ssh: false, active: true }
    return
  }
  try {
    const { data } = await get(route.params.id)
    check.value = data
    const { data: res } = await getResults(route.params.id)
    results.value = res
  } catch (e) {
    toast.error('Erro ao carregar check')
  }
})

async function save() {
  try {
    if (isNew.value) {
      const { data } = await create(check.value)
      toast.success('Salvo')
      router.replace(`/checks/${data.id}`)
      check.value = data
    } else {
      await update(check.value.id, check.value)
      toast.success('Salvo')
    }
  } catch (e) {
    const d = e.response?.data?.detail
    toast.error(Array.isArray(d) ? d.map((x) => x.msg || x).join(', ') : (d || 'Erro'))
  }
}
</script>

<template>
  <div>
    <router-link to="/checks" class="text-brand-500 hover:underline mb-4 inline-block">← Health Checks</router-link>
    <div v-if="check" class="bg-white rounded-lg shadow-sm border p-6">
      <h2 class="text-xl font-bold mb-4">{{ isNew ? 'Novo Check' : check.name }}</h2>
      <form @submit.prevent="save" class="grid gap-4 max-w-md">
        <div>
          <label class="block text-sm text-gray-600 mb-1">Nome</label>
          <input v-model="check.name" class="w-full border rounded px-3 py-2" required />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Tipo</label>
          <select v-model="check.check_type" class="w-full border rounded px-3 py-2">
            <option value="URL">URL (HTTP)</option>
            <option value="PORT">Porta TCP</option>
            <option value="PING">Ping</option>
            <option value="TELNET">Telnet</option>
            <option value="DATABASE">Banco de dados</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Servidor</label>
          <select v-model="check.server_id" class="w-full border rounded px-3 py-2">
            <option :value="null">— Nenhum —</option>
            <option v-for="s in servers" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div v-if="selectedServer?.ssh_host" class="flex items-center gap-2">
          <input v-model="check.use_ssh" type="checkbox" id="use_ssh" />
          <label for="use_ssh">Executar via SSH</label>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Alvo</label>
          <input
            v-model="check.target"
            class="w-full border rounded px-3 py-2"
            :placeholder="check.check_type === 'DATABASE' ? 'mysql+pymysql://usuario:senha@host:3306/nome_banco' : 'https://... ou host:porta'"
            required
          />
          <p v-if="check.check_type === 'DATABASE'" class="mt-1 text-xs text-gray-500">
            String de conexão completa. MySQL/MariaDB: <code class="bg-gray-100 px-1">mysql+pymysql://usuario:senha@host:3306/banco</code> | PostgreSQL: <code class="bg-gray-100 px-1">postgresql://usuario:senha@host:5432/banco</code>
          </p>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">Intervalo (s)</label>
            <input v-model.number="check.interval_sec" type="number" class="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Timeout (s)</label>
            <input v-model.number="check.timeout_sec" type="number" class="w-full border rounded px-3 py-2" />
          </div>
        </div>
        <div class="flex items-center gap-2">
          <input v-model="check.active" type="checkbox" id="active" />
          <label for="active">Ativo</label>
        </div>
        <button type="submit" class="px-4 py-2 bg-brand-500 text-white rounded-lg w-fit">Salvar</button>
      </form>
      <div v-if="!isNew && results.length" class="mt-8">
        <h3 class="font-medium mb-2">Histórico</h3>
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-500">
              <th class="py-2">Data</th>
              <th class="py-2">Status</th>
              <th class="py-2">Latência</th>
              <th class="py-2">Mensagem</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in results" :key="r.id" class="border-t">
              <td class="py-1">{{ new Date(r.checked_at).toLocaleString() }}</td>
              <td :class="r.status === 'OK' ? 'text-emerald-600' : 'text-red-600'">{{ r.status }}</td>
              <td>{{ r.latency_ms != null ? r.latency_ms + 'ms' : '–' }}</td>
              <td>{{ r.message || '–' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
