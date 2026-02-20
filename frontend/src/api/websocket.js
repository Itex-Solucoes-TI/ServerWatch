import { useAuthStore } from '../stores/auth'
import { toast } from 'vue-sonner'

let ws = null

export function connectWebSocket() {
  const auth = useAuthStore()
  if (!auth.token || !auth.companyId) return
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = location.host
  ws = new WebSocket(`${proto}//${host}/api/ws/events`)
  ws.onmessage = (e) => {
    try {
      const { event, data } = JSON.parse(e.data)
      if (event === 'check_update') {
        toast.info(`Check #${data.check_id}: ${data.status}`, { description: data.message })
      }
    } catch {}
  }
  ws.onclose = () => {
    setTimeout(connectWebSocket, 5000)
  }
}

export function closeWebSocket() {
  if (ws) {
    ws.close()
    ws = null
  }
}
