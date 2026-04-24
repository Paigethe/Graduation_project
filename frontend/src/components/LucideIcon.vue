<script setup lang="ts">
import type { Component } from 'vue'
import { computed } from 'vue'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BookOpen,
  BrainCircuit,
  ClipboardList,
  Database,
  Download,
  Filter,
  FileText,
  LayoutDashboard,
  MessageCircle,
  Plus,
  Search,
  Send,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  UserRound,
  Users,
} from 'lucide-vue-next'

import type { LucideName } from '../app/menu'

const props = defineProps<{
  name: LucideName | string
}>()

const icon = computed<Component>(() => {
  const map: Record<string, Component> = {
    activity: Activity,
    'alert-triangle': AlertTriangle,
    'bar-chart-3': BarChart3,
    'book-open': BookOpen,
    'brain-circuit': BrainCircuit,
    'clipboard-list': ClipboardList,
    database: Database,
    download: Download,
    filter: Filter,
    'file-text': FileText,
    'layout-dashboard': LayoutDashboard,
    'message-circle': MessageCircle,
    plus: Plus,
    search: Search,
    send: Send,
    'shield-check': ShieldCheck,
    'sliders-horizontal': SlidersHorizontal,
    sparkles: Sparkles,
    'user-round': UserRound,
    users: Users,
  }
  return map[String(props.name)] ?? BrainCircuit
})
</script>

<template>
  <component :is="icon" v-bind="$attrs" />
</template>
