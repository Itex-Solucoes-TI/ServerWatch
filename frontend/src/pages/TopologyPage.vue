<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import { getGraph, savePositions, deleteLink } from '../api/topology'
import AddLinkModal from '../components/topology/AddLinkModal.vue'
import ServerNode from '../components/topology/ServerNode.vue'
import RouterNode from '../components/topology/RouterNode.vue'
import { toast } from 'vue-sonner'

const auth = useAuthStore()
const nodeTypes = { server: ServerNode, router: RouterNode }

const nodes = ref([])
const edges = ref([])
const loading = ref(true)
const showAddLink = ref(false)

onMounted(loadGraph)

async function loadGraph() {
  loading.value = true
  try {
    const { data } = await getGraph()
    nodes.value = (data.nodes ?? []).map((n) => ({ ...n, position: n.position }))
    edges.value = data.edges ?? []
  } catch (e) {
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
    nodeType = 'INTERNET'
    nodeId = 0
  } else if (node.id === 'VPN') {
    nodeType = 'VPN'
    nodeId = 0
  } else {
    const id = parseInt(String(node.id).replace(/^[SR]-/, ''))
    if (isNaN(id)) return
    nodeType = node.type === 'server' ? 'SERVER' : 'ROUTER'
    nodeId = id
  }

  const positions = [{
    node_type: nodeType,
    node_id: nodeId,
    position_x: pos.x ?? 0,
    position_y: pos.y ?? 0,
  }]
  try {
    await savePositions(positions)
  } catch {}
}

async function onLinkAdded() {
  await loadGraph()
  toast.success('Ligação criada')
}

/** Chamado pelo botão na lista E pelo Delete do teclado via @edges-delete */
async function removeEdge(edge) {
  if (edge.data?.auto) return
  const linkId = edge.data?.linkId
  if (!linkId) {
    toast.error('ID da ligação não encontrado')
    // restaura o edge no array caso o VueFlow já tenha removido
    await loadGraph()
    return
  }
  if (!confirm('Remover esta ligação?')) {
    await loadGraph()
    return
  }
  try {
    await deleteLink(linkId)
    edges.value = edges.value.filter((e) => e.id !== edge.id)
    toast.success('Ligação removida')
  } catch (e) {
    toast.error(e.response?.data?.detail ?? 'Erro ao remover ligação')
    await loadGraph()
  }
}

/** VueFlow dispara edgesChange com type='remove' ao pressionar Delete no canvas */
async function onEdgesChange(changes) {
  const removals = changes.filter((c) => c.type === 'remove')
  if (!removals.length) return

  if (!auth.isAdmin) {
    await loadGraph()
    return
  }

  for (const change of removals) {
    const edge = edges.value.find((e) => e.id === change.id)
    if (!edge) continue

    if (edge.data?.auto) {
      // restaura — ligações automáticas não podem ser removidas
      await loadGraph()
      return
    }

    const linkId = edge.data?.linkId
    if (!linkId) {
      await loadGraph()
      return
    }

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
      <button
        v-if="auth.isOperator && nodes.length >= 2"
        @click="showAddLink = true"
        class="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg shrink-0 w-fit"
      >
        + Adicionar ligação
      </button>
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
      </VueFlow>
    </div>

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
          >
            ×
          </button>
        </div>
      </div>
    </div>

    <div class="mt-4 bg-brand-50 border border-brand-100 rounded-lg p-4 text-sm text-brand-800">
      <p class="font-medium mb-2">Ligações automáticas por interface</p>
      <ol class="list-decimal list-inside space-y-1 text-gray-700">
        <li><strong>IP público</strong> → Liga ao nó "Internet"</li>
        <li><strong>Rede local (LAN)</strong> → Marque a interface como "Rede local". Liga somente entre dispositivos com LAN na mesma sub-rede (ex.: 192.168.1.10/24 e 192.168.1.20/24)</li>
        <li><strong>VPN</strong> → Liga ao nó "VPN" (não cria ligação direta entre dispositivos)</li>
        <li>Ligações manuais em "Adicionar ligação" para links adicionais (ex.: WAN entre Docker e Datacenter)</li>
      </ol>
    </div>

    <AddLinkModal v-if="showAddLink" :nodes="nodes" @done="onLinkAdded" @close="showAddLink = false" />
  </div>
</template>
