<script setup lang="ts">
import LucideIcon from './LucideIcon.vue'

defineProps<{
  title: string
  desc?: string
  icon?: string
}>()
</script>

<template>
  <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-14 text-center text-slate-400">
    <LucideIcon :name="icon || 'activity'" class="w-12 h-12 mx-auto mb-4 opacity-10" />
    <div class="text-sm font-bold text-slate-600">{{ title }}</div>
    <div v-if="desc" class="text-xs text-slate-400 mt-2 max-w-md mx-auto">{{ desc }}</div>
  </div>
</template>

