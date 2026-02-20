<script setup>
import { ref, onMounted } from 'vue'
import { listChannels, createChannel, updateChannel, deleteChannel, listRules, createRule, updateRule, deleteRule } from '../api/notifications'
import { list as listChecks } from '../api/checks'
import { toast } from 'vue-sonner'
import BaseModal from '../components/ui/BaseModal.vue'

const channels = ref([])
const rules = ref([])
const checks = ref([])
const showChannelForm = ref(false)
const showRuleForm = ref(false)
const editChannelId = ref(null)
const editRuleId = ref(null)
const newChannel = ref({ name: '', channel_type: 'EMAIL', target: '' })
const newRule = ref({ check_id: null, channel_id: null, fail_threshold: 3 })

const checkById = (id) => checks.value.find((c) => c.id === id)
const channelById = (id) => channels.value.find((ch) => ch.id === id)
const ruleLabel = (r) => {
  const check = checkById(r.check_id)
  const channel = channelById(r.channel_id)
  return `${check?.name ?? 'Check #' + r.check_id} → ${channel?.name ?? 'Canal #' + r.channel_id} (≥${r.fail_threshold} falhas)`
}

onMounted(async () => {
  try {
    const [ch, ru, chk] = await Promise.all([
      listChannels(),
      listRules(),
      listChecks(),
    ])
    channels.value = ch.data
    rules.value = ru.data
    checks.value = chk.data
  } catch (e) {
    toast.error('Erro ao carregar')
  }
})

function openEditChannel(ch) {
  editChannelId.value = ch.id
  newChannel.value = { name: ch.name, channel_type: ch.channel_type, target: ch.target }
  showChannelForm.value = true
}

function openEditRule(r) {
  editRuleId.value = r.id
  newRule.value = { check_id: r.check_id, channel_id: r.channel_id, fail_threshold: r.fail_threshold }
  showRuleForm.value = true
}

function cancelEdit() {
  editChannelId.value = null
  editRuleId.value = null
  newChannel.value = { name: '', channel_type: 'EMAIL', target: '' }
  newRule.value = { check_id: null, channel_id: null, fail_threshold: 3 }
  showChannelForm.value = false
  showRuleForm.value = false
}

function openNewChannel() {
  cancelEdit()
  showChannelForm.value = true
}

function openNewRule() {
  cancelEdit()
  showRuleForm.value = true
}

async function saveChannel() {
  try {
    if (editChannelId.value) {
      const { data } = await updateChannel(editChannelId.value, newChannel.value)
      const idx = channels.value.findIndex((c) => c.id === editChannelId.value)
      if (idx >= 0) channels.value[idx] = data
      toast.success('Canal atualizado')
    } else {
      const { data } = await createChannel(newChannel.value)
      channels.value.push(data)
      toast.success('Canal criado')
    }
    cancelEdit()
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function saveRule() {
  if (!newRule.value.check_id || !newRule.value.channel_id) {
    toast.error('Selecione check e canal')
    return
  }
  try {
    if (editRuleId.value) {
      const { data } = await updateRule(editRuleId.value, newRule.value)
      const idx = rules.value.findIndex((r) => r.id === editRuleId.value)
      if (idx >= 0) rules.value[idx] = data
      toast.success('Regra atualizada')
    } else {
      const { data } = await createRule(newRule.value)
      rules.value.push(data)
      toast.success('Regra criada')
    }
    cancelEdit()
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function delChannel(ch) {
  if (!confirm('Remover este canal?')) return
  try {
    await deleteChannel(ch.id)
    channels.value = channels.value.filter((c) => c.id !== ch.id)
    rules.value = rules.value.filter((r) => r.channel_id !== ch.id)
    toast.success('Canal removido')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function delRule(r) {
  if (!confirm('Remover esta regra?')) return
  try {
    await deleteRule(r.id)
    rules.value = rules.value.filter((x) => x.id !== r.id)
    toast.success('Regra removida')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}
</script>

<template>
  <div>
    <h2 class="text-xl font-bold text-brand-800 mb-6">Notificações</h2>
    <div class="grid gap-6 md:grid-cols-2">
      <div class="bg-white rounded-lg shadow-sm border p-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="font-medium">Canais</h3>
          <button @click="openNewChannel" class="text-brand-500 text-sm">+ Novo</button>
        </div>
        <ul class="space-y-2">
          <li v-for="ch in channels" :key="ch.id" class="py-2 border-b flex justify-between items-center">
            <span>{{ ch.name }} ({{ ch.channel_type }}) → {{ ch.target }}</span>
            <div class="flex gap-2 text-sm">
              <button @click="openEditChannel(ch)" class="text-brand-500 hover:underline">Editar</button>
              <button @click="delChannel(ch)" class="text-red-500 hover:underline">Remover</button>
            </div>
          </li>
        </ul>
      </div>
      <div class="bg-white rounded-lg shadow-sm border p-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="font-medium">Regras de Alerta</h3>
          <button @click="openNewRule" class="text-brand-500 text-sm">+ Nova</button>
        </div>
        <ul class="space-y-2">
          <li v-for="r in rules" :key="r.id" class="py-2 border-b flex justify-between items-center text-sm">
            <span>{{ ruleLabel(r) }}</span>
            <div class="flex gap-2 shrink-0">
              <button @click="openEditRule(r)" class="text-brand-500 hover:underline">Editar</button>
              <button @click="delRule(r)" class="text-red-500 hover:underline">Remover</button>
            </div>
          </li>
        </ul>
      </div>
    </div>

    <BaseModal v-if="showChannelForm" :title="editChannelId ? 'Editar Canal' : 'Novo Canal'" @close="cancelEdit">
      <form @submit.prevent="saveChannel" class="space-y-4">
        <div>
          <label class="block text-sm text-gray-600 mb-1">Nome</label>
          <input v-model="newChannel.name" class="w-full border rounded px-3 py-2" required />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Tipo</label>
          <select v-model="newChannel.channel_type" class="w-full border rounded px-3 py-2">
            <option value="EMAIL">Email</option>
            <option value="WHATSAPP">WhatsApp (Z-API)</option>
            <option value="WEBHOOK">Webhook</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Destino</label>
          <input v-model="newChannel.target" placeholder="Email, telefone ou URL" class="w-full border rounded px-3 py-2" required />
        </div>
        <div class="flex gap-2">
          <button type="submit" class="px-4 py-2 bg-brand-500 text-white rounded-lg">{{ editChannelId ? 'Salvar' : 'Criar' }}</button>
          <button type="button" @click="cancelEdit" class="px-4 py-2 border rounded-lg">Cancelar</button>
        </div>
      </form>
    </BaseModal>

    <BaseModal v-if="showRuleForm" :title="editRuleId ? 'Editar Regra' : 'Nova Regra de Alerta'" @close="cancelEdit">
      <form @submit.prevent="saveRule" class="space-y-4">
        <div>
          <label class="block text-sm text-gray-600 mb-1">Check</label>
          <select v-model="newRule.check_id" class="w-full border rounded px-3 py-2" required>
            <option :value="null">Selecione o check</option>
            <option v-for="c in checks" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Canal</label>
          <select v-model="newRule.channel_id" class="w-full border rounded px-3 py-2" required>
            <option :value="null">Selecione o canal</option>
            <option v-for="ch in channels" :key="ch.id" :value="ch.id">{{ ch.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Falhas consecutivas para alertar</label>
          <input v-model.number="newRule.fail_threshold" type="number" min="1" class="w-full border rounded px-3 py-2" />
        </div>
        <div class="flex gap-2">
          <button type="submit" class="px-4 py-2 bg-brand-500 text-white rounded-lg">{{ editRuleId ? 'Salvar' : 'Criar' }}</button>
          <button type="button" @click="cancelEdit" class="px-4 py-2 border rounded-lg">Cancelar</button>
        </div>
      </form>
    </BaseModal>
  </div>
</template>
