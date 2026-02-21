<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get, update, list, listInterfaces, addInterface, updateInterface, removeInterface, listSnmpMonitors, createSnmpMonitor, updateSnmpMonitor, deleteSnmpMonitor, getSnmpLatest, getSnmpMetrics, collectSnmpNow, discoverSnmp, copySnmpMonitors, listWifiNetworks, createWifiNetwork, updateWifiNetwork, deleteWifiNetwork, copyWifiNetworks } from '../api/routers'
import { list as listChecks } from '../api/checks'
import { toast } from 'vue-sonner'
import { Plus, RefreshCw, CheckCircle, XCircle, HelpCircle, Eye, EyeOff, QrCode } from 'lucide-vue-next'
import SparkLine from '../components/ui/SparkLine.vue'
import { fmtTime } from '../utils/date'

const route = useRoute()
const router = useRouter()
const routerData = ref(null)
const interfaces = ref([])
const isNew = computed(() => route.params.id === 'new')
const editInt = ref(null)
const newInt = ref({ ip_address: '', interface_name: '', subnet_mask: '', is_external: false, is_vpn: false, is_primary: false })

// SNMP
const snmpMonitors = ref([])
const snmpLatest = ref([])
const snmpHistory = ref({})
const snmpCollecting = ref(false)
const showMonitorForm = ref(false)
const monitorForm = ref(defaultMonitorForm())
const editMonitorId = ref(null)
const routerChecks = ref([]) // health checks vinculados a este roteador

// Descoberta SNMP
const snmpDiscovery = ref(null)
const snmpDiscovering = ref(false)
const discoveryFilter = ref('')
const showDiscovery = ref(false)

// Cópia de monitores
const showCopyModal = ref(false)
const allRouters = ref([])
const copyTargetId = ref(null)
const copying = ref(false)

// Redes WiFi
const wifiNetworks = ref([])
const showWifiForm = ref(false)
const editWifiId = ref(null)
const wifiForm = ref(defaultWifiForm())
const showWifiCopyModal = ref(false)
const wifiCopyTargetId = ref(null)
const wifiCopying = ref(false)
const visiblePasswords = ref(new Set())  // IDs com senha visível
const qrModal = ref(null)               // { ssid, password, dataUrl }

function togglePassword(id) {
  const s = new Set(visiblePasswords.value)
  s.has(id) ? s.delete(id) : s.add(id)
  visiblePasswords.value = s
}

async function showQr(wn) {
  if (!wn.password) return
  const QRCode = (await import('qrcode')).default
  const wifiString = `WIFI:S:${wn.ssid};T:WPA;P:${wn.password};;`
  const dataUrl = await QRCode.toDataURL(wifiString, { width: 240, margin: 2 })
  qrModal.value = { ssid: wn.ssid, password: wn.password, dataUrl }
}

function defaultWifiForm() {
  return { ssid: '', band: '', password: '', vlan: '', notes: '', active: true }
}

const METRIC_TYPES = [
  { value: 'TRAFFIC', label: 'Tráfego (WALK todas as interfaces)', hint: 'Sem OID customizado: coleta todas as interfaces automaticamente' },
  { value: 'TRAFFIC_IN', label: 'Tráfego IN (interface específica)', hint: 'Use com OID customizado: ex 1.3.6.1.2.1.2.2.1.10.1 (ifInOctets.1)' },
  { value: 'TRAFFIC_OUT', label: 'Tráfego OUT (interface específica)', hint: 'Use com OID customizado: ex 1.3.6.1.2.1.2.2.1.16.1 (ifOutOctets.1)' },
  { value: 'CPU', label: 'CPU', hint: 'Carga % do processador' },
  { value: 'MEMORY', label: 'Memória', hint: 'Uso % da RAM' },
  { value: 'WIFI_CLIENTS', label: 'Clientes WiFi', hint: 'Número de clientes conectados' },
  { value: 'UPTIME', label: 'Uptime', hint: 'Tempo de atividade do equipamento' },
]

function defaultMonitorForm() {
  return { metric_type: 'TRAFFIC', custom_oid: '', interface_filter: '', interval_sec: 60, threshold_warn: null, active: true }
}

let wsConn = null

onMounted(async () => {
  if (isNew.value) {
    routerData.value = { name: '', brand: '', model: '', location: '', device_type: 'ROUTER', has_vpn: false, gateway: '', dns_primary: '', dns_secondary: '', wifi_ssid: '', wifi_band: '', wifi_channel: '', snmp_enabled: false, snmp_community: 'public', snmp_port: 161 }
    return
  }
  await loadRouter()
  setupWebSocket()
})

onUnmounted(() => {
  if (wsConn) wsConn.close()
})

async function loadRouter() {
  try {
    const { data } = await get(route.params.id)
    routerData.value = data
    const [ints, monitors, latest, checks, wifis] = await Promise.all([
      listInterfaces(route.params.id),
      listSnmpMonitors(route.params.id),
      getSnmpLatest(route.params.id),
      listChecks(),
      listWifiNetworks(route.params.id),
    ])
    interfaces.value = ints.data
    snmpMonitors.value = monitors.data
    snmpLatest.value = latest.data
    routerChecks.value = checks.data.filter((c) => c.router_id == route.params.id)
    wifiNetworks.value = wifis.data
    if (data.snmp_enabled && monitors.data.length) {
      await loadHistory(monitors.data)
    }
  } catch {
    toast.error('Erro ao carregar roteador')
  }
}

async function loadHistory(monitors) {
  const types = [...new Set(monitors.map((m) => m.metric_type))]
  const toLoad = new Set()
  for (const t of types) {
    if (t === 'TRAFFIC') { toLoad.add('TRAFFIC_IN'); toLoad.add('TRAFFIC_OUT') }
    else toLoad.add(t)
  }
  for (const type of toLoad) {
    try {
      const { data } = await getSnmpMetrics(route.params.id, { metric_type: type, hours: 24 })
      snmpHistory.value[type] = data
    } catch {}
  }
}

function setupWebSocket() {
  const wsBase = window.location.protocol === 'https:' ? 'wss' : 'ws'
  wsConn = new WebSocket(`${wsBase}://${window.location.host}/api/ws/events`)
  wsConn.onmessage = (e) => {
    const msg = JSON.parse(e.data)
    if (msg.event === 'snmp_update' && msg.data.router_id == route.params.id) {
      getSnmpLatest(route.params.id).then(({ data }) => { snmpLatest.value = data })
    }
  }
}

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

// --- Interfaces ---
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

// --- SNMP Monitors ---
function openMonitorForm(m = null) {
  if (m) {
    editMonitorId.value = m.id
    monitorForm.value = { metric_type: m.metric_type, custom_oid: m.custom_oid || '', interface_filter: m.interface_filter || '', interval_sec: m.interval_sec, threshold_warn: m.threshold_warn, active: m.active }
  } else {
    editMonitorId.value = null
    monitorForm.value = defaultMonitorForm()
  }
  showMonitorForm.value = true
}
async function saveMonitor() {
  try {
    const payload = { ...monitorForm.value, custom_oid: monitorForm.value.custom_oid || null, interface_filter: monitorForm.value.interface_filter || null }
    if (editMonitorId.value) {
      const { data } = await updateSnmpMonitor(routerData.value.id, editMonitorId.value, payload)
      const idx = snmpMonitors.value.findIndex((m) => m.id === editMonitorId.value)
      if (idx >= 0) snmpMonitors.value[idx] = data
      toast.success('Monitor atualizado')
    } else {
      const { data } = await createSnmpMonitor(routerData.value.id, payload)
      snmpMonitors.value.push(data)
      toast.success('Monitor adicionado')
    }
    showMonitorForm.value = false
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}
async function delMonitor(id) {
  try {
    await deleteSnmpMonitor(routerData.value.id, id)
    snmpMonitors.value = snmpMonitors.value.filter((m) => m.id !== id)
    toast.success('Monitor removido')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}
async function collectNow() {
  snmpCollecting.value = true
  try {
    const { data } = await collectSnmpNow(routerData.value.id)
    toast.success(`${data.collected} coleta(s) executadas`)
    const [latest, checks] = await Promise.all([getSnmpLatest(routerData.value.id), listChecks()])
    snmpLatest.value = latest.data
    routerChecks.value = checks.data.filter((c) => c.router_id == route.params.id)
    await loadHistory(snmpMonitors.value)
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro ao coletar')
  } finally {
    snmpCollecting.value = false
  }
}

// --- Helpers display ---
function latestFor(type, iface = null) {
  return snmpLatest.value.filter((m) => {
    const typeMatch = type === 'TRAFFIC' ? (m.metric_type === 'TRAFFIC_IN' || m.metric_type === 'TRAFFIC_OUT') : m.metric_type === type
    const ifaceMatch = iface ? m.interface_name === iface : true
    return typeMatch && ifaceMatch
  })
}
function fmtBytes(bps) {
  if (bps == null) return '—'
  if (bps >= 1_000_000) return (bps / 1_000_000).toFixed(1) + ' MB/s'
  if (bps >= 1000) return (bps / 1000).toFixed(1) + ' KB/s'
  return Math.round(bps) + ' B/s'
}
function fmtVal(m) {
  if (!m) return '—'
  if (m.unit === 'bytes_sec') return fmtBytes(m.value)
  if (m.unit === 'percent') return m.value + '%'
  if (m.unit === 'count') return m.value + ' clientes'
  if (m.unit === 'seconds') return fmtUptime(m.value)
  return m.value
}
function fmtUptime(secs) {
  const d = Math.floor(secs / 86400), h = Math.floor((secs % 86400) / 3600), m = Math.floor((secs % 3600) / 60)
  const parts = []
  if (d) parts.push(`${d}d`)
  if (h || parts.length) parts.push(`${h}h`)
  parts.push(`${m}m`)
  return parts.join(' ')
}
function metricLabel(type) {
  return METRIC_TYPES.find((t) => t.value === type)?.label ?? type
}
function valColor(m) {
  if (!m || m.unit === 'bytes_sec' || m.unit === 'count' || m.unit === 'seconds') return 'text-brand-700'
  if (m.unit === 'percent') {
    if (m.value >= 90) return 'text-red-600'
    if (m.value >= 75) return 'text-amber-600'
    return 'text-emerald-600'
  }
  return 'text-gray-700'
}
function sparkValues(type, interface_name = null) {
  const key = type === 'TRAFFIC' ? 'TRAFFIC_IN' : type
  const history = snmpHistory.value[key] || []
  return history
    .filter((h) => !interface_name || h.interface_name === interface_name)
    .slice(-40)
    .map((h) => h.value)
}
function sparkValuesOut(interface_name = null) {
  const history = snmpHistory.value['TRAFFIC_OUT'] || []
  return history
    .filter((h) => !interface_name || h.interface_name === interface_name)
    .slice(-40)
    .map((h) => h.value)
}
function activeMonitors() {
  return snmpMonitors.value.filter((m) => m.active)
}
function uniqueInterfaces(type) {
  const metrics = snmpLatest.value.filter((m) => m.metric_type === 'TRAFFIC_IN' || m.metric_type === 'TRAFFIC_OUT')
  const seen = new Set(metrics.map((m) => m.interface_name).filter(Boolean))
  return [...seen]
}

function snmpChecks() {
  return routerChecks.value.filter((c) => c.check_type === 'SNMP')
}
function otherChecks() {
  return routerChecks.value.filter((c) => c.check_type !== 'SNMP')
}
function checkStatusClass(status) {
  if (status === 'OK') return 'text-emerald-600'
  if (status === 'FAIL' || status === 'ERROR') return 'text-red-600'
  return 'text-gray-400'
}
function checkStatusIcon(status) {
  if (status === 'OK') return CheckCircle
  if (status === 'FAIL' || status === 'ERROR') return XCircle
  return HelpCircle
}

// --- Descoberta SNMP ---
// --- WiFi Networks ---
function openWifiForm(wn = null) {
  if (wn) {
    editWifiId.value = wn.id
    wifiForm.value = { ssid: wn.ssid, band: wn.band || '', password: wn.password || '', vlan: wn.vlan || '', notes: wn.notes || '', active: wn.active }
  } else {
    editWifiId.value = null
    wifiForm.value = defaultWifiForm()
  }
  showWifiForm.value = true
}

async function saveWifi() {
  try {
    const payload = { ...wifiForm.value }
    if (editWifiId.value) {
      const { data } = await updateWifiNetwork(routerData.value.id, editWifiId.value, payload)
      const idx = wifiNetworks.value.findIndex(w => w.id === editWifiId.value)
      if (idx >= 0) wifiNetworks.value[idx] = data
      toast.success('Rede WiFi atualizada')
    } else {
      const { data } = await createWifiNetwork(routerData.value.id, payload)
      wifiNetworks.value.push(data)
      toast.success('Rede WiFi adicionada')
    }
    showWifiForm.value = false
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function deleteWifi(id) {
  if (!confirm('Remover esta rede WiFi?')) return
  try {
    await deleteWifiNetwork(routerData.value.id, id)
    wifiNetworks.value = wifiNetworks.value.filter(w => w.id !== id)
    toast.success('Rede removida')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro')
  }
}

async function openWifiCopyModal() {
  wifiCopyTargetId.value = null
  showWifiCopyModal.value = true
  if (!allRouters.value.length) {
    const { data } = await list()
    allRouters.value = data.filter(r => r.id !== routerData.value.id)
  }
}

async function executeWifiCopy() {
  if (!wifiCopyTargetId.value) return
  wifiCopying.value = true
  try {
    const { data } = await copyWifiNetworks(routerData.value.id, wifiCopyTargetId.value)
    toast.success(`${data.copied} rede(s) copiada(s)` + (data.skipped ? `, ${data.skipped} já existia(m)` : ''))
    showWifiCopyModal.value = false
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro ao copiar')
  } finally {
    wifiCopying.value = false
  }
}

async function openCopyModal() {
  copyTargetId.value = null
  showCopyModal.value = true
  if (!allRouters.value.length) {
    const { data } = await list()
    allRouters.value = data.filter(r => r.id !== routerData.value.id)
  }
}

async function executeCopy() {
  if (!copyTargetId.value) return
  copying.value = true
  try {
    const { data } = await copySnmpMonitors(routerData.value.id, copyTargetId.value)
    toast.success(`${data.copied} monitor(es) copiado(s)` + (data.skipped ? `, ${data.skipped} já existia(m)` : ''))
    showCopyModal.value = false
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro ao copiar monitores')
  } finally {
    copying.value = false
  }
}

async function runDiscovery() {
  snmpDiscovering.value = true
  snmpDiscovery.value = null
  showDiscovery.value = true
  try {
    const { data } = await discoverSnmp(routerData.value.id)
    snmpDiscovery.value = data
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro na descoberta')
    showDiscovery.value = false
  } finally {
    snmpDiscovering.value = false
  }
}

const filteredDiscovery = computed(() => {
  if (!snmpDiscovery.value?.results) return {}
  const q = discoveryFilter.value.toLowerCase()
  const filtered = snmpDiscovery.value.results.filter(
    (r) => !q || r.name.toLowerCase().includes(q) || r.value.toLowerCase().includes(q) || r.category.toLowerCase().includes(q) || r.hint.toLowerCase().includes(q) || r.oid.includes(q)
  )
  const cats = {}
  filtered.forEach((r) => {
    cats[r.category] = cats[r.category] || []
    cats[r.category].push(r)
  })
  return cats
})

function copyOid(oid) {
  navigator.clipboard.writeText(oid)
  toast.success('OID copiado')
}
</script>

<template>
  <div>
    <router-link to="/routers" class="text-brand-500 hover:underline mb-4 inline-block">← Roteadores</router-link>
    <div v-if="routerData" class="space-y-6">
      <!-- Dados básicos -->
      <div class="bg-white rounded-lg shadow-sm border p-6">
        <h2 class="text-xl font-bold mb-4">{{ isNew ? 'Novo Aparelho' : routerData.name }}</h2>

        <!-- Identificação -->
        <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Identificação</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mb-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">Nome</label>
            <input v-model="routerData.name" class="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Tipo de Aparelho</label>
            <select v-model="routerData.device_type" class="w-full border rounded px-3 py-2 text-sm">
              <option value="ROUTER">Roteador</option>
              <option value="WIFI_AP">Access Point / WiFi</option>
              <option value="SWITCH">Switch</option>
              <option value="FIREWALL">Firewall</option>
              <option value="OTHER">Outro</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Marca</label>
            <input v-model="routerData.brand" class="w-full border rounded px-3 py-2 text-sm" placeholder="MikroTik, Ubiquiti, TP-Link..." />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Modelo</label>
            <input v-model="routerData.model" class="w-full border rounded px-3 py-2 text-sm" placeholder="RB3011, UAP-AC-PRO..." />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">Localização</label>
            <input v-model="routerData.location" class="w-full border rounded px-3 py-2 text-sm" placeholder="Sala de TI, Rack 2..." />
          </div>
        </div>
        <div class="flex gap-6 mb-4">
          <label class="flex items-center gap-2 text-sm cursor-pointer"><input v-model="routerData.has_vpn" type="checkbox" /> Possui VPN</label>
        </div>

        <!-- Rede -->
        <div class="border-t pt-4 mb-4">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Configurações de Rede</p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl">
            <div>
              <label class="block text-xs text-gray-500 mb-1">Gateway</label>
              <input v-model="routerData.gateway" class="w-full border rounded px-3 py-1.5 text-sm" placeholder="192.168.0.1" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">DNS Primário</label>
              <input v-model="routerData.dns_primary" class="w-full border rounded px-3 py-1.5 text-sm" placeholder="8.8.8.8" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">DNS Secundário</label>
              <input v-model="routerData.dns_secondary" class="w-full border rounded px-3 py-1.5 text-sm" placeholder="8.8.4.4" />
            </div>
          </div>
        </div>


        <!-- SNMP -->
        <div class="border-t pt-4">
          <label class="flex items-center gap-2 cursor-pointer text-sm font-medium mb-3">
            <input v-model="routerData.snmp_enabled" type="checkbox" /> Habilitar SNMP
          </label>
          <div v-if="routerData.snmp_enabled" class="grid grid-cols-2 sm:grid-cols-3 gap-3 max-w-xl">
            <div>
              <label class="block text-xs text-gray-500 mb-1">Community</label>
              <input v-model="routerData.snmp_community" class="w-full border rounded px-3 py-1.5 text-sm" placeholder="public" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Porta</label>
              <input v-model.number="routerData.snmp_port" type="number" class="w-full border rounded px-3 py-1.5 text-sm" />
            </div>
          </div>
        </div>

        <button @click="save" class="mt-4 px-4 py-2 bg-brand-500 text-white rounded-lg w-fit text-sm">Salvar</button>
      </div>

      <!-- Interfaces -->
      <div v-if="!isNew" class="bg-white rounded-lg shadow-sm border p-6">
        <h3 class="font-medium mb-2">Interfaces de Rede</h3>
        <p class="text-sm text-gray-500 mb-3">IP público (WAN), IP privado (LAN), interfaces VPN</p>
        <div class="grid gap-2 max-w-lg mb-4 p-3 bg-gray-50 rounded-lg">
          <div class="flex gap-2 flex-wrap">
            <input v-model="newInt.ip_address" placeholder="IP (ex: 192.168.0.1)" class="border rounded px-3 py-2 flex-1 min-w-[140px] text-sm" />
            <input v-model="newInt.interface_name" placeholder="WAN1, LAN..." class="border rounded px-3 py-2 w-24 text-sm" />
            <input v-model="newInt.subnet_mask" placeholder="/24" class="border rounded px-3 py-2 w-16 text-sm" />
          </div>
          <div class="flex gap-4 items-center flex-wrap text-sm">
            <label class="flex items-center gap-1"><input v-model="newInt.is_external" type="checkbox" /> Público</label>
            <label class="flex items-center gap-1"><input v-model="newInt.is_primary" type="checkbox" /> LAN</label>
            <label class="flex items-center gap-1"><input v-model="newInt.is_vpn" type="checkbox" /> VPN</label>
            <button @click="addInt" class="px-3 py-1 bg-brand-500 text-white rounded text-sm">{{ editInt ? 'Salvar' : 'Adicionar' }}</button>
            <button v-if="editInt" @click="cancelEdit" class="px-3 py-1 border rounded text-sm">Cancelar</button>
          </div>
        </div>
        <ul class="divide-y text-sm">
          <li v-for="i in interfaces" :key="i.id" class="flex justify-between py-1.5 items-center">
            <span>
              <span class="font-mono">{{ i.ip_address }}</span>
              <span v-if="i.subnet_mask" class="text-gray-400">{{ i.subnet_mask }}</span>
              <span v-if="i.interface_name" class="text-gray-400 ml-1">({{ i.interface_name }})</span>
              <span v-if="i.is_external" class="text-amber-600 text-xs ml-1">público</span>
              <span v-if="i.is_primary" class="text-emerald-600 text-xs ml-1">LAN</span>
              <span v-if="i.is_vpn" class="text-brand-600 text-xs ml-1">VPN</span>
            </span>
            <div class="flex gap-2">
              <button @click="openEditInt(i)" class="text-brand-500 hover:underline text-xs">Editar</button>
              <button @click="delInt(i.id)" class="text-red-500 hover:underline text-xs">Remover</button>
            </div>
          </li>
        </ul>
      </div>

      <!-- Redes WiFi -->
      <div v-if="!isNew && routerData.device_type !== 'ROUTER'" class="bg-white rounded-lg shadow-sm border p-6">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="font-medium">Redes WiFi</h3>
            <p class="text-xs text-gray-400 mt-0.5">SSIDs configuradas neste aparelho. Pode ter múltiplas redes (2.4GHz, 5GHz, redes de convidados, etc.)</p>
          </div>
          <div class="flex gap-2">
            <button v-if="wifiNetworks.length" @click="openWifiCopyModal" class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-sm">Copiar para...</button>
            <button @click="openWifiForm()" class="flex items-center gap-1 px-3 py-1.5 bg-brand-500 hover:bg-brand-600 text-white rounded text-sm">
              <Plus class="w-4 h-4" /> Rede
            </button>
          </div>
        </div>

        <!-- Formulário -->
        <div v-if="showWifiForm" class="bg-gray-50 rounded-lg p-4 mb-4 space-y-3">
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="block text-xs text-gray-500 mb-1">SSID <span class="text-red-500">*</span></label>
              <input v-model="wifiForm.ssid" class="w-full border rounded px-3 py-1.5 text-sm" placeholder="Nome da rede" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Banda</label>
              <select v-model="wifiForm.band" class="w-full border rounded px-3 py-1.5 text-sm">
                <option value="">—</option>
                <option value="2.4GHz">2.4 GHz</option>
                <option value="5GHz">5 GHz</option>
                <option value="6GHz">6 GHz</option>
                <option value="Dual">Dual Band</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Senha</label>
              <input v-model="wifiForm.password" type="password" class="w-full border rounded px-3 py-1.5 text-sm" placeholder="••••••••" autocomplete="new-password" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">VLAN</label>
              <input v-model="wifiForm.vlan" class="w-full border rounded px-3 py-1.5 text-sm" placeholder="ex: 10" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Observações</label>
              <input v-model="wifiForm.notes" class="w-full border rounded px-3 py-1.5 text-sm" placeholder="Rede de convidados..." />
            </div>
          </div>
          <div class="flex gap-2">
            <button @click="saveWifi" class="px-3 py-1.5 bg-brand-500 text-white rounded text-sm">Salvar</button>
            <button @click="showWifiForm = false" class="px-3 py-1.5 border rounded text-sm">Cancelar</button>
          </div>
        </div>

        <!-- Lista -->
        <div v-if="!wifiNetworks.length && !showWifiForm" class="text-sm text-gray-400">Nenhuma rede cadastrada.</div>
        <div class="grid gap-2">
          <div v-for="wn in wifiNetworks" :key="wn.id" class="p-3 border rounded-lg">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <p class="font-medium text-sm">
                  {{ wn.ssid }}
                  <span v-if="wn.band" class="ml-1 text-xs bg-brand-50 text-brand-700 px-1.5 py-0.5 rounded">{{ wn.band }}</span>
                  <span v-if="wn.vlan" class="ml-1 text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">VLAN {{ wn.vlan }}</span>
                </p>
                <p v-if="wn.notes" class="text-xs text-gray-400 mt-0.5">{{ wn.notes }}</p>
                <!-- Senha -->
                <div v-if="wn.password" class="flex items-center gap-2 mt-1.5">
                  <span class="font-mono text-sm text-gray-700">{{ visiblePasswords.has(wn.id) ? wn.password : '••••••••' }}</span>
                  <button @click="togglePassword(wn.id)" class="text-gray-400 hover:text-gray-600" :title="visiblePasswords.has(wn.id) ? 'Ocultar' : 'Ver senha'">
                    <EyeOff v-if="visiblePasswords.has(wn.id)" class="w-4 h-4" />
                    <Eye v-else class="w-4 h-4" />
                  </button>
                  <button @click="showQr(wn)" class="text-gray-400 hover:text-brand-600" title="Gerar QR Code para conectar">
                    <QrCode class="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div class="flex gap-2 shrink-0 text-xs">
                <button @click="openWifiForm(wn)" class="text-brand-500 hover:underline">Editar</button>
                <button @click="deleteWifi(wn.id)" class="text-red-500 hover:underline">Remover</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Status de Monitoramento do Roteador -->
      <div v-if="!isNew && routerChecks.length" class="bg-white rounded-lg shadow-sm border p-6">
        <h3 class="font-medium mb-3">Status dos Checks</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div v-for="c in routerChecks" :key="c.id" class="flex items-center gap-3 p-3 border rounded-lg">
            <component :is="checkStatusIcon(c.last_status)" class="w-5 h-5 flex-shrink-0" :class="checkStatusClass(c.last_status)" />
            <div class="min-w-0">
              <p class="text-sm font-medium truncate">{{ c.name }}</p>
              <p class="text-xs text-gray-400">{{ c.check_type }} <span v-if="c.last_checked_at">· {{ fmtTime(c.last_checked_at) }}</span></p>
              <p v-if="c.last_message && c.last_status !== 'OK'" class="text-xs text-red-600 truncate">{{ c.last_message }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Monitores SNMP -->
      <div v-if="!isNew && routerData.snmp_enabled" class="bg-white rounded-lg shadow-sm border p-6">
        <div class="flex items-center justify-between mb-1">
          <div>
            <h3 class="font-medium">Monitores SNMP</h3>
            <p class="text-xs text-gray-400 mt-0.5">O scheduler coleta automaticamente. Com "Alerta quando" configurado, um Health Check é criado automaticamente.</p>
          </div>
          <div class="flex gap-2">
            <button @click="collectNow" :disabled="snmpCollecting" class="flex items-center gap-1 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-sm disabled:opacity-50">
              <RefreshCw class="w-4 h-4" :class="snmpCollecting ? 'animate-spin' : ''" />
              {{ snmpCollecting ? 'Coletando...' : 'Coletar agora' }}
            </button>
            <button @click="openCopyModal" :disabled="!snmpMonitors.length" class="flex items-center gap-1 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-sm disabled:opacity-40" title="Copiar monitores para outro roteador">
              Copiar para...
            </button>
            <button @click="openMonitorForm()" class="flex items-center gap-1 px-3 py-1.5 bg-brand-500 hover:bg-brand-600 text-white rounded text-sm">
              <Plus class="w-4 h-4" /> Monitor
            </button>
          </div>
        </div>

        <!-- Formulário de monitor -->
        <div v-if="showMonitorForm" class="bg-gray-50 rounded-lg p-4 mb-4 space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs text-gray-500 mb-1">Tipo de Métrica</label>
              <select v-model="monitorForm.metric_type" :disabled="!!editMonitorId" class="w-full border rounded px-2 py-1.5 text-sm disabled:opacity-60">
                <option v-for="t in METRIC_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
              <p class="text-xs text-gray-400 mt-1">{{ METRIC_TYPES.find(t => t.value === monitorForm.metric_type)?.hint }}</p>
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Intervalo (seg)</label>
              <input v-model.number="monitorForm.interval_sec" type="number" class="w-full border rounded px-2 py-1.5 text-sm" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs text-gray-500 mb-1">
                OID Customizado
                <span v-if="['TRAFFIC_IN','TRAFFIC_OUT'].includes(monitorForm.metric_type)" class="text-red-500">*</span>
                <span v-else>(opcional)</span>
              </label>
              <input v-model="monitorForm.custom_oid" class="w-full border rounded px-2 py-1.5 text-sm font-mono" placeholder="1.3.6.1.2.1..." />
              <p v-if="['TRAFFIC_IN','TRAFFIC_OUT'].includes(monitorForm.metric_type)" class="text-xs text-amber-600 mt-1">
                Cole o OID completo da interface (ex: <span class="font-mono">1.3.6.1.2.1.2.2.1.10.1</span>).
                Use "Descobrir OIDs" para encontrar.
              </p>
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">
                {{ ['TRAFFIC_IN','TRAFFIC_OUT'].includes(monitorForm.metric_type) ? 'Nome/Label da Interface' : 'Filtro de Interface (opcional)' }}
              </label>
              <input v-model="monitorForm.interface_filter" class="w-full border rounded px-2 py-1.5 text-sm"
                :placeholder="['TRAFFIC_IN','TRAFFIC_OUT'].includes(monitorForm.metric_type) ? 'ex: Internet, ether1, WAN' : 'ex: eth0, wlan, ether'" />
              <p class="text-xs text-gray-400 mt-1">
                {{ ['TRAFFIC_IN','TRAFFIC_OUT'].includes(monitorForm.metric_type) ? 'Nome exibido nos gráficos' : 'Filtra apenas interfaces que contenham este texto' }}
              </p>
            </div>
          </div>

          <div>
            <label class="block text-xs text-gray-500 mb-1">Alerta quando >= (opcional)</label>
            <input v-model.number="monitorForm.threshold_warn" type="number" class="w-full border rounded px-2 py-1.5 text-sm max-w-xs"
              :placeholder="['CPU','MEMORY'].includes(monitorForm.metric_type) ? 'ex: 90 (%)' : ['WIFI_CLIENTS'].includes(monitorForm.metric_type) ? 'ex: 50 (clientes)' : 'ex: 10000000 (bytes/s)'" />
          </div>

          <label class="flex items-center gap-2 text-sm cursor-pointer"><input v-model="monitorForm.active" type="checkbox" /> Ativo</label>
          <div class="flex gap-2">
            <button @click="saveMonitor" class="px-3 py-1.5 bg-brand-500 text-white rounded text-sm">{{ editMonitorId ? 'Salvar' : 'Adicionar' }}</button>
            <button @click="showMonitorForm = false" class="px-3 py-1.5 border rounded text-sm">Cancelar</button>
          </div>
        </div>

        <!-- Lista de monitores -->
        <div v-if="!snmpMonitors.length" class="text-sm text-gray-400">Nenhum monitor configurado. Clique em "Monitor" para adicionar.</div>
        <div v-else class="space-y-2">
          <div v-for="m in snmpMonitors" :key="m.id" class="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <span class="font-medium text-sm">{{ metricLabel(m.metric_type) }}</span>
              <span v-if="m.interface_filter" class="text-xs text-gray-400 ml-2">[{{ m.interface_filter }}]</span>
              <span v-if="m.custom_oid" class="text-xs text-gray-400 ml-2 font-mono">{{ m.custom_oid }}</span>
              <span class="text-xs text-gray-400 ml-2">a cada {{ m.interval_sec }}s</span>
              <span v-if="m.threshold_warn" class="text-xs text-amber-600 ml-2">alerta >= {{ m.threshold_warn }}</span>
              <span v-if="!m.active" class="text-xs text-gray-400 ml-2">(inativo)</span>
            </div>
            <div class="flex gap-2">
              <button @click="openMonitorForm(m)" class="text-brand-500 hover:underline text-xs">Editar</button>
              <button @click="delMonitor(m.id)" class="text-red-500 hover:underline text-xs">Remover</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Cards de métricas coletadas -->
      <div v-if="!isNew && routerData.snmp_enabled && snmpLatest.length" class="bg-white rounded-lg shadow-sm border p-6">
        <h3 class="font-medium mb-4">Métricas em Tempo Real</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">

          <!-- CPU -->
          <template v-for="m in snmpLatest.filter(x => x.metric_type === 'CPU')" :key="'cpu-' + m.metric_type">
            <div class="border rounded-lg p-4">
              <p class="text-xs text-gray-500 mb-1">CPU</p>
              <p class="text-2xl font-bold" :class="valColor(m)">{{ fmtVal(m) }}</p>
              <div class="mt-2">
                <SparkLine :values="sparkValues('CPU')" color="#6366f1" :width="160" :height="36" />
              </div>
              <p class="text-xs text-gray-400 mt-1">{{ fmtTime(m.collected_at) }}</p>
              </div>
          </template>

          <!-- Memória -->
          <template v-for="m in snmpLatest.filter(x => x.metric_type === 'MEMORY')" :key="'mem-' + m.metric_type">
            <div class="border rounded-lg p-4">
              <p class="text-xs text-gray-500 mb-1">Memória</p>
              <p class="text-2xl font-bold" :class="valColor(m)">{{ fmtVal(m) }}</p>
              <div class="mt-2">
                <div class="w-full bg-gray-100 rounded-full h-2">
                  <div class="h-2 rounded-full transition-all" :class="m.value >= 90 ? 'bg-red-500' : m.value >= 75 ? 'bg-amber-500' : 'bg-emerald-500'" :style="{ width: m.value + '%' }" />
                </div>
              </div>
              <p class="text-xs text-gray-400 mt-1">{{ fmtTime(m.collected_at) }}</p>
            </div>
          </template>

          <!-- Clientes WiFi -->
          <template v-for="m in snmpLatest.filter(x => x.metric_type === 'WIFI_CLIENTS')" :key="'wifi-' + m.metric_type">
            <div class="border rounded-lg p-4">
              <p class="text-xs text-gray-500 mb-1">Clientes WiFi</p>
              <p class="text-2xl font-bold text-brand-700">{{ Math.round(m.value) }}</p>
              <div class="mt-2">
                <SparkLine :values="sparkValues('WIFI_CLIENTS')" color="#10b981" :width="160" :height="36" />
              </div>
              <p class="text-xs text-gray-400 mt-1">{{ fmtTime(m.collected_at) }}</p>
            </div>
          </template>

          <!-- Uptime -->
          <template v-for="m in snmpLatest.filter(x => x.metric_type === 'UPTIME')" :key="'up-' + m.metric_type">
            <div class="border rounded-lg p-4">
              <p class="text-xs text-gray-500 mb-1">Uptime</p>
              <p class="text-2xl font-bold text-emerald-600">{{ fmtUptime(m.value) }}</p>
              <p class="text-xs text-gray-400 mt-1">{{ fmtTime(m.collected_at) }}</p>
            </div>
          </template>

          <!-- Tráfego por interface -->
          <template v-for="iface in uniqueInterfaces('TRAFFIC')" :key="'traffic-' + iface">
            <div class="border rounded-lg p-4 col-span-1 sm:col-span-2">
              <p class="text-xs text-gray-500 mb-2">Tráfego — <span class="font-mono font-semibold">{{ iface }}</span></p>
              <div class="grid grid-cols-2 gap-4">
                <!-- IN -->
                <div>
                  <p class="text-xs text-gray-400 mb-1">↓ Download</p>
                  <p class="text-xl font-bold text-emerald-600">
                    {{ fmtBytes(snmpLatest.find(x => x.metric_type === 'TRAFFIC_IN' && x.interface_name === iface)?.value) }}
                  </p>
                  <SparkLine :values="sparkValues('TRAFFIC_IN', iface)" color="#10b981" :width="180" :height="40" class="mt-2" />
                </div>
                <!-- OUT -->
                <div>
                  <p class="text-xs text-gray-400 mb-1">↑ Upload</p>
                  <p class="text-xl font-bold text-orange-500">
                    {{ fmtBytes(snmpLatest.find(x => x.metric_type === 'TRAFFIC_OUT' && x.interface_name === iface)?.value) }}
                  </p>
                  <SparkLine :values="sparkValuesOut(iface)" color="#f97316" :width="180" :height="40" class="mt-2" />
                </div>
              </div>
              <p class="text-xs text-gray-400 mt-2">últimas 24h</p>
            </div>
          </template>
        </div>
      </div>

      <!-- Descoberta SNMP -->
      <div v-if="!isNew && routerData.snmp_enabled" class="bg-white rounded-lg shadow-sm border p-6">
        <div class="flex items-center justify-between mb-2">
          <div>
            <h3 class="font-medium">Descoberta SNMP</h3>
            <p class="text-xs text-gray-400 mt-0.5">Faz um WALK no aparelho e mostra todos os OIDs respondidos com nome e categoria. Use para descobrir o que o aparelho suporta e copiar o OID para configurar um monitor.</p>
          </div>
          <button @click="runDiscovery" :disabled="snmpDiscovering" class="flex items-center gap-1.5 px-4 py-2 bg-gray-700 hover:bg-gray-800 text-white rounded-lg text-sm disabled:opacity-50 shrink-0 ml-4">
            <RefreshCw class="w-4 h-4" :class="snmpDiscovering ? 'animate-spin' : ''" />
            {{ snmpDiscovering ? 'Buscando...' : 'Descobrir OIDs' }}
          </button>
        </div>

        <div v-if="showDiscovery">
          <div v-if="snmpDiscovering" class="py-8 text-center text-gray-400 text-sm">Fazendo WALK SNMP no aparelho, aguarde...</div>

          <div v-else-if="snmpDiscovery">
            <div v-if="snmpDiscovery.error" class="p-3 bg-red-50 text-red-700 rounded text-sm">{{ snmpDiscovery.error }}</div>
            <div v-else>
              <div class="flex items-center gap-3 mb-4 mt-3">
                <span class="text-sm text-gray-500">{{ snmpDiscovery.total }} OIDs encontrados em <strong>{{ snmpDiscovery.host }}</strong></span>
                <input v-model="discoveryFilter" placeholder="Filtrar por nome, valor, categoria..." class="flex-1 border rounded px-3 py-1.5 text-sm" />
              </div>

              <div v-for="(entries, cat) in filteredDiscovery" :key="cat" class="mb-5">
                <h4 class="text-xs font-semibold uppercase text-gray-500 tracking-wide mb-2 flex items-center gap-2">
                  {{ cat }}
                  <span class="text-gray-300 font-normal normal-case">{{ entries.length }} entradas</span>
                </h4>
                <div class="border rounded-lg overflow-hidden">
                  <table class="w-full text-sm">
                    <thead class="bg-gray-50 text-xs text-gray-500">
                      <tr>
                        <th class="text-left px-3 py-2 w-48">Nome</th>
                        <th class="text-left px-3 py-2">Valor</th>
                        <th class="text-left px-3 py-2 hidden md:table-cell">Dica de uso</th>
                        <th class="px-3 py-2 w-24"></th>
                      </tr>
                    </thead>
                    <tbody class="divide-y">
                      <tr v-for="e in entries" :key="e.oid" class="hover:bg-gray-50">
                        <td class="px-3 py-2">
                          <p class="font-medium text-gray-800">{{ e.name }}</p>
                          <p class="text-xs text-gray-400 font-mono">{{ e.oid }}</p>
                        </td>
                        <td class="px-3 py-2">
                          <span class="font-mono text-brand-700 break-all">{{ e.value }}</span>
                        </td>
                        <td class="px-3 py-2 text-gray-500 text-xs hidden md:table-cell">{{ e.hint }}</td>
                        <td class="px-3 py-2 text-right">
                          <button @click="copyOid(e.oid)" class="text-xs text-brand-500 hover:underline whitespace-nowrap">Copiar OID</button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <p v-if="Object.keys(filteredDiscovery).length === 0" class="text-sm text-gray-400 py-4 text-center">Nenhum resultado para "{{ discoveryFilter }}"</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal: Copiar monitores para outro roteador -->
  <div v-if="showCopyModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showCopyModal = false">
    <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm">
      <h3 class="font-semibold text-gray-800 mb-1">Copiar monitores SNMP</h3>
      <p class="text-xs text-gray-500 mb-4">
        Copia os {{ snmpMonitors.length }} monitor(es) de <strong>{{ routerData.name }}</strong> para o roteador selecionado.
        Monitores já existentes no destino serão ignorados.
      </p>

      <label class="block text-xs font-medium text-gray-700 mb-1">Roteador destino</label>
      <select v-model="copyTargetId" class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 mb-4">
        <option :value="null" disabled>Selecione...</option>
        <option v-for="r in allRouters" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>

      <div class="flex gap-2 justify-end">
        <button @click="showCopyModal = false" class="px-4 py-2 text-sm rounded-lg bg-gray-100 hover:bg-gray-200">Cancelar</button>
        <button @click="executeCopy" :disabled="!copyTargetId || copying" class="px-4 py-2 text-sm rounded-lg bg-brand-500 hover:bg-brand-600 text-white disabled:opacity-50">
          {{ copying ? 'Copiando...' : 'Copiar' }}
        </button>
      </div>
    </div>
  </div>

  <!-- Modal: Copiar redes WiFi -->
  <div v-if="showWifiCopyModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showWifiCopyModal = false">
    <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm">
      <h3 class="font-semibold text-gray-800 mb-1">Copiar redes WiFi</h3>
      <p class="text-xs text-gray-500 mb-4">
        Copia as {{ wifiNetworks.length }} rede(s) de <strong>{{ routerData.name }}</strong> para outro aparelho.
        SSIDs já existentes no destino serão ignorados.
      </p>
      <label class="block text-xs font-medium text-gray-700 mb-1">Aparelho destino</label>
      <select v-model="wifiCopyTargetId" class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 mb-4">
        <option :value="null" disabled>Selecione...</option>
        <option v-for="r in allRouters" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>
      <div class="flex gap-2 justify-end">
        <button @click="showWifiCopyModal = false" class="px-4 py-2 text-sm rounded-lg bg-gray-100 hover:bg-gray-200">Cancelar</button>
        <button @click="executeWifiCopy" :disabled="!wifiCopyTargetId || wifiCopying" class="px-4 py-2 text-sm rounded-lg bg-brand-500 hover:bg-brand-600 text-white disabled:opacity-50">
          {{ wifiCopying ? 'Copiando...' : 'Copiar' }}
        </button>
      </div>
    </div>
  </div>

  <!-- Modal: QR Code WiFi -->
  <div v-if="qrModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="qrModal = null">
    <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-xs text-center">
      <h3 class="font-semibold text-gray-800 mb-1">{{ qrModal.ssid }}</h3>
      <p class="text-xs text-gray-400 mb-4">Escaneie para conectar automaticamente</p>
      <img :src="qrModal.dataUrl" alt="QR Code WiFi" class="mx-auto rounded-lg" />
      <p class="text-xs text-gray-500 mt-3 font-mono break-all">{{ qrModal.password }}</p>
      <button @click="qrModal = null" class="mt-4 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm w-full">Fechar</button>
    </div>
  </div>
</template>
