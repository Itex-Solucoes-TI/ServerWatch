<script setup>
import { ref, onMounted, computed } from 'vue'
import { list, get, create, update } from '../api/companies'
import { toast } from 'vue-sonner'
import { useAuthStore } from '../stores/auth'
import BaseModal from '../components/ui/BaseModal.vue'

const items = ref([])
const loading = ref(true)
const showForm = ref(false)
const editCompany = ref(null)
const form = ref({ name: '', slug: '', cnpj: '' })
const auth = useAuthStore()

const isSuperadmin = computed(() => auth.user?.is_superadmin)

onMounted(async () => {
  try {
    if (isSuperadmin.value) {
      const { data } = await list()
      items.value = data
    } else {
      // ADMIN: carrega só a empresa atual
      const { data } = await get(auth.companyId)
      items.value = [data]
    }
  } catch (e) {
    toast.error('Erro ao carregar empresa')
  } finally {
    loading.value = false
  }
})

function slugify(s) {
  return (s || '').toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
}

function openNew() {
  editCompany.value = null
  form.value = { name: '', slug: '', cnpj: '' }
  showForm.value = true
}

function openEdit(c) {
  editCompany.value = c
  form.value = { name: c.name, slug: c.slug, cnpj: maskCnpj(c.cnpj || '') }
  showForm.value = true
}

function onNameChange() {
  if (!editCompany.value) form.value.slug = slugify(form.value.name)
}

function maskCnpj(val) {
  const d = (val || '').replace(/\D/g, '').slice(0, 14)
  if (d.length <= 2) return d
  if (d.length <= 5) return `${d.slice(0, 2)}.${d.slice(2)}`
  if (d.length <= 8) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5)}`
  if (d.length <= 12) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8)}`
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`
}

function onCnpjInput(e) {
  const v = maskCnpj(e.target.value)
  if (v !== form.value.cnpj) form.value.cnpj = v
}

function isValidCnpj(val) {
  const d = (val || '').replace(/\D/g, '')
  if (d.length !== 14) return false
  if (/^(\d)\1+$/.test(d)) return false
  const w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
  const w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
  const sum = (arr, w) => arr.reduce((s, n, i) => s + n * w[i], 0)
  const nums = d.split('').map(Number)
  const d1 = sum(nums.slice(0, 12), w1) % 11
  const d2 = sum(nums.slice(0, 13), w2) % 11
  return (d1 < 2 ? 0 : 11 - d1) === nums[12] && (d2 < 2 ? 0 : 11 - d2) === nums[13]
}

async function save() {
  const cnpj = (form.value.cnpj || '').trim()
  if (cnpj && !isValidCnpj(cnpj)) {
    toast.error('CNPJ inválido')
    return
  }
  try {
    if (editCompany.value) {
      await update(editCompany.value.id, form.value)
      auth.updateCompany(editCompany.value.id, form.value)
      const idx = items.value.findIndex((c) => c.id === editCompany.value.id)
      if (idx >= 0) items.value[idx] = { ...items.value[idx], ...form.value }
      toast.success('Empresa atualizada')
    } else {
      const { data } = await create(form.value)
      items.value.push(data)
      toast.success('Empresa criada')
    }
    showForm.value = false
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-xl font-bold text-brand-800">{{ isSuperadmin ? 'Empresas' : 'Minha Empresa' }}</h2>
      <button v-if="isSuperadmin" @click="openNew" class="px-4 py-2 bg-brand-500 text-white rounded-lg">Nova</button>
    </div>

    <div v-if="loading" class="text-gray-500">Carregando...</div>
    <div v-else class="bg-white rounded-lg shadow-sm border overflow-hidden">
      <table class="w-full">
        <thead class="bg-gray-50">
          <tr>
            <th class="text-left px-4 py-3 text-sm font-medium text-gray-600">Nome</th>
            <th class="text-left px-4 py-3 text-sm font-medium text-gray-600">Slug</th>
            <th class="text-left px-4 py-3 text-sm font-medium text-gray-600">CNPJ</th>
            <th class="px-4 py-3 w-20"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in items" :key="c.id" class="border-t hover:bg-gray-50">
            <td class="px-4 py-3">{{ c.name }}</td>
            <td class="px-4 py-3 text-gray-500 text-sm">{{ c.slug }}</td>
            <td class="px-4 py-3 text-gray-500 text-sm">{{ c.cnpj || '—' }}</td>
            <td class="px-4 py-3">
              <button @click="openEdit(c)" class="text-brand-500 text-sm hover:underline">Editar</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BaseModal v-if="showForm" :title="editCompany ? 'Editar Empresa' : 'Nova Empresa'" @close="showForm = false">
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="block text-sm text-gray-600 mb-1">Nome</label>
          <input v-model="form.name" @input="onNameChange" class="w-full border rounded px-3 py-2" required />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">Slug</label>
          <input v-model="form.slug" class="w-full border rounded px-3 py-2" :disabled="!!editCompany && !isSuperadmin" required />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">CNPJ</label>
          <input v-model="form.cnpj" @input="onCnpjInput" class="w-full border rounded px-3 py-2" placeholder="00.000.000/0000-00" maxlength="18" />
        </div>
        <div class="flex gap-2">
          <button type="submit" class="px-4 py-2 bg-brand-500 text-white rounded-lg">{{ editCompany ? 'Salvar' : 'Criar' }}</button>
          <button type="button" @click="showForm = false" class="px-4 py-2 border rounded-lg">Cancelar</button>
        </div>
      </form>
    </BaseModal>
  </div>
</template>
