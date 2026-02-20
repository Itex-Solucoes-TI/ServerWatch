<script setup>
import { Handle, Position } from '@vue-flow/core'

defineProps({
  data: Object,
})
</script>

<template>
  <div class="px-4 py-3 bg-white border-2 border-amber-200 rounded-lg shadow-sm min-w-[120px]">
    <Handle type="target" :position="Position.Top" class="!w-2 !h-2 !bg-amber-500" />
    <Handle type="source" :position="Position.Bottom" class="!w-2 !h-2 !bg-amber-500" />
    <Handle type="target" :position="Position.Left" class="!w-2 !h-2 !bg-amber-500" />
    <Handle type="source" :position="Position.Right" class="!w-2 !h-2 !bg-amber-500" />
    <p class="font-semibold text-amber-800">{{ data?.label || 'Roteador' }}</p>
  </div>
</template>
