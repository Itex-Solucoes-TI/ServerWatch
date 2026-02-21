<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import { getGraph, savePositions, deleteLink, getGenericDevice, createGenericDevice, updateGenericDevice, deleteGenericDevice } from '../api/topology'
import AddLinkModal from '../components/topology/AddLinkModal.vue'
import ServerNode from '../components/topology/ServerNode.vue'
import RouterNode from '../components/topology/RouterNode.vue'
import GenericNode from '../components/topology/GenericNode.vue'
import { toast } from 'vue-sonner'
import { X, Video, Eye, EyeOff } from 'lucide-vue-next'

const auth = useAuthStore()

// Evento de câmera vindo do GenericNode
function handleNodeEvents(events) {
  return {
    openCamera: (generic) => openCameraPip(generic),
  }
}

const nodeTypes = {
  server: ServerNode,
  router: RouterNode,
  generic: GenericNode,
}

const nodes = ref([])
const edges = ref([])
const loading = ref(false)
const showAddLink = ref(false)

// Modal de dispositivo genérico
const showDeviceModal = ref(false)
const editingDeviceId = ref(null)
const showPassword = ref(false)
const deviceForm = ref(defaultDeviceForm())
const savingDevice = ref(false)

function defaultDeviceForm() {
  return { name: '', device_type: 'OTHER', ip_address: '', notes: '', rtsp_username: '', rtsp_password: '', rtsp_port: 554, rtsp_channel: 1, rtsp_subtype: 0 }
}

function rtspPreview(f) {
  const user = f.rtsp_username || 'user'
  const ip = f.ip_address || 'ip'
  const port = f.rtsp_port || 554
  const ch = f.rtsp_channel || 1
  const sub = f.rtsp_subtype ?? 0
  return `rtsp://${user}:***@${ip}:${port}/cam/realmonitor?channel=${ch}&subtype=${sub}`
}

// PiP câmera
const cameraModal = ref(null) // { id, name, streamUrl }

onMounted(loadGraph)

async function loadGraph() {
  loading.value = true
  try {
    const { data } = await getGraph()
    nodes.value = (data.nodes ?? []).map((n) => ({ ...n, position: n.position }))
    edges.value = data.edges ?? []
  } catch {
    toast.error('Erro ao carregar topologia')
  } finally {
    loading.value = false
  }
}

async function onNodeDragStop(evt) {
  const node = evt?.node || evt?.nodes?.[0]
  if (!node) return

  await nextTick()
  const current = nodes.value.find((n) => n.id === node.id)
  const pos = current?.position ?? node.position ?? { x: 0, y: 0 }

  let nodeType, nodeId
  if (node.id === 'INTERNET') {
    nodeType = 'INTERNET'; nodeId = 0
  } else if (node.id === 'VPN') {
    nodeType = 'VPN'; nodeId = 0
  } else if (node.id.startsWith('G-')) {
    nodeType = 'GENERIC'; nodeId = parseInt(node.id.replace('G-', ''))
  } else {
    const id = parseInt(String(node.id).replace(/^[SR]-/, ''))
    if (isNaN(id)) return
    nodeType = node.type === 'server' ? 'SERVER' : 'ROUTER'
    nodeId = id
  }

  try {
    await savePositions([{ node_type: nodeType, node_id: nodeId, position_x: pos.x ?? 0, position_y: pos.y ?? 0 }])
  } catch {}
}

async function onLinkAdded() {
  await loadGraph()
  toast.success('Ligação criada')
}

async function removeEdge(edge) {
  if (edge.data?.auto) return
  const linkId = edge.data?.linkId
  if (!linkId) { await loadGraph(); return }
  if (!confirm('Remover esta ligação?')) { await loadGraph(); return }
  try {
    await deleteLink(linkId)
    edges.value = edges.value.filter((e) => e.id !== edge.id)
    toast.success('Ligação removida')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro ao remover ligação')
    await loadGraph()
  }
}

async function onEdgesChange(changes) {
  const removals = changes.filter((c) => c.type === 'remove')
  if (!removals.length) return
  if (!auth.isAdmin) { await loadGraph(); return }

  for (const change of removals) {
    const edge = edges.value.find((e) => e.id === change.id)
    if (!edge) continue
    if (edge.data?.auto) { await loadGraph(); return }
    const linkId = edge.data?.linkId
    if (!linkId) { await loadGraph(); return }
    try {
      await deleteLink(linkId)
      edges.value = edges.value.filter((e) => e.id !== edge.id)
      toast.success('Ligação removida')
    } catch (e) {
      toast.error(e.response?.data?.detail ?? 'Erro ao remover ligação')
      await loadGraph()
    }
  }
}

async function openDeviceModal(existing = null) {
  showPassword.value = false
  if (existing?.id) {
    editingDeviceId.value = existing.id
    // Busca dados completos (com credenciais) do backend
    try {
      const { data } = await getGenericDevice(existing.id)
      deviceForm.value = { ...defaultDeviceForm(), ...data }
    } catch {
      deviceForm.value = { ...defaultDeviceForm(), ...existing }
    }
  } else {
    editingDeviceId.value = null
    deviceForm.value = defaultDeviceForm()
  }
  showDeviceModal.value = true
}

async function saveDevice() {
  if (!deviceForm.value.name.trim()) return
  savingDevice.value = true
  try {
    const payload = {
      name: deviceForm.value.name.trim(),
      device_type: deviceForm.value.device_type,
      ip_address: deviceForm.value.ip_address || null,
      notes: deviceForm.value.notes || null,
      rtsp_username: deviceForm.value.rtsp_username || null,
      rtsp_password: deviceForm.value.rtsp_password || null,
      rtsp_port: deviceForm.value.rtsp_port || 554,
      rtsp_channel: deviceForm.value.rtsp_channel || 1,
      rtsp_subtype: deviceForm.value.rtsp_subtype ?? 0,
    }
    if (editingDeviceId.value) {
      await updateGenericDevice(editingDeviceId.value, payload)
      toast.success('Dispositivo atualizado')
    } else {
      await createGenericDevice(payload)
      toast.success('Dispositivo adicionado')
    }
    showDeviceModal.value = false
    await loadGraph()
  } catch {
    toast.error('Erro ao salvar dispositivo')
  } finally {
    savingDevice.value = false
  }
}

async function removeGenericNode(nodeId) {
  const id = parseInt(nodeId.replace('G-', ''))
  if (!confirm('Remover este dispositivo da topologia?')) return
  try {
    await deleteGenericDevice(id)
    await loadGraph()
    toast.success('Dispositivo removido')
  } catch {
    toast.error('Erro ao remover dispositivo')
  }
}

// PiP câmera — token passado via query param pois <img> não envia headers
function openCameraPip(generic) {
  const token = encodeURIComponent(auth.token)
  const cid = auth.companyId
  const streamUrl = `/api/topology/devices/${generic.id}/stream?token=${token}&cid=${cid}`
  cameraModal.value = { id: generic.id, name: generic.name, streamUrl }
}

function closeCameraPip() {
  cameraModal.value = null
}

// Captura evento dos nós filhos via VueFlow node-click não funciona facilmente;
// usamos provide/inject ou eventos customizados. Aqui usando window event simples.
function onNodeClick(evt) {
  // handled via emit from GenericNode → não funciona direto no VueFlow com nodeTypes customizados
  // O botão no GenericNode chama $emit('openCamera') mas precisa ser propagado
}

const isCamera = computed(() => deviceForm.value.device_type === 'CAMERA')
const DEVICE_LABELS = { CAMERA: 'Câmera', PRINTER: 'Impressora', OTHER: 'Outro' }
</script>

<template>
  <div>
    <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 mb-4">
      <div class="min-w-0">
        <h2 class="text-xl font-bold text-brand-800">Topologia de Rede</h2>
        <p class="text-sm text-gray-500 mt-1 hidden sm:block">
          Cadastre servidores e roteadores em suas páginas, depois adicione as ligações aqui.
        </p>
      </div>
      <div v-if="auth.isOperator" class="flex gap-2 shrink-0">
        <button
          @click="openDeviceModal()"
          class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm"
        >
          + Dispositivo
        </button>
        <button
          v-if="nodes.length >= 2"
          @click="showAddLink = true"
          class="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm"
        >
          + Ligação
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-gray-500">Carregando...</div>
    <div v-else class="h-[min(70vh,500px)] sm:h-[600px] border rounded-lg bg-white relative">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :node-types="nodeTypes"
        :fit-view-on-init="true"
        @node-drag-stop="onNodeDragStop"
        @edges-change="onEdgesChange"
      >
        <Background />
        <Controls />
        <template #node-generic="nodeProps">
          <GenericNode v-bind="nodeProps" @openCamera="openCameraPip" />
        </template>
      </VueFlow>
    </div>

    <!-- Legenda de tipos -->
    <div class="mt-3 flex flex-wrap gap-3 text-xs text-gray-500">
      <span class="flex items-center gap-1"><span class="w-3 h-3 rounded border-2 border-amber-300 inline-block"></span> Roteador</span>
      <span class="flex items-center gap-1"><span class="w-3 h-3 rounded border-2 border-blue-300 inline-block"></span> Switch</span>
      <span class="flex items-center gap-1"><span class="w-3 h-3 rounded border-2 border-emerald-300 inline-block"></span> WiFi AP</span>
      <span class="flex items-center gap-1"><span class="w-3 h-3 rounded border-2 border-red-300 inline-block"></span> Firewall</span>
      <span class="flex items-center gap-1"><span class="w-3 h-3 rounded border-2 border-brand-300 inline-block"></span> Servidor</span>
      <span class="flex items-center gap-1"><span class="w-3 h-3 rounded border-2 border-dashed border-gray-400 inline-block"></span> Dispositivo</span>
    </div>

    <!-- Lista de ligações -->
    <div v-if="edges.length" class="mt-4 bg-white rounded-lg border p-4">
      <h3 class="font-medium mb-2">Ligações</h3>
      <div class="flex flex-wrap gap-2">
        <div
          v-for="e in edges"
          :key="e.id"
          class="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded text-sm"
        >
          <span>{{ (nodes.find(n => n.id === e.source)?.data?.label || e.source) }} → {{ (nodes.find(n => n.id === e.target)?.data?.label || e.target) }}</span>
          <span class="text-gray-500">({{ e.data?.linkType || 'LAN' }})</span>
          <span v-if="e.data?.auto" class="text-xs text-brand-600">auto</span>
          <button
            v-if="auth.isAdmin && !e.data?.auto"
            @click="removeEdge(e)"
            class="text-red-500 hover:bg-red-50 rounded p-1"
            title="Remover"
          >×</button>
        </div>
      </div>
    </div>

    <!-- Lista de dispositivos genéricos -->
    <div v-if="nodes.some(n => n.type === 'generic')" class="mt-4 bg-white rounded-lg border p-4">
      <h3 class="font-medium mb-2">Dispositivos</h3>
      <div class="flex flex-wrap gap-2">
        <div
          v-for="n in nodes.filter(n => n.type === 'generic')"
          :key="n.id"
          class="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded text-sm"
        >
          <span>{{ n.data?.label }}</span>
          <span class="text-xs text-gray-400">{{ DEVICE_LABELS[n.data?.device_type] || n.data?.device_type }}</span>
          <button
            v-if="n.data?.device_type === 'CAMERA' && n.data?.generic?.ip_address"
            @click="openCameraPip(n.data.generic)"
            class="text-brand-600 hover:bg-brand-50 rounded p-1"
            title="Ver câmera"
          >
            <Video :size="14" />
          </button>
          <button
            v-if="auth.isOperator"
            @click="openDeviceModal(n.data.generic)"
            class="text-gray-500 hover:bg-gray-100 rounded p-1 text-xs"
            title="Editar"
          >✎</button>
          <button
            v-if="auth.isAdmin"
            @click="removeGenericNode(n.id)"
            class="text-red-500 hover:bg-red-50 rounded p-1"
            title="Remover"
          >×</button>
        </div>
      </div>
    </div>

    <div class="mt-4 bg-brand-50 border border-brand-100 rounded-lg p-4 text-sm text-brand-800">
      <p class="font-medium mb-2">Ligações automáticas por interface</p>
      <ol class="list-decimal list-inside space-y-1 text-gray-700">
        <li><strong>IP público</strong> → Liga ao nó "Internet"</li>
        <li><strong>Rede local (LAN)</strong> → Marque a interface como "Rede local". Liga somente entre dispositivos com LAN na mesma sub-rede</li>
        <li><strong>VPN</strong> → Liga ao nó "VPN"</li>
        <li><strong>Câmeras/Dispositivos</strong> → Ligação automática ao switch ou roteador na mesma sub-rede</li>
        <li>Ligações manuais em "+ Ligação" para links adicionais</li>
      </ol>
    </div>

    <!-- Modal: criar/editar dispositivo genérico -->
    <div v-if="showDeviceModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="showDeviceModal = false">
      <div class="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        <h3 class="font-medium mb-4">{{ editingDeviceId ? 'Editar Dispositivo' : 'Adicionar Dispositivo' }}</h3>
        <form @submit.prevent="saveDevice" class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="block text-sm text-gray-600 mb-1">Nome *</label>
              <input v-model="deviceForm.name" class="w-full border rounded px-3 py-2 text-sm" placeholder="Ex: Câmera Recepção" required />
            </div>
            <div>
              <label class="block text-sm text-gray-600 mb-1">Tipo</label>
              <select v-model="deviceForm.device_type" class="w-full border rounded px-3 py-2 text-sm">
                <option value="CAMERA">Câmera IP</option>
                <option value="PRINTER">Impressora</option>
                <option value="OTHER">Outro</option>
              </select>
            </div>
            <div>
              <label class="block text-sm text-gray-600 mb-1">IP</label>
              <input v-model="deviceForm.ip_address" class="w-full border rounded px-3 py-2 text-sm" placeholder="192.168.1.x" />
            </div>
          </div>

          <!-- Campos específicos de câmera (padrão Intelbras) -->
          <template v-if="isCamera">
            <div class="border-t pt-3 mt-1">
              <p class="text-xs font-medium text-gray-500 uppercase mb-2">Configuração RTSP — Intelbras</p>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-sm text-gray-600 mb-1">Usuário</label>
                  <input
                    v-model="deviceForm.rtsp_username"
                    autocomplete="off"
                    name="camera_user"
                    class="w-full border rounded px-3 py-2 text-sm"
                    placeholder="admin"
                  />
                </div>
                <div>
                  <label class="block text-sm text-gray-600 mb-1">Senha</label>
                  <div class="relative">
                    <input
                      v-model="deviceForm.rtsp_password"
                      :type="showPassword ? 'text' : 'password'"
                      autocomplete="new-password"
                      name="camera_pass"
                      class="w-full border rounded px-3 py-2 text-sm pr-8"
                      placeholder="••••••"
                    />
                    <button type="button" @click="showPassword = !showPassword" class="absolute right-2 top-2 text-gray-400">
                      <component :is="showPassword ? EyeOff : Eye" :size="14" />
                    </button>
                  </div>
                </div>
                <div>
                  <label class="block text-sm text-gray-600 mb-1">Porta RTSP</label>
                  <input v-model.number="deviceForm.rtsp_port" type="number" autocomplete="off" class="w-full border rounded px-3 py-2 text-sm" placeholder="554" />
                </div>
                <div>
                  <label class="block text-sm text-gray-600 mb-1">Canal</label>
                  <input v-model.number="deviceForm.rtsp_channel" type="number" min="1" autocomplete="off" class="w-full border rounded px-3 py-2 text-sm" placeholder="1" />
                </div>
                <div class="col-span-2">
                  <label class="block text-sm text-gray-600 mb-1">Stream</label>
                  <div class="flex gap-2">
                    <label class="flex items-center gap-1.5 text-sm cursor-pointer">
                      <input type="radio" v-model.number="deviceForm.rtsp_subtype" :value="0" class="accent-brand-500" />
                      <span>Principal (subtype 0 — maior qualidade)</span>
                    </label>
                    <label class="flex items-center gap-1.5 text-sm cursor-pointer">
                      <input type="radio" v-model.number="deviceForm.rtsp_subtype" :value="1" class="accent-brand-500" />
                      <span>Extra (subtype 1)</span>
                    </label>
                  </div>
                </div>
              </div>
              <p class="text-xs text-gray-400 mt-2 font-mono break-all">{{ rtspPreview(deviceForm) }}</p>
            </div>
          </template>

          <div>
            <label class="block text-sm text-gray-600 mb-1">Observações</label>
            <input v-model="deviceForm.notes" class="w-full border rounded px-3 py-2 text-sm" placeholder="Opcional" />
          </div>

          <div class="flex gap-2 pt-1">
            <button type="submit" :disabled="savingDevice" class="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm">
              {{ savingDevice ? 'Salvando...' : (editingDeviceId ? 'Salvar' : 'Adicionar') }}
            </button>
            <button type="button" @click="showDeviceModal = false" class="px-4 py-2 border rounded-lg text-sm">Cancelar</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal PiP câmera -->
    <div v-if="cameraModal" class="fixed inset-0 bg-black/80 flex items-center justify-center z-[60]" @click.self="closeCameraPip">
      <div class="bg-black rounded-lg overflow-hidden shadow-2xl" style="max-width: 720px; width: 100%;">
        <div class="flex items-center justify-between px-4 py-2 bg-gray-900">
          <div class="flex items-center gap-2 text-white">
            <Video :size="16" />
            <span class="font-medium text-sm">{{ cameraModal.name }}</span>
            <span class="text-xs text-gray-400">ao vivo</span>
          </div>
          <button @click="closeCameraPip" class="text-gray-400 hover:text-white">
            <X :size="18" />
          </button>
        </div>
        <!-- Stream MJPEG via img tag — o browser mantém conexão SSE-like com o endpoint -->
        <img
          :src="cameraModal.streamUrl"
          :key="cameraModal.id"
          class="w-full"
          style="max-height: 60vh; object-fit: contain; background: #111;"
          alt="Stream câmera"
          @error="toast.error('Erro ao conectar na câmera. Verifique IP e credenciais.')"
        />
        <p class="text-xs text-gray-500 text-center py-2">
          Conexão via RTSP → MJPEG (requer ffmpeg no servidor)
        </p>
      </div>
    </div>

    <AddLinkModal v-if="showAddLink" :nodes="nodes" @done="onLinkAdded" @close="showAddLink = false" />
  </div>
</template>
