<script setup lang="ts">
import LucideIcon from './LucideIcon.vue'

defineProps<{
  icon: string
  label: string
  value: string | number
  hint?: string
  tone?: 'indigo' | 'emerald' | 'amber' | 'rose' | 'slate'
  clickable?: boolean
  badge?: string | number | null
}>()
</script>

<template>
  <component
    :is="clickable ? 'button' : 'div'"
    :type="clickable ? 'button' : undefined"
    :class="[
      'bg-white rounded-2xl border border-slate-100 shadow-sm p-5 transition-shadow text-left',
      clickable ? 'hover:shadow-md hover:border-indigo-200 cursor-pointer' : 'hover:shadow-md',
    ]"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="flex items-center gap-2 min-w-0">
          <div class="text-xs font-bold text-slate-400 tracking-widest uppercase truncate">{{ label }}</div>
          <span
            v-if="badge !== undefined && badge !== null && badge !== '' && Number(badge) !== 0"
            class="inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full bg-rose-500 text-white text-[10px] font-bold"
          >
            {{ badge }}
          </span>
        </div>
        <div class="mt-2 text-2xl font-black tracking-tight text-slate-900">{{ value }}</div>
        <div v-if="hint" class="mt-2 text-xs text-slate-500 truncate">{{ hint }}</div>
      </div>

      <div
        :class="[
          'p-3 rounded-xl border shadow-sm flex-shrink-0',
          tone === 'emerald'
            ? 'bg-emerald-50 text-emerald-600 border-emerald-100'
            : tone === 'amber'
              ? 'bg-amber-50 text-amber-600 border-amber-100'
              : tone === 'rose'
                ? 'bg-rose-50 text-rose-600 border-rose-100'
                : tone === 'slate'
                  ? 'bg-slate-50 text-slate-600 border-slate-100'
                  : 'bg-indigo-50 text-indigo-600 border-indigo-100',
        ]"
      >
        <LucideIcon :name="icon" class="w-5 h-5" />
      </div>
    </div>
  </component>
</template>
