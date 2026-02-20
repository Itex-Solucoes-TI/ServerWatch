<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import {
  LayoutDashboard, Network, Server, Radio, Activity, Container, Bell, Settings,
  Users, Building2, Terminal,
} from 'lucide-vue-next'

const route = useRoute()
const auth = useAuthStore()

const iconMap = {
  LayoutDashboard, Network, Server, Radio, Activity, Container, Bell, Settings, Users, Building2, Terminal,
}

const allLinks = [
  { path: '/dashboard', icon: 'LayoutDashboard', label: 'Dashboard', roles: ['VIEWER', 'OPERATOR', 'ADMIN'] },
  { path: '/topology', icon: 'Network', label: 'Topologia', roles: ['VIEWER', 'OPERATOR', 'ADMIN'] },
  { path: '/servers', icon: 'Server', label: 'Servidores', roles: ['VIEWER', 'OPERATOR', 'ADMIN'] },
  { path: '/routers', icon: 'Radio', label: 'Roteadores', roles: ['VIEWER', 'OPERATOR', 'ADMIN'] },
  { path: '/checks', icon: 'Activity', label: 'Health Checks', roles: ['VIEWER', 'OPERATOR', 'ADMIN'] },
  { path: '/docker', icon: 'Container', label: 'Docker', roles: ['VIEWER', 'OPERATOR', 'ADMIN'] },
  { path: '/terminal', icon: 'Terminal', label: 'Terminal', roles: ['OPERATOR', 'ADMIN'] },
  { path: '/notifications', icon: 'Bell', label: 'Notificações', roles: ['ADMIN'] },
  { path: '/settings', icon: 'Settings', label: 'Configurações', roles: ['ADMIN'] },
  { path: '/companies', icon: 'Building2', label: 'Minha Empresa', roles: ['ADMIN'] },
]

const adminLinks = [
  { path: '/users', icon: 'Users', label: 'Usuários' },
  { path: '/companies', icon: 'Building2', label: 'Empresas' },
]

const links = computed(() => {
  if (auth.user?.is_superadmin) {
    // superadmin vê tudo exceto o que está na seção adminLinks
    return allLinks.filter((l) => l.path !== '/companies' && l.path !== '/users')
  }
  return allLinks.filter((l) => l.roles.includes(auth.currentRole))
})

function isActive(l) {
  return route.path === l.path || (l.path === '/terminal' && route.path.startsWith('/terminal'))
}
</script>

<template>
  <aside class="w-56 bg-brand-800 min-h-screen flex flex-col">
    <div class="p-4">
      <RouterLink to="/dashboard" class="flex items-center gap-2">
        <span class="text-white font-bold text-lg">ServerWatch</span>
      </RouterLink>
    </div>
    <nav class="flex-1 px-2">
      <RouterLink
        v-for="l in links"
        :key="l.path"
        :to="l.path"
        class="flex items-center gap-2 px-3 py-2 rounded-lg mb-1 text-brand-100 hover:bg-brand-700 hover:text-white transition"
        :class="{ 'bg-brand-500/15 border-l-4 border-brand-500 text-white': isActive(l) }"
      >
        <component :is="iconMap[l.icon]" class="w-5 h-5" />
        {{ l.label }}
      </RouterLink>
      <template v-if="auth.user?.is_superadmin">
        <div class="border-t border-brand-700 my-2" />
        <RouterLink
          v-for="l in adminLinks"
          :key="l.path"
          :to="l.path"
          class="flex items-center gap-2 px-3 py-2 rounded-lg mb-1 text-brand-100 hover:bg-brand-700 hover:text-white transition"
          :class="{ 'bg-brand-500/15 border-l-4 border-brand-500 text-white': route.path === l.path }"
        >
          <component :is="iconMap[l.icon]" class="w-5 h-5" />
          {{ l.label }}
        </RouterLink>
      </template>
    </nav>
    <div class="p-4 border-t border-brand-700">
      <p class="text-brand-300 text-sm">{{ auth.currentCompany?.name }}</p>
      <p class="text-brand-400 text-xs">
        <span v-if="auth.currentRole" class="capitalize">{{ auth.currentRole === 'ADMIN' ? 'Admin' : auth.currentRole === 'OPERATOR' ? 'Operador' : 'Visualizador' }}</span>
        <span v-else>v1.0</span>
      </p>
    </div>
  </aside>
</template>
