import { defineStore } from 'pinia'
import { useAuthStore } from './auth'

let nextId = 1
function genId() {
  return `t${nextId++}`
}

export const useTerminalStore = defineStore('terminal', {
  state: () => ({
    sessions: [], // { id, serverId, serverName, status, errorMsg, ws, writeCallback }
    activeId: null,
    isFullscreen: false,
    layoutMode: 'single', // 'single' | 'split-h' | 'split-v'
  }),
  getters: {
    hasAny: (s) => s.sessions.length > 0,
    hasConnected: (s) => s.sessions.some((x) => x.status === 'connected'),
    activeSession: (s) => s.sessions.find((x) => x.id === s.activeId),
    connectedSessions: (s) => s.sessions.filter((x) => x.status === 'connected'),
  },
  actions: {
    addSession() {
      const id = genId()
      this.sessions.push({
        id,
        serverId: null,
        serverName: '',
        status: '',
        errorMsg: '',
        ws: null,
        writeCallback: null,
        pendingServerId: null,
      })
      this.activeId = id
      return id
    },
    removeSession(id) {
      const s = this.sessions.find((x) => x.id === id)
      if (s?.ws) {
        s.ws.close()
        s.ws = null
      }
      this.sessions = this.sessions.filter((x) => x.id !== id)
      if (this.activeId === id && this.sessions.length) {
        this.activeId = this.sessions[0].id
      } else {
        this.activeId = this.sessions[0]?.id ?? null
      }
      if (!this.sessions.length) this.isFullscreen = false
    },
    setActiveSession(id) {
      if (this.sessions.some((x) => x.id === id)) this.activeId = id
    },
    setSessionWriteCallback(id, fn) {
      const s = this.sessions.find((x) => x.id === id)
      if (s) s.writeCallback = fn
    },
    setLayoutMode(mode) {
      this.layoutMode = mode
    },
    connect(sessionId, serverId, serverName) {
      const auth = useAuthStore()
      if (!sessionId || !serverId || !auth.token || !auth.companyId) return
      const s = this.sessions.find((x) => x.id === sessionId)
      if (!s) return
      if (s.ws) {
        s.ws.close()
        s.ws = null
      }
      s.serverId = serverId
      s.serverName = serverName || ''
      s.status = 'connecting'
      s.errorMsg = ''
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url = `${proto}//${location.host}/api/ws/ssh/${serverId}?token=${encodeURIComponent(auth.token)}&company_id=${auth.companyId}`
      const ws = new WebSocket(url)
      s.ws = ws
      ws.onopen = () => {
        s.status = 'connected'
      }
      ws.onmessage = (e) => {
        const data = e.data
        if (typeof data === 'string' && data.startsWith('{')) {
          try {
            const obj = JSON.parse(data)
            if (obj.error) {
              s.errorMsg = obj.error
              s.status = 'error'
            }
            return
          } catch (_) {}
        }
        s.writeCallback?.(data)
      }
      ws.onerror = () => {
        s.status = 'error'
        s.errorMsg = s.errorMsg || 'Falha na conexão'
      }
      ws.onclose = () => {
        if (s.status === 'connecting') {
          s.status = 'error'
          s.errorMsg = s.errorMsg || 'Conexão fechada'
        }
      }
    },
    disconnect(sessionId) {
      const s = sessionId ? this.sessions.find((x) => x.id === sessionId) : null
      if (s) {
        if (s.ws) {
          s.ws.close()
          s.ws = null
        }
        s.status = ''
        s.errorMsg = ''
        s.serverId = null
        s.serverName = ''
      }
    },
    sendInput(sessionId, data) {
      const s = this.sessions.find((x) => x.id === sessionId)
      if (s?.ws?.readyState === WebSocket.OPEN) {
        s.ws.send(JSON.stringify({ type: 'input', data }))
      }
    },
    setFullscreen(val) {
      this.isFullscreen = val
    },
    // Convenience: usa sessão vazia se existir, senão cria (TerminalPage)
    connectToNew(serverId, serverName) {
      const empty = this.sessions.find((s) => !s.serverId && s.status === '')
      const id = empty ? empty.id : this.addSession()
      this.connect(id, serverId, serverName)
      return id
    },
  },
})
