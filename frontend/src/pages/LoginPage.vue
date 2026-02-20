<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { toast } from 'vue-sonner'

const email = ref('')
const password = ref('')
const licenseToken = ref('')
const loading = ref(false)
const router = useRouter()
const auth = useAuthStore()

function goNext() {
  if (auth.companies.length === 1) {
    auth.setCompany(auth.companies[0].id)
    router.push('/dashboard')
  } else {
    router.push('/select-company')
  }
}

async function onSubmit() {
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    if (auth.needsLicense) return
    goNext()
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro ao fazer login')
  } finally {
    loading.value = false
  }
}

async function onActivateLicense() {
  if (!licenseToken.value.trim()) {
    toast.error('Informe o token')
    return
  }
  loading.value = true
  try {
    await auth.activateLicense(licenseToken.value.trim())
    toast.success('Licença ativada')
    goNext()
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Token inválido ou expirado')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-brand-800 to-brand-500 flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-xl p-8 w-full max-w-md">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-brand-800">ServerWatch</h1>
        <p class="text-gray-500 mt-1">Monitoramento de Infraestrutura</p>
      </div>

      <div v-if="auth.needsLicense" class="space-y-4">
        <p class="text-amber-700 text-sm">Licença necessária ou vencida. Insira o token de licença.</p>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Token de licença</label>
          <input
            v-model="licenseToken"
            type="text"
            placeholder="Cole o token aqui"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
        </div>
        <button
          @click="onActivateLicense"
          :disabled="loading"
          class="w-full py-2 bg-brand-500 hover:bg-brand-600 text-white font-medium rounded-lg disabled:opacity-50"
        >
          {{ loading ? 'Validando...' : 'Ativar licença' }}
        </button>
        <button
          @click="auth.logout(); router.push('/login')"
          class="w-full py-2 text-gray-600 hover:text-gray-800"
        >
          Voltar ao login
        </button>
      </div>

      <form v-else @submit.prevent="onSubmit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            v-model="email"
            type="email"
            required
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Senha</label>
          <input
            v-model="password"
            type="password"
            required
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
        </div>
        <button
          type="submit"
          :disabled="loading"
          class="w-full py-2 bg-brand-500 hover:bg-brand-600 text-white font-medium rounded-lg disabled:opacity-50"
        >
          {{ loading ? 'Entrando...' : 'Entrar' }}
        </button>
      </form>
    </div>
  </div>
</template>
