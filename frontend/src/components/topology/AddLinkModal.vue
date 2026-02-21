<script setup>
import { ref, computed } from 'vue'
import { createLink } from '../../api/topology'

const props = defineProps({ nodes: { type: Array, default: () => [] } })
const emit = defineEmits(['done', 'close'])

const source = ref('')
const target = ref('')
const linkType = ref('LAN')
const loading = ref(false)

const TYPE_LABEL = { server: 'Servidor', router: 'Rede', generic: 'Dispositivo' }

const options = computed(() =>
  props.nodes.map((n) => ({
    value: n.id,
    label: `${n.data?.label || n.id} (${TYPE_LABEL[n.type] || n.type})`,
  }))
)

const sourceOptions = computed(() => options.value.filter((o) => o.value !== target.value))
const targetOptions = computed(() => options.value.filter((o) => o.value !== source.value))

function parseNode(nodeId) {
  if (nodeId.startsWith('S-')) return { server_id: parseInt(nodeId.replace('S-', '')) }
  if (nodeId.startsWith('G-')) return { generic_id: parseInt(nodeId.replace('G-', '')) }
  // R- ou INTERNET/VPN
  const id = parseInt(nodeId.replace('R-', ''))
  return isNaN(id) ? {} : { router_id: id }
}

async function submit() {
  if (!source.value || !target.value) return
  loading.value = true
  try {
    const src = parseNode(source.value)
    const tgt = parseNode(target.value)
    await createLink({
      link_type: linkType.value,
      source_server_id: src.server_id ?? null,
      source_router_id: src.router_id ?? null,
      source_generic_id: src.generic_id ?? null,
      target_server_id: tgt.server_id ?? null,
      target_router_id: tgt.router_id ?? null,
      target_generic_id: tgt.generic_id ?? null,
    })
    emit('done')
    emit('close')
    source.value = ''
    target.value = ''
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="emit('close')">
    <div class="bg-white rounded-lg p-6 w-full max-w-md">
      <h3 class="font-medium mb-4">Adicionar Ligação</h3>
      <form @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm text-gray-600 mb-1">Origem</label>
          <select v-model="source" class="w-full border rounded px-3 py-2" required>
            <option value="">Selecione</option>
            <option v-for="o in sourceOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Destino</label>
          <select v-model="target" class="w-full border rounded px-3 py-2" required>
            <option value="">Selecione</option>
            <option v-for="o in targetOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Tipo</label>
          <select v-model="linkType" class="w-full border rounded px-3 py-2">
            <option value="LAN">LAN (rede local)</option>
            <option value="WAN">WAN (rede externa)</option>
            <option value="VPN">VPN</option>
            <option value="INTERNET">Internet</option>
          </select>
        </div>
        <div class="flex gap-2">
          <button type="submit" :disabled="loading" class="px-4 py-2 bg-brand-500 text-white rounded-lg">Criar</button>
          <button type="button" @click="emit('close')" class="px-4 py-2 border rounded-lg">Cancelar</button>
        </div>
      </form>
    </div>
  </div>
</template>
