<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { switchCompany } from '../../api/auth'
import { list as listCompanies } from '../../api/companies'
import { ChevronDown } from 'lucide-vue-next'

const router = useRouter()

const auth = useAuthStore()
const open = ref(false)
const allCompanies = ref(auth.companies)

async function loadAll() {
  if (!auth.user?.is_superadmin) return
  try {
    const { data } = await listCompanies()
    allCompanies.value = data
  } catch {}
}

async function selectCompany(c) {
  if (c.id === auth.companyId) {
    open.value = false
    return
  }
  try {
    const { data } = await switchCompany(c.id)
    auth.token = data.access_token
    auth.setCompany(c.id, data.role)
    if (!auth.companies.find((x) => x.id === c.id)) {
      auth.companies.push({ id: c.id, name: c.name, slug: c.slug })
    }
    open.value = false
    router.push('/dashboard')
  } catch (e) {
    console.error(e)
  }
}

function handleClickOutside(e) {
  if (open.value && !e.target.closest('.relative')) open.value = false
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  loadAll()
})
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<template>
  <div class="relative">
    <button
      @click.stop="open = !open; if (open) loadAll()"
      class="flex items-center gap-2 px-2 sm:px-3 py-2 rounded-lg hover:bg-gray-100 text-left max-w-[140px] sm:max-w-[200px]"
    >
      <span class="font-medium text-gray-700 truncate">{{ auth.currentCompany?.name || 'Selecione' }}</span>
      <ChevronDown class="w-4 h-4 text-gray-400 flex-shrink-0" />
    </button>
    <div
      v-if="open"
      @click.stop
      class="absolute top-full right-0 sm:left-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-100 py-1 min-w-[160px] max-w-[90vw] z-50"
    >
      <button
        v-for="c in allCompanies"
        :key="c.id"
        @click="selectCompany(c)"
        class="w-full px-4 py-2 text-left hover:bg-brand-50 text-sm"
        :class="{ 'bg-brand-50 text-brand-600': c.id === auth.companyId }"
      >
        {{ c.name }}
      </button>
    </div>
  </div>
</template>
