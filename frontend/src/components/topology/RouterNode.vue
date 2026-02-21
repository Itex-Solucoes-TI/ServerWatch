<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Router, Network, Wifi, ShieldCheck, Globe, Lock, HelpCircle } from 'lucide-vue-next'

const props = defineProps({ data: Object })

const TYPE_CONFIG = {
  ROUTER:   { icon: Router,      border: 'border-amber-300',   text: 'text-amber-800',   bg: 'bg-amber-50'   },
  SWITCH:   { icon: Network,     border: 'border-blue-300',    text: 'text-blue-800',    bg: 'bg-blue-50'    },
  WIFI_AP:  { icon: Wifi,        border: 'border-emerald-300', text: 'text-emerald-800', bg: 'bg-emerald-50' },
  FIREWALL: { icon: ShieldCheck, border: 'border-red-300',     text: 'text-red-800',     bg: 'bg-red-50'     },
  INTERNET: { icon: Globe,       border: 'border-sky-300',     text: 'text-sky-800',     bg: 'bg-sky-50'     },
  VPN:      { icon: Lock,        border: 'border-purple-300',  text: 'text-purple-800',  bg: 'bg-purple-50'  },
}

const config = computed(() => TYPE_CONFIG[props.data?.device_type] ?? TYPE_CONFIG.ROUTER)
const Icon = computed(() => config.value.icon ?? HelpCircle)
</script>

<template>
  <div :class="['px-4 py-3 bg-white border-2 rounded-lg shadow-sm min-w-[130px]', config.border]">
    <Handle type="target" :position="Position.Top"    class="!w-2 !h-2 !bg-current" />
    <Handle type="source" :position="Position.Bottom" class="!w-2 !h-2 !bg-current" />
    <Handle type="target" :position="Position.Left"   class="!w-2 !h-2 !bg-current" />
    <Handle type="source" :position="Position.Right"  class="!w-2 !h-2 !bg-current" />
    <div :class="['flex items-center gap-2', config.text]">
      <component :is="Icon" :size="16" />
      <p class="font-semibold truncate max-w-[120px]">{{ data?.label || 'Dispositivo' }}</p>
    </div>
  </div>
</template>
