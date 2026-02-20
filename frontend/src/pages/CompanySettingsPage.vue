<script setup>
import { ref, onMounted } from 'vue'
import { get, update } from '../api/settings'
import { toast } from 'vue-sonner'

const s = ref({})
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await get()
    s.value = data
  } catch (e) {
    toast.error('Erro ao carregar configurações')
  } finally {
    loading.value = false
  }
})

async function save() {
  try {
    await update(s.value)
    toast.success('Configurações salvas')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}
</script>

<template>
  <div>
    <h2 class="text-xl font-bold text-brand-800 mb-6">Configurações</h2>
    <div v-if="loading" class="text-gray-500">Carregando...</div>
    <form v-else @submit.prevent="save" class="bg-white rounded-lg shadow-sm border p-6 max-w-2xl space-y-6">
      <div>
        <h3 class="font-medium mb-4">SMTP (Email)</h3>
        <div class="grid gap-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">Host</label>
            <input v-model="s.smtp_host" class="w-full border rounded px-3 py-2" placeholder="smtp.exemplo.com" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm text-gray-600 mb-1">Porta</label>
              <input v-model.number="s.smtp_port" type="number" class="w-full border rounded px-3 py-2" />
            </div>
            <div class="flex items-center gap-2 pt-8">
              <input v-model="s.smtp_tls" type="checkbox" id="tls" />
              <label for="tls">TLS</label>
            </div>
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Usuário</label>
            <input v-model="s.smtp_user" class="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Senha</label>
            <input v-model="s.smtp_password" type="password" class="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Remetente</label>
            <input v-model="s.smtp_from" class="w-full border rounded px-3 py-2" placeholder="noreply@empresa.com" />
          </div>
        </div>
      </div>
      <div>
        <h3 class="font-medium mb-4">Z-API (WhatsApp)</h3>
        <div class="grid gap-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">Instance ID</label>
            <input v-model="s.zapi_instance_id" class="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Token</label>
            <input v-model="s.zapi_token" class="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Client Token (opcional)</label>
            <input v-model="s.zapi_client_token" class="w-full border rounded px-3 py-2" />
          </div>
        </div>
      </div>
      <button type="submit" class="px-6 py-2 bg-brand-500 text-white rounded-lg">Salvar</button>
    </form>
  </div>
</template>
