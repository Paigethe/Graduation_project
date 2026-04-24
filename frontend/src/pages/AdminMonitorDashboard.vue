<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElMessage, ElProgress, ElTag } from 'element-plus'

import { api } from '../api/client'
import type { PageResp, RiskAlert } from '../api/types'
import { fmtDateTime } from '../app/format'

type AuditLog = {
  id: number
  created_at: string
  duration_ms: number
  status_code: number
  method: string
  path: string
}

const loading = ref(false)

const usersCount = ref(0)
const collegesCount = ref(0)
const assessmentsCount = ref(0)
const alertsCount = ref(0)
const unAckAlerts = ref(0)
const auditLogs = ref<AuditLog[]>([])

const avgApiMs = computed(() => {
  if (!auditLogs.value.length) return 0
  const sum = auditLogs.value.reduce((acc, l) => acc + Number(l.duration_ms || 0), 0)
  return Math.round(sum / auditLogs.value.length)
})

const bars = computed(() => {
  const list = auditLogs.value.slice(0, 12).map((l) => Math.min(160, Math.max(12, Number(l.duration_ms || 0))))
  return list.length ? list.reverse() : [12, 45, 23, 89, 120, 34, 12, 67, 43, 22]
})

async function load() {
  loading.value = true
  try {
    const [uResp, cResp, aResp, alertResp, logResp] = await Promise.all([
      api.get<PageResp<any>>('/api/admin/users/'),
      api.get<PageResp<any>>('/api/colleges/'),
      api.get<PageResp<any>>('/api/assessments/results/'),
      api.get<PageResp<RiskAlert>>('/api/assessments/alerts/'),
      api.get<PageResp<AuditLog>>('/api/admin/audit-logs/'),
    ])
    usersCount.value = uResp.data.count ?? 0
    collegesCount.value = cResp.data.count ?? (cResp.data.results?.length ?? 0)
    assessmentsCount.value = aResp.data.count ?? 0
    alertsCount.value = alertResp.data.count ?? 0
    unAckAlerts.value = (alertResp.data.results ?? []).filter((x) => !x.is_acknowledged).length
    auditLogs.value = logResp.data.results ?? []
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function pct(n: number, max = 1000) {
  return Math.min(100, Math.round((n / max) * 100))
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-900 tracking-tight">运维状态监控</div>
          <div class="text-xs text-slate-400 mt-1">系统管理员视角：数据规模、预警状态与请求审计概览</div>
        </div>
        <ElButton :loading="loading" @click="load">刷新</ElButton>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="p-5 rounded-2xl shadow-sm border border-slate-100 bg-gradient-to-br from-white to-slate-50">
        <p class="text-[10px] font-bold tracking-widest text-slate-400 mb-1">用户总数</p>
        <p class="text-2xl font-black text-slate-900">{{ usersCount }}</p>
        <ElProgress :percentage="pct(usersCount, 200)" :show-text="false" color="#4f46e5" :stroke-width="4" class="mt-3" />
      </div>

      <div class="p-5 rounded-2xl shadow-sm border border-slate-100 bg-gradient-to-br from-white to-slate-50">
        <p class="text-[10px] font-bold tracking-widest text-slate-400 mb-1">学院总数</p>
        <p class="text-2xl font-black text-slate-900">{{ collegesCount }}</p>
        <ElProgress :percentage="pct(collegesCount, 30)" :show-text="false" color="#16a34a" :stroke-width="4" class="mt-3" />
      </div>

      <div class="p-5 rounded-2xl shadow-sm border border-slate-100 bg-gradient-to-br from-white to-slate-50">
        <p class="text-[10px] font-bold tracking-widest text-slate-400 mb-1">评估样本</p>
        <p class="text-2xl font-black text-slate-900">{{ assessmentsCount }}</p>
        <ElProgress :percentage="pct(assessmentsCount, 500)" :show-text="false" color="#0ea5e9" :stroke-width="4" class="mt-3" />
      </div>

      <div class="p-5 rounded-2xl shadow-sm border border-slate-100 bg-gradient-to-br from-white to-slate-50">
        <p class="text-[10px] font-bold tracking-widest text-slate-400 mb-1">预警 / 未处理</p>
        <p class="text-2xl font-black text-slate-900">{{ alertsCount }} <span class="text-sm text-slate-400">/ {{ unAckAlerts }}</span></p>
        <ElProgress :percentage="pct(unAckAlerts, Math.max(alertsCount, 1))" :show-text="false" color="#e11d48" :stroke-width="4" class="mt-3" />
      </div>
    </div>

    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <div class="font-bold text-slate-800">API 请求审计（最近）</div>
          <div class="text-xs text-slate-400 mt-1">基于审计日志计算的响应时延分布（示例）</div>
        </div>
        <ElTag type="info" effect="light">平均 {{ avgApiMs }}ms</ElTag>
      </div>

      <div class="mt-4 h-48 flex items-end justify-between px-4 pb-4 bg-slate-50 rounded-2xl border border-slate-100">
        <div
          v-for="(h, idx) in bars"
          :key="idx"
          class="w-8 bg-indigo-500 rounded-t transition-all hover:bg-indigo-400"
          :style="{ height: h + 'px' }"
        ></div>
      </div>

      <div v-if="auditLogs.length" class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
        <div
          v-for="l in auditLogs.slice(0, 6)"
          :key="l.id"
          class="p-4 rounded-xl border border-slate-100 bg-white"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="text-xs font-mono text-slate-600 truncate">{{ l.method }} {{ l.path }}</div>
            <ElTag size="small" effect="light" :type="l.status_code >= 500 ? 'danger' : l.status_code >= 400 ? 'warning' : 'success'">
              {{ l.status_code }}
            </ElTag>
          </div>
          <div class="mt-2 text-[10px] text-slate-400 font-mono">
            {{ fmtDateTime(l.created_at) }} · {{ l.duration_ms }}ms
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
