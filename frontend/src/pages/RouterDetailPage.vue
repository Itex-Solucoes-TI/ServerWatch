<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get, update, listInterfaces, addInterface, updateInterface, removeInterface } from '../api/routers'
import { toast } from 'vue-sonner'

const route = useRoute()
const router = useRouter()
const routerData = ref(null)
const interfaces = ref([])
const isNew = computed(() => route.params.id === 'new')
const editInt = ref(null)
const newInt = ref({ ip_address: '', interface_name: '', subnet_mask: '', is_external: false, is_vpn: false, is_primary: false })

onMounted(async () => {
  if (isNew.value) {
    routerData.value = { name: '', model: '', has_vpn: false }
    return
  }
  try {
    const { data } = await get(route.params.id)
    routerData.value = data
    const { data: ints } = await listInterfaces(route.params.id)
    interfaces.value = ints
  } catch (e) {
    toast.error('Erro ao carregar roteador')
  }
})

async function save() {
  try {
    if (isNew.value) {
      const { create } = await import('../api/routers')
      const { data } = await create(routerData.value)
      toast.success('Roteador criado')
      router.replace(`/routers/${data.id}`)
      routerData.value = data
    } else {
      await update(routerData.value.id, routerData.value)
      toast.success('Roteador salvo')
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
      const { data } = await updateInterface(routerData.value.id, editInt.value.id, newInt.value)
      const idx = interfaces.value.findIndex((x) => x.id === editInt.value.id)
      if (idx >= 0) interfaces.value[idx] = data
      toast.success('Interface atualizada')
    } else {
      const { data } = await addInterface(routerData.value.id, newInt.value)
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
    await removeInterface(routerData.value.id, id)
    interfaces.value = interfaces.value.filter((i) => i.id !== id)
    cancelEdit()
    toast.success('Interface removida')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}
</script>

<template>
  <div>
    <router-link to="/routers" class="text-brand-500 hover:underline mb-4 inline-block">← Roteadores</router-link>
    <div v-if="routerData" class="bg-white rounded-lg shadow-sm border p-6">
      <h2 class="text-xl font-bold mb-4">{{ isNew ? 'Novo Roteador' : routerData.name }}</h2>
      <div class="grid gap-4 max-w-md">
        <div>
          <label class="block text-sm text-gray-600 mb-1">Nome</label>
          <input v-model="routerData.name" class="w-full border rounded px-3 py-2" />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Modelo</label>
          <input v-model="routerData.model" class="w-full border rounded px-3 py-2" />
        </div>
        <div class="flex items-center gap-2">
          <input v-model="routerData.has_vpn" type="checkbox" id="vpn" />
          <label for="vpn">Possui VPN</label>
        </div>
        <button @click="save" class="px-4 py-2 bg-brand-500 text-white rounded-lg w-fit">Salvar</button>
      </div>
      <div v-if="!isNew" class="mt-8">
        <h3 class="font-medium mb-2">Interfaces</h3>
        <p class="text-sm text-gray-500 mb-2">Ex: IP público (WAN), IP privado 192.168.0.1/24 (LAN), interfaces VPN</p>
        <div class="grid gap-2 max-w-lg mb-4 p-4 bg-gray-50 rounded-lg">
          <div class="flex gap-2 flex-wrap">
            <input v-model="newInt.ip_address" placeholder="IP (ex: 200.x.x.x ou 192.168.0.1)" class="border rounded px-3 py-2 flex-1 min-w-[160px]" />
            <input v-model="newInt.interface_name" placeholder="Interface (WAN1, LAN, tun0...)" class="border rounded px-3 py-2 w-28" />
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
