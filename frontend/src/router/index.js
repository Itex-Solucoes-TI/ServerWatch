import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import MainLayout from '../components/layout/MainLayout.vue'
import LoginPage from '../pages/LoginPage.vue'
import CompanySelectPage from '../pages/CompanySelectPage.vue'
import DashboardPage from '../pages/DashboardPage.vue'
import TopologyPage from '../pages/TopologyPage.vue'
import ServersPage from '../pages/ServersPage.vue'
import ServerDetailPage from '../pages/ServerDetailPage.vue'
import RoutersPage from '../pages/RoutersPage.vue'
import RouterDetailPage from '../pages/RouterDetailPage.vue'
import ChecksPage from '../pages/ChecksPage.vue'
import CheckDetailPage from '../pages/CheckDetailPage.vue'
import DockerPage from '../pages/DockerPage.vue'
import TerminalPage from '../pages/TerminalPage.vue'
import NotificationsPage from '../pages/NotificationsPage.vue'
import CompanySettingsPage from '../pages/CompanySettingsPage.vue'
import UsersPage from '../pages/UsersPage.vue'
import CompaniesPage from '../pages/CompaniesPage.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginPage, meta: { public: true } },
  { path: '/select-company', name: 'selectCompany', component: CompanySelectPage, meta: { public: true } },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: DashboardPage },
      { path: 'topology', name: 'topology', component: TopologyPage },
      { path: 'servers', name: 'servers', component: ServersPage },
      { path: 'servers/:id', name: 'serverDetail', component: ServerDetailPage },
      { path: 'routers', name: 'routers', component: RoutersPage },
      { path: 'routers/:id', name: 'routerDetail', component: RouterDetailPage },
      { path: 'checks', name: 'checks', component: ChecksPage },
      { path: 'checks/:id', name: 'checkDetail', component: CheckDetailPage },
      { path: 'docker', name: 'docker', component: DockerPage },
      { path: 'terminal', name: 'terminal', component: TerminalPage },
      { path: 'terminal/:serverId', name: 'terminalServer', component: TerminalPage },
      { path: 'notifications', name: 'notifications', component: NotificationsPage },
      { path: 'settings', name: 'settings', component: CompanySettingsPage },
      { path: 'users', name: 'users', component: UsersPage },
      { path: 'companies', name: 'companies', component: CompaniesPage },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (auth.token && to.path === '/login' && !auth.needsLicense) next('/dashboard')
    else if (auth.token && auth.needsLicense && to.path !== '/login') next('/login')
    else if (auth.token && to.path === '/select-company' && auth.companyId && !auth.needsLicense) next('/dashboard')
    else next()
  } else if (auth.token) {
    if (auth.needsLicense) next('/login')
    else if (!auth.companyId && to.path !== '/select-company') next('/select-company')
    else next()
  } else {
    next('/login')
  }
})

export default router
