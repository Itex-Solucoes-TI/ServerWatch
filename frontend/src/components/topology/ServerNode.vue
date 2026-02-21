<script setup>
import { ref } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Server } from 'lucide-vue-next'

defineProps({ data: Object })
const expanded = ref(false)
</script>

<template>
  <div class="px-4 py-3 bg-white border-2 border-brand-300 rounded-lg shadow-sm min-w-[130px]">
    <Handle type="target" :position="Position.Top"    class="!w-2 !h-2 !bg-brand-500" />
    <Handle type="source" :position="Position.Bottom" class="!w-2 !h-2 !bg-brand-500" />
    <Handle type="target" :position="Position.Left"   class="!w-2 !h-2 !bg-brand-500" />
    <Handle type="source" :position="Position.Right"  class="!w-2 !h-2 !bg-brand-500" />

    <div class="flex items-center justify-between gap-2 text-brand-800">
      <div class="flex items-center gap-2 min-w-0">
        <Server :size="16" class="shrink-0" />
        <p class="font-semibold truncate">{{ data?.label || 'Servidor' }}</p>
      </div>
      <button
        v-if="data?.containers?.length"
        @click.prevent="expanded = !expanded"
        class="shrink-0 w-6 h-6 flex items-center justify-center rounded bg-brand-100 hover:bg-brand-200 text-brand-600 text-sm font-bold"
        :title="expanded ? 'Recolher' : 'Expandir'"
      >
        {{ expanded ? '−' : '+' }}
      </button>
    </div>

    <div v-if="data?.containers?.length && expanded" class="mt-2 pt-2 border-t border-gray-100">
      <p class="text-xs text-gray-500 font-medium">Docker</p>
      <ul class="text-xs text-gray-600 mt-0.5 space-y-0.5 max-h-48 overflow-y-auto">
        <li v-for="c in data.containers" :key="c.name" class="truncate flex gap-1">
          <span :class="c.status === 'running' ? 'text-emerald-600' : 'text-gray-400'">•</span>
          {{ c.name }}
        </li>
      </ul>
    </div>
    <p v-else-if="data?.containers?.length" class="text-xs text-gray-500 mt-1">
      {{ data.containers.length }} container{{ data.containers.length > 1 ? 'es' : '' }}
    </p>
  </div>
</template>
