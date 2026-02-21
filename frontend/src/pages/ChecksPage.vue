<script setup>
import { ref, onMounted, computed } from 'vue'
import { list, create, update, remove, runNow, getResults } from '../api/checks'
import { list as listServers } from '../api/servers'
import { toast } from 'vue-sonner'
import { Plus, Activity, Trash2, Play, Pencil } from 'lucide-vue-next'
import BaseModal from '../components/ui/BaseModal.vue'
import { useAuthStore } from '../stores/auth'
import { fmtDateTime } from '../utils/date'

const auth = useAuthStore()

const items = ref([])
const servers = ref([])
const loading = ref(true)
const showModal = ref(false)
const editId = ref(null)
const results = ref([])
const form = ref(defaultForm())

function defaultForm() {
  return { name: '', check_type: 'URL', target: '', interval_sec: 60, timeout_sec: 10, server_id: null, use_ssh: false, active: true }
}

const selectedServer = computed(() => servers.value.find((s) => s.id === form.value.server_id))

onMounted(async () => {
  try {
    const [chk, srv] = await Promise.all([list(), listServers()])
    items.value = chk.data
    servers.value = srv.data
  } catch {
    toast.error('Erro ao carregar')
  } finally {
    loading.value = false
  }
})

async function openNew() {
  editId.value = null
  form.value = defaultForm()
  results.value = []
  showModal.value = true
}

async function openEdit(c) {
  editId.value = c.id
  form.value = { ...c }
  results.value = []
  showModal.value = true
  try {
    const { data } = await getResults(c.id, 20)
    results.value = data
  } catch {}
}

function closeModal() {
  showModal.value = false
  editId.value = null
}

async function save() {
  try {
    if (editId.value) {
      const { data } = await update(editId.value, form.value)
      const idx = items.value.findIndex((c) => c.id === editId.value)
      if (idx >= 0) items.value[idx] = data
      toast.success('Check salvo')
    } else {
      const { data } = await create(form.value)
      items.value.push(data)
      editId.value = data.id
      toast.success('Check criado')
    }
  } catch (e) {
    const d = e.response?.data?.detail
    toast.error(Array.isArray(d) ? d.map((x) => x.msg || x).join(', ') : (d || 'Erro'))
  }
}

async function doRun(id) {
  try {
    await runNow(id)
    const { data } = await list()
    items.value = data
    toast.success('Check executado')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function doRemove(id) {
  if (!confirm('Excluir este check?')) return
  try {
    await remove(id)
    items.value = items.value.filter((c) => c.id !== id)
    toast.success('Check removido')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

function maskTarget(c) {
  if (c.check_type === 'DATABASE' && c.target) {
    const m = c.target.match(/@([^\/:]+)(?::(\d+))?/)
    return m ? `${m[1]}:${m[2] || '3306'}` : '***'
  }
  return c.target
}

function statusColor(s) {
  if (s === 'OK') return 'text-emerald-600'
  if (s === 'TIMEOUT') return 'text-amber-600'
  return 'text-red-600'
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-xl font-bold text-brand-800">Health Checks</h2>
      <button v-if="auth.isOperator" @click="openNew" class="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg">
        <Plus class="w-4 h-4" /> Novo
      </button>
    </div>

    <div v-if="loading" class="text-gray-500">Carregando...</div>
    <div v-else class="grid gap-4">
      <div v-for="c in items" :key="c.id" class="bg-white rounded-lg shadow-sm border p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div class="flex items-center gap-4 min-w-0">
          <Activity class="w-6 h-6 sm:w-8 sm:h-8 text-brand-500 shrink-0" />
          <div class="min-w-0">
            <p class="font-medium text-brand-800 truncate">{{ c.name }}</p>
            <p class="text-sm text-gray-500 truncate">{{ c.check_type }} • {{ maskTarget(c) }}</p>
          </div>
        </div>
        <div class="flex items-center gap-1 shrink-0 justify-end sm:justify-start">
          <span :class="statusColor(c.last_status)" class="text-sm font-medium mr-1">{{ c.last_status || '–' }}</span>
          <button v-if="auth.isOperator" @click="doRun(c.id)" class="p-2 text-brand-500 hover:bg-brand-50 rounded" title="Executar agora"><Play class="w-4 h-4" /></button>
          <button v-if="auth.isOperator" @click="openEdit(c)" class="p-2 text-brand-500 hover:bg-brand-50 rounded" title="Editar"><Pencil class="w-4 h-4" /></button>
          <button v-if="auth.isAdmin" @click="doRemove(c.id)" class="p-2 text-red-500 hover:bg-red-50 rounded" title="Excluir"><Trash2 class="w-4 h-4" /></button>
        </div>
      </div>
      <p v-if="!items.length" class="text-gray-500 py-8 text-center">Nenhum check configurado.</p>
    </div>

    <BaseModal v-if="showModal" :title="editId ? 'Editar Check' : 'Novo Check'" size="lg" @close="closeModal">
      <div class="space-y-4">
        <div>
          <label class="block text-sm text-gray-600 mb-1">Nome</label>
          <input v-model="form.name" class="w-full border rounded px-3 py-2" required />
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">Tipo</label>
            <select v-model="form.check_type" class="w-full border rounded px-3 py-2">
              <option value="URL">URL (HTTP)</option>
              <option value="PORT">Porta TCP</option>
              <option value="PING">Ping</option>
              <option value="TELNET">Telnet</option>
              <option value="DATABASE">Banco de dados</option>
              <option value="SNMP">SNMP (threshold de métrica)</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Servidor</label>
            <select v-model="form.server_id" class="w-full border rounded px-3 py-2">
              <option :value="null">— Nenhum —</option>
              <option v-for="s in servers" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </div>
        </div>
        <div v-if="selectedServer?.ssh_host">
          <label class="flex items-center gap-2 cursor-pointer text-sm">
            <input v-model="form.use_ssh" type="checkbox" /> Executar via SSH
          </label>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Alvo</label>
          <input
            v-model="form.target"
            class="w-full border rounded px-3 py-2"
            :placeholder="form.check_type === 'DATABASE' ? 'mysql+pymysql://usuario:senha@host:3306/banco' : form.check_type === 'SNMP' ? 'ROUTER_ID:METRIC_TYPE[:OP:VALOR] ex: 42:CPU:>:90' : 'https://... ou host:porta'"
            required
          />
          <p v-if="form.check_type === 'DATABASE'" class="mt-1 text-xs text-gray-500">
            MySQL: <code class="bg-gray-100 px-1">mysql+pymysql://user:pass@host:3306/db</code> | PG: <code class="bg-gray-100 px-1">postgresql://user:pass@host:5432/db</code>
          </p>
          <p v-if="form.check_type === 'SNMP'" class="mt-1 text-xs text-gray-500">
            Formato: <code class="bg-gray-100 px-1">ROUTER_ID:METRIC_TYPE:OPERADOR:VALOR</code>
            <br/>Métricas: CPU, MEMORY, WIFI_CLIENTS, TRAFFIC_IN, TRAFFIC_OUT, UPTIME
            <br/>Operadores: &gt;, &gt;=, &lt;, &lt;=
            <br/>Ex: <code class="bg-gray-100 px-1">42:CPU:>:90</code> alerta se CPU do roteador 42 &gt; 90%
          </p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">Intervalo (s)</label>
            <input v-model.number="form.interval_sec" type="number" class="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Timeout (s)</label>
            <input v-model.number="form.timeout_sec" type="number" class="w-full border rounded px-3 py-2" />
          </div>
        </div>
        <label class="flex items-center gap-2 cursor-pointer text-sm">
          <input v-model="form.active" type="checkbox" /> Ativo
        </label>

        <button @click="save" class="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm">
          {{ editId ? 'Salvar alterações' : 'Criar check' }}
        </button>

        <!-- Histórico (só ao editar) -->
        <div v-if="editId && results.length" class="border-t pt-4 mt-2 overflow-x-auto">
          <h4 class="font-medium text-sm mb-2">Últimos resultados</h4>
          <table class="w-full text-sm min-w-[320px]">
            <thead>
              <tr class="text-left text-gray-500 text-xs">
                <th class="py-1">Data</th>
                <th class="py-1">Status</th>
                <th class="py-1">Latência</th>
                <th class="py-1">Mensagem</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in results" :key="r.id" class="border-t">
                <td class="py-1 text-xs text-gray-500">{{ fmtDateTime(r.checked_at) }}</td>
                <td :class="r.status === 'OK' ? 'text-emerald-600' : 'text-red-600'" class="font-medium">{{ r.status }}</td>
                <td class="text-gray-600">{{ r.latency_ms != null ? r.latency_ms + 'ms' : '–' }}</td>
                <td class="text-gray-500 text-xs truncate max-w-[150px]">{{ r.message || '–' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </BaseModal>
  </div>
</template>
