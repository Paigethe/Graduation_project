<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
  <div class="bg-white p-20 rounded-xl shadow-sm border border-slate-100 text-center text-slate-300">
    <div class="mx-auto mb-4 opacity-10">
      <slot name="icon" />
    </div>
    <h3 class="text-sm font-bold uppercase tracking-widest text-slate-400">“{{ title }}” 模块已挂载</h3>
    <p class="text-[10px] mt-2 font-mono">Vue3 Frontend Bridge Connected Successfully</p>
  </div>
</template>

