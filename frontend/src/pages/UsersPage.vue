<script setup>
import { ref, onMounted } from 'vue'
import { list, create, update, remove, myAdminCompanies, getUserCompanies } from '../api/users'
import { toast } from 'vue-sonner'
import { Pencil, Trash2 } from 'lucide-vue-next'
import BaseModal from '../components/ui/BaseModal.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const items = ref([])
const loading = ref(true)
const showForm = ref(false)
const editUser = ref(null)
const adminCompanies = ref([]) // empresas onde o criador é ADMIN

const form = ref(defaultForm())

function defaultForm() {
  return { name: '', email: '', password: '', company_roles: [] }
}

const roleLabel = (r) => r === 'ADMIN' ? 'Admin' : r === 'OPERATOR' ? 'Operador' : 'Visualizador'
const roleOptions = [
  { value: 'VIEWER', label: 'Visualizador' },
  { value: 'OPERATOR', label: 'Operador' },
  { value: 'ADMIN', label: 'Admin' },
]

onMounted(load)

async function load() {
  try {
    const { data } = await list()
    items.value = data
  } catch {
    toast.error('Erro ao carregar usuários')
  } finally {
    loading.value = false
  }
}

async function openForm(u = null) {
  editUser.value = u
  // carrega empresas disponíveis para o criador
  try {
    const { data } = await myAdminCompanies()
    adminCompanies.value = data
  } catch {
    adminCompanies.value = []
  }

  if (u) {
    // busca todos os vínculos reais do usuário
    let existingRoles = []
    try {
      const { data } = await getUserCompanies(u.id)
      existingRoles = data // [{ company_id, role }]
    } catch {}

    form.value = {
      name: u.name,
      email: u.email,
      password: '',
      company_roles: adminCompanies.value.map((c) => {
        const found = existingRoles.find((r) => r.company_id === c.id)
        return { company_id: c.id, role: found ? found.role : null }
      }),
    }
  } else {
    form.value = {
      ...defaultForm(),
      company_roles: adminCompanies.value.map((c) => ({
        company_id: c.id,
        role: c.id === auth.companyId ? 'VIEWER' : null,
      })),
    }
  }
  showForm.value = true
}

function toggleCompany(companyId, checked) {
  const cr = form.value.company_roles.find((x) => x.company_id === companyId)
  if (cr) cr.role = checked ? 'VIEWER' : null
}

function setRole(companyId, role) {
  const cr = form.value.company_roles.find((x) => x.company_id === companyId)
  if (cr) cr.role = role
}

async function save() {
  const activeRoles = form.value.company_roles.filter((cr) => cr.role !== null)

  const editandoSuperadmin = editUser.value?.is_superadmin

  if (!editandoSuperadmin && !activeRoles.length) {
    toast.error('Selecione ao menos uma empresa')
    return
  }

  const roleAtual = activeRoles.find((cr) => cr.company_id === auth.companyId)?.role ?? activeRoles[0]?.role ?? 'VIEWER'
  const payload = {
    name: form.value.name,
    email: form.value.email,
    company_roles: editandoSuperadmin ? null : activeRoles,
    role: roleAtual,
  }
  try {
    if (editUser.value) {
      if (form.value.password) payload.password = form.value.password
      const { data } = await update(editUser.value.id, payload)
      const idx = items.value.findIndex((u) => u.id === editUser.value.id)
      if (idx >= 0) items.value[idx] = data
      toast.success('Usuário atualizado')
    } else {
      payload.password = form.value.password || 'temp123'
      const { data } = await create(payload)
      items.value.push(data)
      toast.success('Usuário criado')
    }
    showForm.value = false
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function doRemove(u) {
  if (!confirm(`Remover ${u.name} desta empresa?`)) return
  try {
    await remove(u.id)
    items.value = items.value.filter((x) => x.id !== u.id)
    toast.success('Usuário removido')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-xl font-bold text-brand-800">Usuários</h2>
      <button v-if="auth.isAdmin" @click="openForm()" class="px-4 py-2 bg-brand-500 text-white rounded-lg">Novo</button>
    </div>

    <div v-if="loading" class="text-gray-500">Carregando...</div>
    <div v-else class="bg-white rounded-lg shadow-sm border overflow-hidden">
      <table class="w-full">
        <thead class="bg-gray-50">
          <tr>
            <th class="text-left px-4 py-3 text-sm font-medium text-gray-600">Nome</th>
            <th class="text-left px-4 py-3 text-sm font-medium text-gray-600">Email</th>
            <th class="text-left px-4 py-3 text-sm font-medium text-gray-600">Função</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in items" :key="u.id" class="border-t hover:bg-gray-50">
            <td class="px-4 py-3">{{ u.name }}</td>
            <td class="px-4 py-3 text-gray-500 text-sm">{{ u.email }}</td>
            <td class="px-4 py-3">
              <span class="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">{{ roleLabel(u.role) }}</span>
            </td>
            <td class="px-4 py-3">
              <div v-if="auth.isAdmin" class="flex gap-1 justify-end">
                <button @click="openForm(u)" class="p-1.5 text-brand-500 hover:bg-brand-50 rounded" title="Editar"><Pencil class="w-4 h-4" /></button>
                <button v-if="!u.is_superadmin" @click="doRemove(u)" class="p-1.5 text-red-500 hover:bg-red-50 rounded" title="Remover"><Trash2 class="w-4 h-4" /></button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BaseModal v-if="showForm" :title="editUser ? 'Editar Usuário' : 'Novo Usuário'" size="lg" @close="showForm = false">
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">Nome</label>
            <input v-model="form.name" class="w-full border rounded px-3 py-2" required />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Email</label>
            <input v-model="form.email" type="email" class="w-full border rounded px-3 py-2" required />
          </div>
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">
            Senha {{ editUser ? '(deixe vazio para manter)' : '' }}
          </label>
          <input v-model="form.password" type="password" class="w-full border rounded px-3 py-2" :required="!editUser" />
        </div>

        <!-- Acesso por empresa — não exibir se o usuário sendo editado/criado for superadmin -->
        <div v-if="!editUser?.is_superadmin">
          <label class="block text-sm font-medium text-gray-700 mb-2">Acesso por empresa</label>
          <div class="border rounded-lg divide-y">
            <div v-for="c in adminCompanies" :key="c.id" class="flex items-center gap-3 px-4 py-3">
              <input
                type="checkbox"
                :id="`company-${c.id}`"
                :checked="!!form.company_roles.find((cr) => cr.company_id === c.id && cr.role)"
                :disabled="c.id === auth.companyId"
                @change="toggleCompany(c.id, $event.target.checked)"
                class="w-4 h-4 accent-brand-500 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <label :for="`company-${c.id}`" class="flex-1 text-sm font-medium cursor-pointer">
                {{ c.name }}
                <span v-if="c.id === auth.companyId" class="text-xs text-brand-500 ml-1">(atual)</span>
              </label>
              <select
                v-if="form.company_roles.find((cr) => cr.company_id === c.id && cr.role)"
                :value="form.company_roles.find((cr) => cr.company_id === c.id)?.role"
                @change="setRole(c.id, $event.target.value)"
                class="border rounded px-2 py-1 text-sm"
              >
                <option v-for="r in roleOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
              </select>
              <span v-else class="text-xs text-gray-400">Sem acesso</span>
            </div>
          </div>
        </div>

        <div class="flex gap-2 pt-2">
          <button @click="save" class="px-4 py-2 bg-brand-500 text-white rounded-lg">Salvar</button>
          <button @click="showForm = false" class="px-4 py-2 border rounded-lg">Cancelar</button>
        </div>
      </div>
    </BaseModal>
  </div>
</template>
