<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { list, create, update, remove, cloneRouter } from '../api/routers'
import { toast } from 'vue-sonner'
import { Plus, Radio, Wifi, Network, Shield, HelpCircle, Trash2, Pencil, BarChart2, Copy } from 'lucide-vue-next'
import BaseModal from '../components/ui/BaseModal.vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()

const auth = useAuthStore()

const items = ref([])
const loading = ref(true)
const showModal = ref(false)
const editId = ref(null)
const form = ref(defaultForm())
const intForm = ref(defaultIntForm())

function defaultForm() {
  return {
    name: '',
    brand: '',
    model: '',
    location: '',
    device_type: 'ROUTER',
    has_vpn: false,
    has_external_ip: false,
    create_ping_check: false
  }
}
function defaultIntForm() {
  return { ip_address: '', interface_name: '', subnet_mask: '', is_external: false, is_vpn: false, is_primary: false }
}

onMounted(load)

async function load() {
  try {
    const { data } = await list()
    items.value = data
  } catch {
    toast.error('Erro ao carregar roteadores')
  } finally {
    loading.value = false
  }
}

const createInterfaces = ref([])

function openNew() {
  editId.value = null
  form.value = defaultForm()
  createInterfaces.value = []
  intForm.value = defaultIntForm()
  showModal.value = true
}

async function openEdit(r) {
  editId.value = r.id
  form.value = { ...r }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editId.value = null
}

async function save() {
  try {
    if (editId.value) {
      await update(editId.value, {
        name: form.value.name, brand: form.value.brand, model: form.value.model,
        location: form.value.location, device_type: form.value.device_type,
        has_vpn: form.value.has_vpn, has_external_ip: form.value.has_external_ip,
      })
      toast.success('Salvo')
      closeModal()
      await load()
    } else {
      const payload = { ...form.value, interfaces: createInterfaces.value }
      const { data } = await create(payload)
      toast.success('Roteador criado')
      closeModal()
      // Navega para a página de detalhe para completar as configurações
      router.push(`/routers/${data.id}`)
    }
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

function addCreateInterface() {
  if (!intForm.value.ip_address.trim()) return
  createInterfaces.value.push({ ...intForm.value })
  intForm.value = defaultIntForm()
}

function removeCreateInterface(idx) {
  createInterfaces.value.splice(idx, 1)
}


async function doRemove(id) {
  if (!confirm('Excluir este roteador?')) return
  try {
    await remove(id)
    items.value = items.value.filter((r) => r.id !== id)
    toast.success('Roteador removido')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

const DEVICE_ICONS = {
  ROUTER: Radio,
  WIFI_AP: Wifi,
  SWITCH: Network,
  FIREWALL: Shield,
  OTHER: HelpCircle,
}
function deviceIcon(type) {
  return DEVICE_ICONS[type] || Radio
}

async function doClone(id) {
  try {
    const { data } = await cloneRouter(id)
    toast.success(`Clonado como "${data.name}"`)
    // Navega direto para o clone para ajustar o nome
    router.push(`/routers/${data.new_router_id}`)
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro ao clonar')
  }
}

</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-xl font-bold text-brand-800">Roteadores</h2>
      <button v-if="auth.isOperator" @click="openNew" class="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg">
        <Plus class="w-4 h-4" /> Novo
      </button>
    </div>

    <div v-if="loading" class="text-gray-500">Carregando...</div>
    <div v-else class="grid gap-4">
      <div v-for="r in items" :key="r.id" class="bg-white rounded-lg shadow-sm border p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div class="flex items-center gap-4 min-w-0">
          <component :is="deviceIcon(r.device_type)" class="w-6 h-6 sm:w-8 sm:h-8 text-brand-500 shrink-0" />
          <div class="min-w-0">
            <p class="font-medium text-brand-800 truncate cursor-pointer hover:text-brand-600" @click="router.push(`/routers/${r.id}`)">{{ r.name }}</p>
            <p class="text-sm text-gray-500 truncate">
              <span class="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded mr-1">{{ { ROUTER:'Roteador', WIFI_AP:'WiFi AP', SWITCH:'Switch', FIREWALL:'Firewall', OTHER:'Outro' }[r.device_type] || r.device_type }}</span>
              {{ [r.brand, r.model].filter(Boolean).join(' ') || '' }}
              <span v-if="r.has_vpn"> • VPN</span>
              <span v-if="r.snmp_enabled" class="ml-1 text-xs bg-brand-100 text-brand-700 px-1.5 py-0.5 rounded-full">SNMP</span>
            </p>
          </div>
        </div>
        <div class="flex gap-1 shrink-0 justify-end sm:justify-start">
          <button @click="router.push(`/routers/${r.id}`)" class="p-2 text-emerald-600 hover:bg-emerald-50 rounded" title="Monitoramento / Detalhe"><BarChart2 class="w-4 h-4" /></button>
          <button v-if="auth.isOperator" @click="openEdit(r)" class="p-2 text-brand-500 hover:bg-brand-50 rounded" title="Editar dados"><Pencil class="w-4 h-4" /></button>
          <button v-if="auth.isOperator" @click="doClone(r.id)" class="p-2 text-indigo-500 hover:bg-indigo-50 rounded" title="Clonar (copia dados, interfaces e monitores SNMP)"><Copy class="w-4 h-4" /></button>
          <button v-if="auth.isAdmin" @click="doRemove(r.id)" class="p-2 text-red-500 hover:bg-red-50 rounded" title="Excluir"><Trash2 class="w-4 h-4" /></button>
        </div>
      </div>
      <p v-if="!items.length" class="text-gray-500 py-8 text-center">Nenhum roteador cadastrado.</p>
    </div>

    <BaseModal v-if="showModal" :title="editId ? 'Editar Identificação' : 'Novo Aparelho'" size="md" @close="closeModal">
      <div class="space-y-4">
        <!-- Identificação -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="sm:col-span-2">
            <label class="block text-sm text-gray-600 mb-1">Nome <span class="text-red-500">*</span></label>
            <input v-model="form.name" class="w-full border rounded px-3 py-2 text-sm" placeholder="ex: Roteador Central, AP Sala" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Tipo de Aparelho</label>
            <select v-model="form.device_type" class="w-full border rounded px-3 py-2 text-sm">
              <option value="ROUTER">Roteador</option>
              <option value="WIFI_AP">Access Point / WiFi</option>
              <option value="SWITCH">Switch</option>
              <option value="FIREWALL">Firewall</option>
              <option value="OTHER">Outro</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Localização</label>
            <input v-model="form.location" class="w-full border rounded px-3 py-2 text-sm" placeholder="Sala de TI, Rack 2..." />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Marca</label>
            <input v-model="form.brand" class="w-full border rounded px-3 py-2 text-sm" placeholder="MikroTik, Ubiquiti..." />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Modelo</label>
            <input v-model="form.model" class="w-full border rounded px-3 py-2 text-sm" placeholder="RB3011, UAP-AC-PRO..." />
          </div>
        </div>
        <div class="flex gap-5 text-sm">
          <label class="flex items-center gap-2 cursor-pointer"><input v-model="form.has_vpn" type="checkbox" /> Possui VPN</label>
          <label class="flex items-center gap-2 cursor-pointer"><input v-model="form.has_external_ip" type="checkbox" /> IP externo</label>
        </div>

        <!-- Interfaces — só na criação -->
        <div v-if="!editId" class="border-t pt-4">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">IPs / Interfaces</p>
          <div class="bg-gray-50 rounded-lg p-3 space-y-2 mb-2">
            <div class="flex gap-2 flex-wrap">
              <input v-model="intForm.ip_address" placeholder="192.168.0.1" class="border rounded px-2 py-1.5 text-sm flex-1 min-w-[130px]" />
              <input v-model="intForm.interface_name" placeholder="WAN, LAN..." class="border rounded px-2 py-1.5 text-sm w-20" />
              <input v-model="intForm.subnet_mask" placeholder="/24" class="border rounded px-2 py-1.5 text-sm w-14" />
            </div>
            <div class="flex gap-4 items-center flex-wrap text-sm">
              <label class="flex items-center gap-1 cursor-pointer"><input v-model="intForm.is_external" type="checkbox" /> Público</label>
              <label class="flex items-center gap-1 cursor-pointer"><input v-model="intForm.is_primary" type="checkbox" /> LAN</label>
              <label class="flex items-center gap-1 cursor-pointer"><input v-model="intForm.is_vpn" type="checkbox" /> VPN</label>
              <button @click="addCreateInterface" class="px-3 py-1 bg-brand-500 text-white rounded text-sm">Adicionar</button>
            </div>
          </div>
          <ul class="divide-y text-sm mb-2">
            <li v-for="(i, idx) in createInterfaces" :key="idx" class="flex justify-between items-center py-1.5">
              <span>
                <span class="font-mono">{{ i.ip_address }}</span>
                <span v-if="i.subnet_mask" class="text-gray-400">{{ i.subnet_mask }}</span>
                <span v-if="i.interface_name" class="text-gray-400 ml-1">({{ i.interface_name }})</span>
                <span v-if="i.is_external" class="text-amber-600 text-xs ml-1">público</span>
                <span v-if="i.is_primary" class="text-emerald-600 text-xs ml-1">LAN</span>
                <span v-if="i.is_vpn" class="text-brand-600 text-xs ml-1">VPN</span>
              </span>
              <button @click="removeCreateInterface(idx)" class="text-red-500 hover:underline text-xs">Remover</button>
            </li>
          </ul>
          <label v-if="createInterfaces.length" class="flex items-center gap-2 cursor-pointer text-sm">
            <input v-model="form.create_ping_check" type="checkbox" /> Criar health check por ping automaticamente
          </label>
        </div>

        <div class="flex items-center justify-between pt-2 border-t gap-3">
          <p v-if="editId" class="text-xs text-gray-400">Rede, WiFi e SNMP: configure na página de detalhe</p>
          <div class="flex gap-2 ml-auto">
            <button @click="closeModal" class="px-4 py-2 border rounded-lg text-sm">Cancelar</button>
            <button @click="save" class="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm">
              {{ editId ? 'Salvar' : 'Criar e configurar →' }}
            </button>
          </div>
        </div>
      </div>
    </BaseModal>
  </div>
</template>
