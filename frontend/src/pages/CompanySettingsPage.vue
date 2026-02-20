<script setup>
import { ref, onMounted } from 'vue'
import { get, update } from '../api/settings'
import { status as licenseStatus, activate as licenseActivate, remove as licenseRemove } from '../api/license'
import { useAuthStore } from '../stores/auth'
import { toast } from 'vue-sonner'

const s = ref({})
const loading = ref(true)
const license = ref({ needs_license: true, valid_until: null })
const licenseToken = ref('')
const licenseLoading = ref(false)
const auth = useAuthStore()

onMounted(async () => {
  try {
    const [settingsRes, licenseRes] = await Promise.all([get(), licenseStatus()])
    s.value = settingsRes.data
    license.value = licenseRes.data
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

async function activateLicense() {
  if (!licenseToken.value.trim()) return
  licenseLoading.value = true
  try {
    await licenseActivate(licenseToken.value.trim())
    const res = await licenseStatus()
    license.value = res.data
    licenseToken.value = ''
    auth.companies.forEach((c) => { c.license_valid = true; c.license_valid_until = license.value.valid_until })
    auth.needsLicense = false
    toast.success('Licença ativada')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Token inválido ou expirado')
  } finally {
    licenseLoading.value = false
  }
}

function formatDate(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function formatCnpj(d) {
  if (!d || d.length !== 14) return d || ''
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`
}

async function removeLicense() {
  if (!confirm('Remover licença? Será necessário ativar novamente no próximo login.')) return
  licenseLoading.value = true
  try {
    await licenseRemove()
    license.value = { needs_license: true, valid_until: null }
    auth.companies.forEach((c) => { c.license_valid = false; c.license_valid_until = null })
    auth.needsLicense = true
    toast.success('Licença removida')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  } finally {
    licenseLoading.value = false
  }
}
</script>

<template>
  <div>
    <h2 class="text-xl font-bold text-brand-800 mb-6">Configurações</h2>
    <div v-if="loading" class="text-gray-500">Carregando...</div>
    <form v-else @submit.prevent="save" class="bg-white rounded-lg shadow-sm border p-6 max-w-2xl space-y-6">
      <div>
        <h3 class="font-medium mb-4">Licença</h3>
        <div class="space-y-4">
          <div v-if="license.valid_until" class="p-3 bg-gray-50 rounded-lg space-y-1">
            <p v-if="license.cnpj" class="text-sm text-gray-600">CNPJ da licença</p>
            <p v-if="license.cnpj" class="font-medium font-mono">{{ formatCnpj(license.cnpj) }}</p>
            <p class="text-sm text-gray-600">Válida até</p>
            <p class="font-medium">{{ formatDate(license.valid_until) }}</p>
          </div>
          <div v-else class="p-3 bg-amber-50 rounded-lg text-amber-800 text-sm">
            Sem licença ativa
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Nova licença (token)</label>
            <div class="flex gap-2">
              <input
                v-model="licenseToken"
                type="text"
                placeholder="Cole o token da licença"
                class="flex-1 border rounded px-3 py-2"
              />
              <button
                type="button"
                @click="activateLicense"
                :disabled="licenseLoading || !licenseToken.trim()"
                class="px-4 py-2 bg-brand-500 text-white rounded-lg disabled:opacity-50"
              >
                Ativar
              </button>
            </div>
          </div>
          <button
            v-if="license.valid_until"
            type="button"
            @click="removeLicense"
            :disabled="licenseLoading"
            class="text-red-600 hover:text-red-700 text-sm"
          >
            Excluir licença
          </button>
        </div>
      </div>
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
