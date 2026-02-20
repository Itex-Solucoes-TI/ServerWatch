<script setup>
import { ref, onMounted } from 'vue'
import { list, create, update, remove, listInterfaces, addInterface, updateInterface, removeInterface } from '../api/servers'
import { toast } from 'vue-sonner'
import { Plus, Server, Trash2, Pencil } from 'lucide-vue-next'
import BaseModal from '../components/ui/BaseModal.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const items = ref([])
const loading = ref(true)
const showModal = ref(false)
const editId = ref(null)
const interfaces = ref([])
const form = ref(defaultForm())
const editInt = ref(null)
const intForm = ref(defaultIntForm())

function defaultForm() {
  return { name: '', hostname: '', environment: 'production', has_docker: false, docker_host: '', docker_tls_ca_cert: '', docker_tls_client_cert: '', docker_tls_client_key: '', ssh_host: '', ssh_port: 22, ssh_user: '', ssh_password: '' }
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
    toast.error('Erro ao carregar servidores')
  } finally {
    loading.value = false
  }
}

async function openNew() {
  editId.value = null
  form.value = defaultForm()
  interfaces.value = []
  editInt.value = null
  intForm.value = defaultIntForm()
  showModal.value = true
}

async function openEdit(s) {
  editId.value = s.id
  form.value = { ...s }
  editInt.value = null
  intForm.value = defaultIntForm()
  showModal.value = true
  try {
    const { data } = await listInterfaces(s.id)
    interfaces.value = data
  } catch {
    interfaces.value = []
  }
}

function closeModal() {
  showModal.value = false
  editId.value = null
}

async function save() {
  try {
    if (editId.value) {
      await update(editId.value, form.value)
      toast.success('Servidor salvo')
    } else {
      const { data } = await create(form.value)
      editId.value = data.id
      items.value.push(data)
      toast.success('Servidor criado')
      return
    }
    await load()
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function doRemove(id) {
  if (!confirm('Excluir este servidor?')) return
  try {
    await remove(id)
    items.value = items.value.filter((s) => s.id !== id)
    toast.success('Servidor removido')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

function openEditInt(i) {
  editInt.value = i
  intForm.value = { ip_address: i.ip_address, interface_name: i.interface_name || '', subnet_mask: i.subnet_mask || '', is_external: i.is_external || false, is_vpn: i.is_vpn || false, is_primary: i.is_primary || false }
}

function cancelInt() {
  editInt.value = null
  intForm.value = defaultIntForm()
}

async function saveInt() {
  if (!intForm.value.ip_address.trim() || !editId.value) return
  try {
    if (editInt.value) {
      const { data } = await updateInterface(editId.value, editInt.value.id, intForm.value)
      const idx = interfaces.value.findIndex((x) => x.id === editInt.value.id)
      if (idx >= 0) interfaces.value[idx] = data
      toast.success('Interface atualizada')
    } else {
      const { data } = await addInterface(editId.value, intForm.value)
      interfaces.value.push(data)
      toast.success('Interface adicionada')
    }
    cancelInt()
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function delInt(id) {
  try {
    await removeInterface(editId.value, id)
    interfaces.value = interfaces.value.filter((i) => i.id !== id)
    toast.success('Interface removida')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-xl font-bold text-brand-800">Servidores</h2>
      <button v-if="auth.isOperator" @click="openNew" class="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg">
        <Plus class="w-4 h-4" /> Novo
      </button>
    </div>

    <div v-if="loading" class="text-gray-500">Carregando...</div>
    <div v-else class="grid gap-4">
      <div v-for="s in items" :key="s.id" class="bg-white rounded-lg shadow-sm border p-4 flex items-center justify-between hover:border-brand-300">
        <div class="flex items-center gap-4">
          <Server class="w-8 h-8 text-brand-500 shrink-0" />
          <div>
            <p class="font-medium text-brand-800">{{ s.name }}</p>
            <p class="text-sm text-gray-500">{{ s.hostname || '—' }} <span class="ml-1 text-xs bg-gray-100 px-1.5 py-0.5 rounded capitalize">{{ s.environment }}</span></p>
          </div>
        </div>
        <div v-if="auth.isOperator" class="flex gap-1">
          <button @click="openEdit(s)" class="p-2 text-brand-500 hover:bg-brand-50 rounded" title="Editar"><Pencil class="w-4 h-4" /></button>
          <button v-if="auth.isAdmin" @click="doRemove(s.id)" class="p-2 text-red-500 hover:bg-red-50 rounded" title="Excluir"><Trash2 class="w-4 h-4" /></button>
        </div>
      </div>
      <p v-if="!items.length" class="text-gray-500 py-8 text-center">Nenhum servidor cadastrado.</p>
    </div>

    <BaseModal v-if="showModal" :title="editId ? 'Editar Servidor' : 'Novo Servidor'" size="xl" @close="closeModal">
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">Nome</label>
            <input v-model="form.name" class="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Hostname</label>
            <input v-model="form.hostname" autocomplete="off" class="w-full border rounded px-3 py-2" />
          </div>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Ambiente</label>
          <select v-model="form.environment" class="w-full border rounded px-3 py-2">
            <option value="production">Production</option>
            <option value="staging">Staging</option>
            <option value="development">Development</option>
            <option value="homologation">Homologação</option>
          </select>
        </div>
        <label class="flex items-center gap-2 cursor-pointer">
          <input v-model="form.has_docker" type="checkbox" />
          <span class="text-sm">Servidor com Docker</span>
        </label>
        <div v-if="form.has_docker">
          <label class="block text-sm text-gray-600 mb-1">Docker Host</label>
          <input v-model="form.docker_host" placeholder="tcp://IP:2375 ou https://IP:2376 — via SSH: deixe vazio" class="w-full border rounded px-3 py-2" />
        </div>

        <details class="border rounded-lg">
          <summary class="cursor-pointer px-4 py-2 text-sm text-brand-600 font-medium">Acesso SSH</summary>
          <div class="p-4 space-y-3 bg-gray-50">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-gray-500 mb-0.5">Host</label>
                <input v-model="form.ssh_host" placeholder="IP ou hostname" class="w-full border rounded px-2 py-1.5 text-sm" />
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-0.5">Porta</label>
                <input v-model.number="form.ssh_port" type="number" placeholder="22" class="w-full border rounded px-2 py-1.5 text-sm" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-gray-500 mb-0.5">Usuário</label>
                <input v-model="form.ssh_user" placeholder="Usuário" class="w-full border rounded px-2 py-1.5 text-sm" />
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-0.5">Senha</label>
                <input v-model="form.ssh_password" type="password" placeholder="Senha SSH" class="w-full border rounded px-2 py-1.5 text-sm" />
              </div>
            </div>
            <p class="text-xs text-gray-500">Com Docker marcado e SSH preenchido, deixe Docker Host vazio — usa túnel SSH.</p>
          </div>
        </details>

        <details v-if="form.has_docker" class="border rounded-lg">
          <summary class="cursor-pointer px-4 py-2 text-sm text-brand-600 font-medium">Docker TLS</summary>
          <div class="p-4 space-y-3 bg-gray-50">
            <div>
              <label class="block text-xs text-gray-500 mb-0.5">CA (opcional)</label>
              <textarea v-model="form.docker_tls_ca_cert" rows="2" placeholder="PEM" class="w-full border rounded px-2 py-1 text-xs font-mono" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-0.5">Certificado cliente</label>
              <textarea v-model="form.docker_tls_client_cert" rows="2" placeholder="PEM" class="w-full border rounded px-2 py-1 text-xs font-mono" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-0.5">Chave privada cliente</label>
              <textarea v-model="form.docker_tls_client_key" rows="2" placeholder="PEM" class="w-full border rounded px-2 py-1 text-xs font-mono" />
            </div>
          </div>
        </details>

        <button @click="save" class="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm">
          {{ editId ? 'Salvar alterações' : 'Criar servidor' }}
        </button>

        <!-- Interfaces (só após criar) -->
        <div v-if="editId" class="border-t pt-4 mt-2">
          <h4 class="font-medium text-sm mb-3">Interfaces de rede</h4>
          <div class="bg-gray-50 rounded-lg p-3 space-y-2 mb-3">
            <div class="flex gap-2 flex-wrap">
              <input v-model="intForm.ip_address" placeholder="IP (200.x.x.x ou 192.168.0.1)" class="border rounded px-2 py-1.5 text-sm flex-1 min-w-[140px]" />
              <input v-model="intForm.interface_name" placeholder="eth0, WAN..." class="border rounded px-2 py-1.5 text-sm w-24" />
              <input v-model="intForm.subnet_mask" placeholder="/24" class="border rounded px-2 py-1.5 text-sm w-16" />
            </div>
            <div class="flex gap-4 items-center flex-wrap text-sm">
              <label class="flex items-center gap-1 cursor-pointer"><input v-model="intForm.is_external" type="checkbox" /> IP público</label>
              <label class="flex items-center gap-1 cursor-pointer"><input v-model="intForm.is_primary" type="checkbox" /> LAN</label>
              <label class="flex items-center gap-1 cursor-pointer"><input v-model="intForm.is_vpn" type="checkbox" /> VPN</label>
              <button @click="saveInt" class="px-3 py-1 bg-brand-500 text-white rounded text-sm">{{ editInt ? 'Salvar' : 'Adicionar' }}</button>
              <button v-if="editInt" @click="cancelInt" class="px-3 py-1 border rounded text-sm">Cancelar</button>
            </div>
          </div>
          <ul class="divide-y text-sm">
            <li v-for="i in interfaces" :key="i.id" class="flex justify-between items-center py-1.5">
              <span>
                <span class="font-mono">{{ i.ip_address }}</span>
                <span v-if="i.subnet_mask" class="text-gray-400">{{ i.subnet_mask }}</span>
                <span v-if="i.interface_name" class="text-gray-400 ml-1">({{ i.interface_name }})</span>
                <span v-if="i.is_external" class="text-amber-600 text-xs ml-1">público</span>
                <span v-if="i.is_primary" class="text-emerald-600 text-xs ml-1">LAN</span>
                <span v-if="i.is_vpn" class="text-brand-600 text-xs ml-1">VPN</span>
              </span>
              <div class="flex gap-2">
                <button @click="openEditInt(i)" class="text-brand-500 hover:underline text-xs">Editar</button>
                <button @click="delInt(i.id)" class="text-red-500 hover:underline text-xs">Remover</button>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </BaseModal>
  </div>
</template>
