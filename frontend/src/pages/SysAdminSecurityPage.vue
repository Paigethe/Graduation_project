<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElInput, ElMessage, ElSelect, ElTag } from 'element-plus'

import { api } from '../api/client'
import type { PageResp, UserLite } from '../api/types'
import { fmtDateTime } from '../app/format'
import EmptyState from '../components/EmptyState.vue'
import LucideIcon from '../components/LucideIcon.vue'

type AuditLog = {
  id: number
  user: UserLite | null
  method: string
  path: string
  status_code: number
  duration_ms: number
  ip: string
  created_at: string
}

const loading = ref(false)
const q = ref('')
const methodFilter = ref<'all' | string>('all')

const logs = ref<AuditLog[]>([])

const filtered = computed(() => {
  const s = q.value.trim()
  return logs.value.filter((l) => {
    if (methodFilter.value !== 'all' && l.method !== methodFilter.value) return false
    if (!s) return true
    return (
      (l.path || '').includes(s) ||
      (l.user?.username || '').includes(s) ||
      (l.user?.real_name || '').includes(s) ||
      String(l.status_code).includes(s)
    )
  })
})

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<PageResp<AuditLog>>('/api/admin/audit-logs/')
    logs.value = data.results ?? []
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败（请确认后端已启用审计日志接口）')
  } finally {
    loading.value = false
  }
}

function statusTone(code: number) {
  if (code >= 500) return 'danger'
  if (code >= 400) return 'warning'
  return 'success'
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-900 tracking-tight">操作日志审计</div>
          <div class="text-xs text-slate-400 mt-1">对关键 API 请求进行留痕，便于追踪与安全审计</div>
        </div>
        <div class="flex items-center gap-2">
          <ElButton :loading="loading" @click="load">刷新</ElButton>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-2 flex-wrap">
          <ElInput v-model="q" placeholder="搜索路径/用户/状态码…" clearable class="w-[280px]" />
          <div class="flex items-center gap-2 px-3 py-2 rounded-xl border bg-slate-50">
            <LucideIcon name="filter" class="w-4 h-4 text-slate-500" />
            <ElSelect v-model="methodFilter" size="small" class="w-24">
              <el-option label="全部" value="all" />
              <el-option label="GET" value="GET" />
              <el-option label="POST" value="POST" />
              <el-option label="PATCH" value="PATCH" />
              <el-option label="PUT" value="PUT" />
              <el-option label="DELETE" value="DELETE" />
            </ElSelect>
          </div>
        </div>
        <ElTag type="info" effect="light">显示 {{ filtered.length }} 条</ElTag>
      </div>
    </div>

    <div v-if="filtered.length" class="space-y-3">
      <div
        v-for="l in filtered"
        :key="l.id"
        class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6"
      >
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <ElTag size="small" effect="light" :type="statusTone(l.status_code)">{{ l.status_code }}</ElTag>
              <ElTag size="small" effect="light" type="info">{{ l.method }}</ElTag>
              <span class="text-xs font-mono text-slate-500 truncate">{{ l.path }}</span>
            </div>
            <div class="mt-2 text-xs text-slate-400">
              时间：<span class="font-mono">{{ fmtDateTime(l.created_at) }}</span>
              <span class="mx-2 text-slate-300">·</span>
              耗时：<span class="font-mono">{{ l.duration_ms }}ms</span>
              <span class="mx-2 text-slate-300">·</span>
              IP：<span class="font-mono">{{ l.ip }}</span>
            </div>
            <div class="mt-2 text-xs text-slate-500">
              用户：{{ l.user?.real_name || l.user?.username || '匿名/系统' }}
            </div>
          </div>
          <ElTag size="small" effect="light" type="info">#{{ l.id }}</ElTag>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      title="暂无审计日志"
      desc="触发一些 API 操作（登录、提交问卷、创建干预等）后，这里会展示留痕记录。"
      icon="shield-check"
    />
  </div>
</template>

