<!--
  BaseModal — modal base reutilizável
  Props:
    title (string)      — título do modal
    size  (string)      — 'sm' | 'md' | 'lg' | 'xl'  (default: 'md')
  Slots:
    default             — conteúdo principal
    footer              — área de botões (opcional)
  Emits:
    close               — ao clicar fora ou no X
-->
<script setup>
defineProps({
  title: String,
  size: { type: String, default: 'md' },
})
const emit = defineEmits(['close'])

const sizeClass = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-2xl',
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      @click.self="emit('close')"
    >
      <div
        class="bg-white rounded-xl shadow-xl w-full flex flex-col max-h-[90vh]"
        :class="sizeClass[size] ?? sizeClass.md"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <h3 class="font-semibold text-gray-800">{{ title }}</h3>
          <button @click="emit('close')" class="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>
        <div class="overflow-y-auto px-6 py-4 flex-1">
          <!-- inputs ocultos para evitar autocomplete do browser -->
          <input type="text" style="display:none" autocomplete="username" />
          <input type="password" style="display:none" autocomplete="new-password" />
          <slot />
        </div>
        <div v-if="$slots.footer" class="px-6 py-4 border-t shrink-0">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
