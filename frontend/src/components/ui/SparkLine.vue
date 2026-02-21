<script setup>
/**
 * SparkLine: mini gráfico de linha SVG.
 * Props: values (number[]), color (string), height (number), width (number)
 */
const props = defineProps({
  values: { type: Array, default: () => [] },
  color: { type: String, default: '#6366f1' },
  height: { type: Number, default: 32 },
  width: { type: Number, default: 120 },
})

function buildPath(vals) {
  if (!vals || vals.length < 2) return ''
  const max = Math.max(...vals) || 1
  const min = Math.min(...vals)
  const range = max - min || 1
  const pad = 2
  const w = props.width
  const h = props.height - pad * 2
  const step = w / (vals.length - 1)
  const points = vals.map((v, i) => {
    const x = i * step
    const y = pad + h - ((v - min) / range) * h
    return `${x},${y}`
  })
  return 'M' + points.join(' L')
}
</script>

<template>
  <svg :width="width" :height="height" class="overflow-visible">
    <path v-if="values.length >= 2" :d="buildPath(values)" fill="none" :stroke="color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>
