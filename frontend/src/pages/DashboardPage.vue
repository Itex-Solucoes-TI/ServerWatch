<script setup>
import { ref, computed, onMounted } from 'vue'
import { get as getDashboard } from '../api/dashboard'
import { toast } from 'vue-sonner'

const data = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data: d } = await getDashboard()
    data.value = d
  } catch {
    toast.error('Erro ao carregar dashboard')
  } finally {
    loading.value = false
  }
})

const uptimeColor = computed(() => {
  const v = data.value?.uptime_24h_pct
  if (v == null) return 'text-gray-400'
  if (v >= 99) return 'text-green-600'
  if (v >= 95) return 'text-yellow-600'
  return 'text-red-600'
})

const statusBadge = (status) => {
  if (status === 'OK') return 'bg-green-100 text-green-700'
  if (status === 'FAIL' || status === 'ERROR') return 'bg-red-100 text-red-700'
  return 'bg-gray-100 text-gray-600'
}

const latencyColor = (ms) => {
  if (!ms) return 'text-gray-400'
  if (ms < 200) return 'text-green-600'
  if (ms < 800) return 'text-yellow-600'
  return 'text-red-600'
}

const formatDate = (iso) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}
</script>

<template>
  <div>
    <h2 class="text-xl font-bold text-brand-800 mb-6">Dashboard</h2>

    <div v-if="loading" class="text-gray-400 text-sm">Carregando...</div>

    <template v-else>
      <!-- KPIs principais -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <p class="text-xs text-gray-500 mb-1">Servidores</p>
          <p class="text-3xl font-bold text-brand-800">{{ data?.servers_count ?? 0 }}</p>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <p class="text-xs text-gray-500 mb-1">Roteadores</p>
          <p class="text-3xl font-bold text-brand-800">{{ data?.routers_count ?? 0 }}</p>
          <p v-if="data?.routers_with_vpn" class="text-xs text-gray-400 mt-1">{{ data.routers_with_vpn }} com VPN</p>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <p class="text-xs text-gray-500 mb-1">Health Checks</p>
          <p class="text-3xl font-bold text-brand-800">{{ data?.checks_count ?? 0 }}</p>
          <div class="flex gap-2 mt-1 text-xs">
            <span class="text-green-600">{{ data?.checks_ok ?? 0 }} OK</span>
            <span class="text-red-500">{{ data?.checks_fail ?? 0 }} falha</span>
            <span class="text-gray-400">{{ data?.checks_unknown ?? 0 }} sem dados</span>
          </div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <p class="text-xs text-gray-500 mb-1">Uptime 24h</p>
          <p class="text-3xl font-bold" :class="uptimeColor">
            {{ data?.uptime_24h_pct != null ? data.uptime_24h_pct + '%' : '—' }}
          </p>
          <p v-if="data?.avg_latency_ms != null" class="text-xs text-gray-400 mt-1">
            Latência média: <span :class="latencyColor(data.avg_latency_ms)">{{ data.avg_latency_ms }}ms</span>
          </p>
        </div>
      </div>

      <!-- Status dos checks (barra visual) -->
      <div v-if="data?.checks_count" class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-6">
        <p class="text-sm font-medium text-gray-700 mb-3">Status dos Checks</p>
        <div class="flex h-3 rounded-full overflow-hidden gap-0.5">
          <div
            v-if="data.checks_ok"
            class="bg-green-500 transition-all"
            :style="{ flex: data.checks_ok }"
            :title="`${data.checks_ok} OK`"
          />
          <div
            v-if="data.checks_fail"
            class="bg-red-500 transition-all"
            :style="{ flex: data.checks_fail }"
            :title="`${data.checks_fail} com falha`"
          />
          <div
            v-if="data.checks_unknown"
            class="bg-gray-300 transition-all"
            :style="{ flex: data.checks_unknown }"
            :title="`${data.checks_unknown} sem dados`"
          />
        </div>
        <div class="flex gap-4 mt-2 text-xs text-gray-500">
          <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-green-500 inline-block" />OK</span>
          <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-red-500 inline-block" />Falha</span>
          <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-gray-300 inline-block" />Sem dados</span>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-6 mb-6">
        <!-- Alertas -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 class="text-sm font-medium text-gray-700 mb-3">
            Alertas
            <span v-if="data?.alerts?.length" class="ml-1 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
              {{ data.alerts.length }}
            </span>
          </h3>
          <p v-if="!data?.alerts?.length" class="text-sm text-green-600">Nenhum alerta ativo</p>
          <ul v-else class="divide-y">
            <li v-for="a in data.alerts" :key="a.check_id" class="py-2.5 flex items-start justify-between gap-2">
              <div class="min-w-0">
                <p class="text-sm font-medium text-gray-800 truncate">{{ a.name }}</p>
                <p v-if="a.message" class="text-xs text-gray-500 truncate">{{ a.message }}</p>
                <p class="text-xs text-gray-400">{{ formatDate(a.checked_at) }}</p>
              </div>
              <div class="flex flex-col items-end gap-1 shrink-0">
                <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="statusBadge(a.status)">
                  {{ a.status }}
                </span>
                <span v-if="a.latency_ms != null" class="text-xs" :class="latencyColor(a.latency_ms)">
                  {{ a.latency_ms }}ms
                </span>
              </div>
            </li>
          </ul>
        </div>

        <!-- Checks mais lentos -->
        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 class="text-sm font-medium text-gray-700 mb-3">Checks mais lentos</h3>
          <p v-if="!data?.slowest_checks?.length" class="text-sm text-gray-400">Sem dados de latência</p>
          <ul v-else class="divide-y">
            <li v-for="s in data.slowest_checks" :key="s.check_id" class="py-2.5 flex items-center justify-between">
              <p class="text-sm text-gray-700 truncate">{{ s.name }}</p>
              <span class="text-sm font-semibold ml-2 shrink-0" :class="latencyColor(s.latency_ms)">
                {{ s.latency_ms }}ms
              </span>
            </li>
          </ul>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <!-- Distribuição por tipo de check -->
        <div v-if="data?.check_types && Object.keys(data.check_types).length" class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 class="text-sm font-medium text-gray-700 mb-3">Tipos de Check</h3>
          <ul class="space-y-2">
            <li v-for="(count, type) in data.check_types" :key="type" class="flex items-center gap-2">
              <span class="text-xs bg-brand-50 text-brand-700 px-2 py-0.5 rounded font-mono">{{ type }}</span>
              <div class="flex-1 bg-gray-100 rounded-full h-2">
                <div
                  class="bg-brand-500 h-2 rounded-full transition-all"
                  :style="{ width: (count / data.checks_count * 100) + '%' }"
                />
              </div>
              <span class="text-xs text-gray-500 w-4 text-right">{{ count }}</span>
            </li>
          </ul>
        </div>

        <!-- Servidores por ambiente -->
        <div v-if="data?.servers_by_env && Object.keys(data.servers_by_env).length" class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h3 class="text-sm font-medium text-gray-700 mb-3">Servidores por Ambiente</h3>
          <ul class="space-y-2">
            <li v-for="(count, env) in data.servers_by_env" :key="env" class="flex items-center gap-2">
              <span class="text-xs capitalize font-medium text-gray-700 w-24 truncate">{{ env }}</span>
              <div class="flex-1 bg-gray-100 rounded-full h-2">
                <div
                  class="bg-indigo-500 h-2 rounded-full transition-all"
                  :style="{ width: (count / data.servers_count * 100) + '%' }"
                />
              </div>
              <span class="text-xs text-gray-500 w-4 text-right">{{ count }}</span>
            </li>
          </ul>
        </div>
      </div>
    </template>
  </div>
</template>
