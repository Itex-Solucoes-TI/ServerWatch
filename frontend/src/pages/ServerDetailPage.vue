<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get, update, listInterfaces, addInterface, updateInterface, removeInterface } from '../api/servers'
import { toast } from 'vue-sonner'

const route = useRoute()
const router = useRouter()
const server = ref(null)
const interfaces = ref([])
const isNew = computed(() => route.params.id === 'new')
const editInt = ref(null)
const newInt = ref({ ip_address: '', interface_name: '', subnet_mask: '', is_external: false, is_vpn: false, is_primary: false })

onMounted(async () => {
  if (isNew.value) {
    server.value = { name: '', hostname: '', environment: 'production', has_docker: false, docker_host: '', docker_tls_ca_cert: '', docker_tls_client_cert: '', docker_tls_client_key: '', ssh_host: '', ssh_port: 22, ssh_user: '', ssh_password: '' }
    return
  }
  try {
    const { data } = await get(route.params.id)
    server.value = data
    const { data: ints } = await listInterfaces(route.params.id)
    interfaces.value = ints
  } catch (e) {
    toast.error('Erro ao carregar servidor')
  }
})

async function save() {
  try {
    if (isNew.value) {
      const { create } = await import('../api/servers')
      const { data } = await create(server.value)
      toast.success('Servidor criado')
      router.replace(`/servers/${data.id}`)
      server.value = data
    } else {
      const { update: apiUpdate } = await import('../api/servers')
      await apiUpdate(server.value.id, server.value)
      toast.success('Servidor salvo')
    }
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

function openEditInt(i) {
  editInt.value = i
  newInt.value = { ip_address: i.ip_address, interface_name: i.interface_name || '', subnet_mask: i.subnet_mask || '', is_external: i.is_external || false, is_vpn: i.is_vpn || false, is_primary: i.is_primary || false }
}

function cancelEdit() {
  editInt.value = null
  newInt.value = { ip_address: '', interface_name: '', subnet_mask: '', is_external: false, is_vpn: false, is_primary: false }
}

async function addInt() {
  if (!newInt.value.ip_address.trim()) return
  try {
    if (editInt.value) {
      const { data } = await updateInterface(server.value.id, editInt.value.id, newInt.value)
      const idx = interfaces.value.findIndex((x) => x.id === editInt.value.id)
      if (idx >= 0) interfaces.value[idx] = data
      toast.success('Interface atualizada')
    } else {
      const { data } = await addInterface(server.value.id, newInt.value)
      interfaces.value.push(data)
      toast.success('Interface adicionada')
    }
    cancelEdit()
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function delInt(id) {
  try {
    await removeInterface(server.value.id, id)
    interfaces.value = interfaces.value.filter((i) => i.id !== id)
    toast.success('Interface removida')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}
</script>

<template>
  <div>
    <router-link to="/servers" class="text-brand-500 hover:underline mb-4 inline-block">← Servidores</router-link>
    <div v-if="server" class="bg-white rounded-lg shadow-sm border p-6">
      <h2 class="text-xl font-bold mb-4">{{ isNew ? 'Novo Servidor' : server.name }}</h2>
      <div class="grid gap-4 max-w-md">
        <div>
          <label class="block text-sm text-gray-600 mb-1">Nome</label>
          <input v-model="server.name" class="w-full border rounded px-3 py-2" />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Hostname</label>
          <input v-model="server.hostname" class="w-full border rounded px-3 py-2" />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Ambiente</label>
          <select v-model="server.environment" class="w-full border rounded px-3 py-2">
            <option value="production">Production</option>
            <option value="staging">Staging</option>
            <option value="development">Development</option>
            <option value="homologation">Homologação</option>
          </select>
        </div>
        <div class="flex items-center gap-2">
          <input v-model="server.has_docker" type="checkbox" id="has_docker" />
          <label for="has_docker" class="text-sm">Servidor com Docker</label>
        </div>
        <div v-if="server.has_docker">
          <label class="block text-sm text-gray-600 mb-1">Docker Host</label>
          <input v-model="server.docker_host" placeholder="tcp://IP:2375 ou https://IP:2376 (TLS). Via SSH: deixe vazio" class="w-full border rounded px-3 py-2" />
        </div>
        <details class="mt-2">
          <summary class="cursor-pointer text-sm text-brand-600">Acesso SSH</summary>
          <div class="mt-2 space-y-2 p-3 bg-gray-50 rounded">
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="block text-xs text-gray-500 mb-0.5">Host</label>
                <input v-model="server.ssh_host" placeholder="IP ou hostname" class="w-full border rounded px-2 py-1 text-sm" />
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-0.5">Porta</label>
                <input v-model.number="server.ssh_port" type="number" placeholder="22" class="w-full border rounded px-2 py-1 text-sm" />
              </div>
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-0.5">Usuário</label>
              <input v-model="server.ssh_user" placeholder="Usuário" class="w-full border rounded px-2 py-1 text-sm" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-0.5">Senha</label>
              <input v-model="server.ssh_password" type="password" placeholder="Senha SSH" class="w-full border rounded px-2 py-1 text-sm" />
            </div>
            <p class="text-xs text-gray-500">Terminal e Health Checks via SSH. Com Docker marcado e SSH preenchido, <strong>Docker Host deve ficar vazio</strong> — túnel até 127.0.0.1:2375 no remoto.</p>
            <router-link
              v-if="server.ssh_host && server.ssh_user && !isNew"
              :to="`/terminal/${server.id}`"
              class="inline-flex items-center gap-1 mt-2 px-3 py-1 bg-brand-600 text-white text-sm rounded hover:bg-brand-500"
            >
              → Abrir Terminal
            </router-link>
          </div>
        </details>
        <details v-if="server.has_docker" class="mt-2">
          <summary class="cursor-pointer text-sm text-brand-600">Docker TLS (conexão segura)</summary>
          <div class="mt-2 space-y-2 p-3 bg-gray-50 rounded">
            <div>
              <label class="block text-xs text-gray-500 mb-0.5">CA (opcional)</label>
              <textarea v-model="server.docker_tls_ca_cert" placeholder="Conteúdo PEM da CA" rows="2" class="w-full border rounded px-2 py-1 text-xs font-mono"></textarea>
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-0.5">Certificado cliente</label>
              <textarea v-model="server.docker_tls_client_cert" placeholder="Conteúdo PEM do cert" rows="2" class="w-full border rounded px-2 py-1 text-xs font-mono"></textarea>
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-0.5">Chave privada cliente</label>
              <textarea v-model="server.docker_tls_client_key" placeholder="Conteúdo PEM da chave" rows="2" class="w-full border rounded px-2 py-1 text-xs font-mono"></textarea>
            </div>
          </div>
        </details>
        <button @click="save" class="px-4 py-2 bg-brand-500 text-white rounded-lg w-fit">Salvar</button>
      </div>
      <div v-if="!isNew" class="mt-8">
        <h3 class="font-medium mb-2">Interfaces</h3>
        <div class="grid gap-2 max-w-lg mb-4 p-4 bg-gray-50 rounded-lg">
          <div class="flex gap-2 flex-wrap">
            <input v-model="newInt.ip_address" placeholder="IP (ex: 200.x.x.x ou 192.168.0.1)" class="border rounded px-3 py-2 flex-1 min-w-[160px]" />
            <input v-model="newInt.interface_name" placeholder="Interface (eth0, WAN...)" class="border rounded px-3 py-2 w-24" />
            <input v-model="newInt.subnet_mask" placeholder="Máscara (/24)" class="border rounded px-3 py-2 w-20" />
          </div>
          <div class="flex gap-4 items-center flex-wrap">
            <label class="flex items-center gap-1"><input v-model="newInt.is_external" type="checkbox" /> IP público</label>
            <label class="flex items-center gap-1"><input v-model="newInt.is_primary" type="checkbox" /> Rede local (LAN)</label>
            <label class="flex items-center gap-1"><input v-model="newInt.is_vpn" type="checkbox" /> VPN</label>
            <button @click="addInt" class="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm">{{ editInt ? 'Salvar' : 'Adicionar' }}</button>
            <button v-if="editInt" @click="cancelEdit" class="px-4 py-2 border rounded-lg text-sm">Cancelar</button>
          </div>
        </div>
        <ul class="space-y-2">
          <li v-for="i in interfaces" :key="i.id" class="flex justify-between py-2 border-b items-center">
            <span><span class="font-mono">{{ i.ip_address }}</span><span v-if="i.subnet_mask" class="text-gray-400">{{ i.subnet_mask }}</span><span v-if="i.interface_name" class="text-gray-400 text-sm ml-1">({{ i.interface_name }})</span><span v-if="i.is_external" class="text-amber-600 text-xs ml-1">público</span><span v-if="i.is_primary" class="text-emerald-600 text-xs ml-1">local</span><span v-if="i.is_vpn" class="text-brand-600 text-xs ml-1">VPN</span></span>
            <div class="flex gap-2">
              <button @click="openEditInt(i)" class="text-brand-500 text-sm hover:underline">Editar</button>
              <button @click="delInt(i.id)" class="text-red-500 text-sm hover:underline">Remover</button>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
