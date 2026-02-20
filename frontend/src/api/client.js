import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import router from '../router'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) config.headers.Authorization = `Bearer ${auth.token}`
  if (auth.companyId) config.headers['X-Company-Id'] = auth.companyId
  return config
})

client.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (err.response?.status === 401 && err.config && !err.config._retry) {
      err.config._retry = true
      const auth = useAuthStore()
      if (auth.refreshToken) {
        try {
          const { data } = await axios.post('/api/auth/refresh', {
            refresh_token: auth.refreshToken,
          })
          auth.token = data.access_token
          err.config.headers.Authorization = `Bearer ${data.access_token}`
          return client(err.config)
        } catch {
          auth.logout()
          router.push('/login')
        }
      } else {
        router.push('/login')
      }
    }
    return Promise.reject(err)
  }
)

export default client
