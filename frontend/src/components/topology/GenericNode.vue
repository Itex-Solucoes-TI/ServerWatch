<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Camera, Printer, HelpCircle, Video, AlertTriangle } from 'lucide-vue-next'

const props = defineProps({ data: Object })
const emit = defineEmits(['openCamera'])

const TYPE_CONFIG = {
  CAMERA:  { icon: Camera,     border: 'border-gray-400', text: 'text-gray-700' },
  PRINTER: { icon: Printer,    border: 'border-gray-400', text: 'text-gray-700' },
  OTHER:   { icon: HelpCircle, border: 'border-gray-300', text: 'text-gray-600' },
}

const config = computed(() => TYPE_CONFIG[props.data?.device_type] ?? TYPE_CONFIG.OTHER)
const Icon = computed(() => config.value.icon)
const isCamera = computed(() => props.data?.device_type === 'CAMERA')
const isAmbiguous = computed(() => props.data?.link_ambiguous === true)
</script>

<template>
  <div :class="['px-3 py-2 bg-white border-2 rounded-lg shadow-sm min-w-[120px] border-dashed', isAmbiguous ? 'border-amber-400' : config.border]">
    <Handle type="target" :position="Position.Top"    class="!w-2 !h-2" />
    <Handle type="source" :position="Position.Bottom" class="!w-2 !h-2" />
    <Handle type="target" :position="Position.Left"   class="!w-2 !h-2" />
    <Handle type="source" :position="Position.Right"  class="!w-2 !h-2" />

    <div :class="['flex items-center gap-2', config.text]">
      <component :is="Icon" :size="14" class="shrink-0" />
      <p class="text-sm font-medium truncate max-w-[100px]">{{ data?.label || 'Dispositivo' }}</p>
      <button
        v-if="isCamera && data?.generic?.ip_address"
        @click.stop="$emit('openCamera', data.generic)"
        class="ml-auto shrink-0 p-0.5 rounded hover:bg-gray-100 text-gray-500 hover:text-brand-600"
        title="Ver câmera ao vivo"
      >
        <Video :size="13" />
      </button>
    </div>
    <p v-if="data?.generic?.ip_address" class="text-xs text-gray-400 mt-0.5 truncate">
      {{ data.generic.ip_address }}
    </p>
    <!-- Aviso: múltiplos switches na subnet, ligação manual necessária -->
    <div v-if="isAmbiguous" class="flex items-center gap-1 mt-1 text-amber-600" title="Mais de 1 switch na subnet — ligue manualmente via + Ligação">
      <AlertTriangle :size="11" />
      <span class="text-xs">Ligar manualmente</span>
    </div>
  </div>
</template>
