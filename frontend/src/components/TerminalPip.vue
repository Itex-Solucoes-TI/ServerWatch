<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { useTerminalStore } from '../stores/terminal'
import { list as listServers } from '../api/servers'
import { Minus, Square, Maximize2, X, Plus, LayoutGrid, Columns2, Rows2 } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const store = useTerminalStore()
const isExpanded = ref(false)
const isDragging = ref(false)
const isResizing = ref(false)
const resizeEdge = ref('')
const dragStart = ref({ x: 0, y: 0 })
const pipPos = ref({ x: 20, y: 20 })
const pipSize = ref({ w: 420, h: 300 })
const servers = ref([])
const splitRatio = ref(0.5)
const isDraggingSplit = ref(false)
const bodyEl = ref(null)

// Mapa NÃO reativo — alterações não causam re-renders
const termMap = new Map() // sessionId -> { terminal, fitAddon, containerEl }

const isOnTerminalPage = computed(() => route.path.startsWith('/terminal'))
const showPip = computed(() => store.hasAny && !isOnTerminalPage.value)
const isFullscreen = computed(() => store.isFullscreen && store.hasAny)
const hasMultiple = computed(() => store.connectedSessions.length >= 2)

const pipStyle = computed(() => {
  if (!showPip.value || isExpanded.value) return undefined
  return {
    left: `${pipPos.value.x}px`,
    top: `${pipPos.value.y}px`,
    width: `${pipSize.value.w}px`,
    height: `${pipSize.value.h}px`,
  }
})

const sshServers = computed(() => servers.value.filter((s) => s.ssh_host))

// Papel de cada sessão no layout atual: 'active' | 'split-0' | 'split-1' | 'hidden'
const panelRoles = computed(() => {
  const roles = {}
  const mode = store.layoutMode
  const connected = store.connectedSessions

  if (mode === 'single') {
    store.sessions.forEach((s) => {
      roles[s.id] = s.id === store.activeId ? 'active' : 'hidden'
    })
  } else {
    const splitSessions = connected.slice(0, 2)
    store.sessions.forEach((s) => {
      const idx = splitSessions.findIndex((c) => c.id === s.id)
      roles[s.id] = idx >= 0 ? `split-${idx}` : 'hidden'
    })
  }
  return roles
})

// Estilo inline de cada painel para controle do splitRatio
function panelStyle(sessionId) {
  const role = panelRoles.value[sessionId]
  if (role === 'hidden') return { display: 'none' }
  if (role === 'active') return { flex: '1 1 auto' }
  if (role === 'split-0') {
    return store.layoutMode === 'split-h'
      ? { width: `${splitRatio.value * 100}%`, flexShrink: '0' }
      : { height: `${splitRatio.value * 100}%`, flexShrink: '0' }
  }
  if (role === 'split-1') {
    return store.layoutMode === 'split-h'
      ? { flex: '1 1 0', minWidth: '0' }
      : { flex: '1 1 0', minHeight: '0' }
  }
  return {}
}

async function loadServers() {
  try {
    const { data } = await listServers()
    servers.value = data
  } catch {}
}

function focusActiveTerminal() {
  const session = store.activeSession
  if (!session) return
  const t = termMap.get(session.id)
  t?.terminal.focus()
}

function mountTerminal(sessionId, containerEl) {
  const existing = termMap.get(sessionId)
  if (existing) return // já montado, não recria

  const term = markRaw(new Terminal({
    cursorBlink: true,
    theme: { background: '#1e293b', foreground: '#e2e8f0' },
    fontSize: 13,
  }))
  const fitAddon = markRaw(new FitAddon())
  term.loadAddon(fitAddon)
  term.onData((data) => store.sendInput(sessionId, data))
  store.setSessionWriteCallback(sessionId, (data) => term.write(data))
  term.open(containerEl)
  nextTick(() => { fitAddon.fit(); term.focus() })
  termMap.set(sessionId, { terminal: term, fitAddon, containerEl })
}

function dismountTerminal(sessionId) {
  const t = termMap.get(sessionId)
  if (!t) return
  store.setSessionWriteCallback(sessionId, null)
  t.terminal.dispose()
  termMap.delete(sessionId)
}

function fitAll() {
  termMap.forEach((t) => { try { t.fitAddon.fit() } catch {} })
}

function newSession() {
  store.addSession()
}

function closeSession(id) {
  dismountTerminal(id)
  store.removeSession(id)
}

function connectSession(sessionId, serverId, serverName) {
  store.connect(sessionId, serverId, serverName)
}

function minimize() {
  store.setFullscreen(false)
  if (isOnTerminalPage.value) router.push('/dashboard')
  else isExpanded.value = false
}

function toggleMaximize() {
  if (showPip.value) {
    isExpanded.value = !isExpanded.value
  } else {
    store.setFullscreen(!store.isFullscreen)
    nextTick(fitAll)
  }
}

function closeAll() {
  const ids = store.sessions.map((s) => s.id)
  ids.forEach((id) => { dismountTerminal(id); store.removeSession(id) })
  if (isOnTerminalPage.value) router.replace('/terminal').catch(() => {})
}

function maximize() {
  if (showPip.value) isExpanded.value = true
  else if (store.activeSession?.serverId) router.push(`/terminal/${store.activeSession.serverId}`)
}

function setLayout(mode) {
  store.setLayoutMode(mode)
  nextTick(() => nextTick(() => { fitAll(); focusActiveTerminal() }))
}

function startDrag(e) {
  if (e.target.closest('button') || e.target.closest('.resize-handle') || e.target.closest('.tab')) return
  isDragging.value = true
  dragStart.value = { x: e.clientX - pipPos.value.x, y: e.clientY - pipPos.value.y }
}

function startResize(e, edge) {
  e.stopPropagation()
  isResizing.value = true
  resizeEdge.value = edge
  dragStart.value = { x: e.clientX, y: e.clientY, ...pipPos.value, ...pipSize.value }
}

function startSplitDrag() { isDraggingSplit.value = true }

function onMouseMove(e) {
  if (isDragging.value) {
    pipPos.value = {
      x: Math.max(0, Math.min(window.innerWidth - pipSize.value.w, e.clientX - dragStart.value.x)),
      y: Math.max(0, Math.min(window.innerHeight - pipSize.value.h, e.clientY - dragStart.value.y)),
    }
  }
  if (isResizing.value) {
    const dx = e.clientX - dragStart.value.x
    const dy = e.clientY - dragStart.value.y
    const min = 200
    if (resizeEdge.value.includes('e')) pipSize.value.w = Math.max(min, dragStart.value.w + dx)
    if (resizeEdge.value.includes('w')) {
      const nw = Math.max(min, dragStart.value.w - dx)
      pipPos.value.x = dragStart.value.x + dragStart.value.w - nw
      pipSize.value.w = nw
    }
    if (resizeEdge.value.includes('s')) pipSize.value.h = Math.max(min, dragStart.value.h + dy)
    if (resizeEdge.value.includes('n')) {
      const nh = Math.max(min, dragStart.value.h - dy)
      pipPos.value.y = dragStart.value.y + dragStart.value.h - nh
      pipSize.value.h = nh
    }
    nextTick(fitAll)
  }
  if (isDraggingSplit.value && bodyEl.value) {
    const rect = bodyEl.value.getBoundingClientRect()
    const pct = store.layoutMode === 'split-h'
      ? (e.clientX - rect.left) / rect.width
      : (e.clientY - rect.top) / rect.height
    splitRatio.value = Math.max(0.2, Math.min(0.8, pct))
    nextTick(fitAll)
  }
}

function onMouseUp() {
  isDragging.value = false
  isResizing.value = false
  isDraggingSplit.value = false
}

// Limpa terminais de sessões removidas
watch(
  () => store.sessions.map((s) => s.id),
  (ids) => {
    termMap.forEach((_, sid) => { if (!ids.includes(sid)) dismountTerminal(sid) })
  }
)

// Re-fit quando layout ou estado da janela muda, e recoloca foco no terminal ativo
watch(
  [() => store.activeId, () => store.layoutMode, isExpanded, () => store.isFullscreen, showPip],
  () => nextTick(() => nextTick(() => { fitAll(); focusActiveTerminal() }))
)

onMounted(() => {
  loadServers()
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  store.sessions.forEach((s) => dismountTerminal(s.id))
})
</script>

<template>
  <div
    v-if="store.hasAny"
    class="terminal-wrapper"
    :class="{
      'terminal-fullscreen': isFullscreen,
      'terminal-expanded': isOnTerminalPage && !isFullscreen,
      'terminal-pip': showPip && !isExpanded,
      'terminal-pip-expanded': showPip && isExpanded,
    }"
    :style="showPip && !isExpanded ? pipStyle : undefined"
  >
    <div class="terminal-header" @mousedown="startDrag">
      <div class="terminal-tabs">
        <button
          v-for="s in store.sessions"
          :key="s.id"
          class="tab"
          :class="{ active: store.activeId === s.id }"
          @click="store.setActiveSession(s.id)"
        >
          <span>{{ s.serverName || 'Nova conexão' }}</span>
          <button
            v-if="store.sessions.length > 1"
            class="tab-close"
            @click.stop="closeSession(s.id)"
            title="Fechar aba"
          >
            <X class="w-3 h-3" />
          </button>
        </button>
        <button @click="newSession(); nextTick(focusActiveTerminal)" class="tab tab-add" title="Novo terminal">
          <Plus class="w-3.5 h-3.5" />
        </button>
      </div>
      <div class="terminal-header-actions">
        <div v-if="hasMultiple" class="layout-btns">
          <button
            :class="['terminal-ctl-btn', { active: store.layoutMode === 'single' }]"
            @click="setLayout('single')"
            title="Aba única"
          >
            <LayoutGrid class="w-3.5 h-3.5" />
          </button>
          <button
            :class="['terminal-ctl-btn', { active: store.layoutMode === 'split-h' }]"
            @click="setLayout('split-h')"
            title="Lado a lado"
          >
            <Columns2 class="w-3.5 h-3.5" />
          </button>
          <button
            :class="['terminal-ctl-btn', { active: store.layoutMode === 'split-v' }]"
            @click="setLayout('split-v')"
            title="Empilhado"
          >
            <Rows2 class="w-3.5 h-3.5" />
          </button>
        </div>
        <div class="terminal-window-controls">
          <button
            v-if="isOnTerminalPage || isExpanded"
            @click="minimize"
            class="terminal-ctl-btn"
            title="Minimizar"
          >
            <Minus class="w-3.5 h-3.5" />
          </button>
          <button
            v-if="showPip && !isExpanded"
            @click="maximize"
            class="terminal-ctl-btn"
            title="Expandir"
          >
            <Maximize2 class="w-3.5 h-3.5" />
          </button>
          <button
            @click="toggleMaximize"
            class="terminal-ctl-btn"
            :title="(isOnTerminalPage && store.isFullscreen) || isExpanded ? 'Restaurar' : 'Maximizar'"
          >
            <Square v-if="!(isOnTerminalPage && store.isFullscreen) && !isExpanded" class="w-3.5 h-3.5" />
            <Maximize2 v-else class="w-3.5 h-3.5" />
          </button>
          <button @click="closeAll" class="terminal-ctl-btn terminal-ctl-close" title="Fechar tudo">
            <X class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <div
      ref="bodyEl"
      class="terminal-body"
      :class="{
        'body-split-h': store.layoutMode === 'split-h',
        'body-split-v': store.layoutMode === 'split-v',
      }"
    >
      <!-- Todos os painéis sempre no DOM — layout controlado por CSS via panelStyle -->
      <div
        v-for="s in store.sessions"
        :key="s.id"
        class="session-panel"
        :style="panelStyle(s.id)"
      >
        <!-- Formulário de conexão -->
        <div v-if="s.status === ''" class="terminal-connect-form">
          <select v-model="s.pendingServerId" class="term-select">
            <option :value="null">— Servidor —</option>
            <option v-for="sv in sshServers" :key="sv.id" :value="sv.id">
              {{ sv.name }} ({{ sv.ssh_host }})
            </option>
          </select>
          <button
            :disabled="!s.pendingServerId"
            class="term-btn"
            @click="connectSession(s.id, s.pendingServerId, sshServers.find(x => x.id === s.pendingServerId)?.name)"
          >
            Conectar
          </button>
        </div>
        <div v-else-if="s.status === 'connecting'" class="terminal-connecting">Conectando...</div>
        <div v-else-if="s.status === 'error'" class="terminal-error">
          {{ s.errorMsg }}
          <button class="retry-btn" @click="store.disconnect(s.id)">Tentar novamente</button>
        </div>
        <!-- Container do terminal: sempre renderizado quando conectado -->
        <div
          v-else-if="s.status === 'connected'"
          :ref="(el) => el && mountTerminal(s.id, el)"
          class="terminal-container"
          @click="termMap.get(s.id)?.terminal.focus()"
        />
      </div>

      <!-- Divisor arrastável (split) -->
      <div
        v-if="store.layoutMode !== 'single' && store.connectedSessions.length >= 2"
        class="split-divider"
        :class="{ 'divider-h': store.layoutMode === 'split-h', 'divider-v': store.layoutMode === 'split-v' }"
        :style="store.layoutMode === 'split-h'
          ? { left: `calc(${splitRatio * 100}% - 2px)` }
          : { top: `calc(${splitRatio * 100}% - 2px)` }"
        @mousedown.stop="startSplitDrag"
      />
    </div>

    <template v-if="showPip && !isExpanded">
      <div class="resize-handle resize-e" @mousedown="(e) => startResize(e, 'e')" />
      <div class="resize-handle resize-s" @mousedown="(e) => startResize(e, 's')" />
      <div class="resize-handle resize-se" @mousedown="(e) => startResize(e, 'se')" />
    </template>
  </div>
</template>

<style scoped>
.terminal-wrapper {
  background: #1e293b; overflow: hidden; display: flex; flex-direction: column;
}
.terminal-fullscreen { position: fixed; inset: 0; z-index: 10000; border-radius: 0; }
.terminal-expanded {
  position: fixed; top: 56px; left: 224px; right: 20px; bottom: 20px; z-index: 100;
  border-radius: 8px; border: 1px solid #334155; box-shadow: 0 4px 24px rgba(0,0,0,0.15);
}
.terminal-pip {
  position: fixed; z-index: 9999; border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.25); border: 1px solid #334155;
}
.terminal-pip-expanded {
  position: fixed; top: 56px; left: 224px; right: 20px; bottom: 20px; z-index: 9999;
  border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); border: 1px solid #334155;
}

.terminal-header {
  display: flex; align-items: center; padding: 6px 8px;
  background: #334155; color: #e2e8f0; font-size: 13px; cursor: move; flex-shrink: 0;
}
.terminal-tabs {
  display: flex; align-items: center; gap: 2px; flex: 1; min-width: 0; overflow-x: auto;
}
.tab {
  display: flex; align-items: center; gap: 4px; padding: 4px 8px; border-radius: 4px;
  background: transparent; border: none; color: #94a3b8; cursor: pointer;
  font-size: 12px; white-space: nowrap; max-width: 140px;
}
.tab:hover, .tab.active { background: rgba(255,255,255,0.08); color: #e2e8f0; }
.tab-close { padding: 0; background: none; border: none; color: inherit; cursor: pointer; opacity: 0.7; }
.tab-close:hover { opacity: 1; color: #f87171; }
.tab-add { padding: 4px 6px; flex-shrink: 0; }

.terminal-header-actions { display: flex; align-items: center; gap: 4px; }
.layout-btns { display: flex; gap: 1px; border-right: 1px solid #475569; padding-right: 6px; margin-right: 2px; }
.layout-btns .terminal-ctl-btn.active { background: rgba(255,255,255,0.18); color: #e2e8f0; }
.terminal-window-controls { display: flex; align-items: center; gap: 2px; }
.terminal-ctl-btn {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 24px; background: transparent; border: none;
  color: #94a3b8; cursor: pointer; border-radius: 4px;
}
.terminal-ctl-btn:hover { background: rgba(255,255,255,0.08); color: #e2e8f0; }
.terminal-ctl-close:hover { background: #dc2626; color: white; }

.terminal-body {
  flex: 1; min-height: 0; display: flex; flex-direction: row; position: relative; overflow: hidden;
}
.terminal-body.body-split-h { flex-direction: row; }
.terminal-body.body-split-v { flex-direction: column; }

.session-panel {
  display: flex; flex-direction: column; min-width: 0; min-height: 0; overflow: hidden;
}

.terminal-connect-form { display: flex; align-items: center; gap: 8px; padding: 16px; flex-wrap: wrap; }
.term-select {
  border: 1px solid #475569; border-radius: 4px; padding: 4px 8px;
  font-size: 13px; background: #1e293b; color: #e2e8f0; outline: none;
}
.term-btn {
  padding: 5px 14px; background: #3b82f6; color: white; border: none;
  border-radius: 4px; font-size: 13px; cursor: pointer;
}
.term-btn:disabled { opacity: 0.5; cursor: default; }
.term-btn:not(:disabled):hover { background: #2563eb; }
.terminal-connecting { padding: 16px; color: #94a3b8; font-size: 13px; }
.terminal-error {
  padding: 16px; color: #f87171; font-size: 13px;
  display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
}
.retry-btn { color: #60a5fa; background: none; border: none; cursor: pointer; font-size: 13px; text-decoration: underline; }
.terminal-container { flex: 1; min-height: 0; min-width: 0; overflow: hidden; padding: 4px; }

.split-divider {
  position: absolute; background: #475569; z-index: 10;
  transition: background 0.15s;
}
.split-divider:hover { background: #64748b; }
.split-divider.divider-h { width: 4px; top: 0; bottom: 0; cursor: col-resize; }
.split-divider.divider-v { height: 4px; left: 0; right: 0; cursor: row-resize; }

.resize-handle { position: absolute; z-index: 1; }
.resize-e { right: 0; top: 0; bottom: 0; width: 6px; cursor: ew-resize; }
.resize-s { bottom: 0; left: 0; right: 0; height: 6px; cursor: ns-resize; }
.resize-se { right: 0; bottom: 0; width: 12px; height: 12px; cursor: nwse-resize; }
</style>
