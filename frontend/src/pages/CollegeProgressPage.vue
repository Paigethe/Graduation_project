<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElAlert, ElButton, ElMessage, ElProgress, ElSwitch, ElTable, ElTableColumn, ElTag } from 'element-plus'

import { api } from '../api/client'
import type { InterventionPlan, PageResp, RiskAlert } from '../api/types'
import { fmtDateTime } from '../app/format'
import { interventionProgressPercent, interventionStatusLabel, interventionStatusType } from '../app/intervention'
import { riskLabel, riskPillClass } from '../app/risk'
import EmptyState from '../components/EmptyState.vue'

const loading = ref(false)
const plans = ref<InterventionPlan[]>([])
const alerts = ref<RiskAlert[]>([])
const includeDone = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const alertsByStudent = computed(() => {
  const map = new Map<number, RiskAlert[]>()
  for (const a of alerts.value) {
    const sid = a.student?.id
    if (!sid) continue
    map.set(sid, [...(map.get(sid) ?? []), a])
  }
  return map
})
const latestAlertByStudent = computed(() => {
  const map = new Map<number, RiskAlert | null>()
  for (const plan of plans.value) {
    const sid = plan.student?.id
    if (!sid) continue
    map.set(sid, (alertsByStudent.value.get(sid) ?? [])[0] ?? null)
  }
  return map
})

const unAckHighCount = computed(() => alerts.value.filter((a) => a.level === 'high' && !a.is_acknowledged).length)
const displayPlans = computed(() => (includeDone.value ? plans.value : plans.value.filter((p) => p.status !== 'done')))

function progressStatus(status: string): 'success' | 'exception' | 'warning' {
  if (status === 'done') return 'success'
  if (status === 'draft') return 'exception'
  return 'warning'
}

async function load() {
  loading.value = true
  try {
    const [planResp, alertResp] = await Promise.all([
      api.get<PageResp<InterventionPlan>>('/api/interventions/plans/'),
      api.get<PageResp<RiskAlert>>('/api/assessments/alerts/'),
    ])
    plans.value = planResp.data.results ?? []
    alerts.value = alertResp.data.results ?? []
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  refreshTimer = setInterval(() => {
    load()
  }, 15000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<template>
  <div class="space-y-6">
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-900 tracking-tight">干预进度监控</div>
          <div class="text-xs text-slate-400 mt-1">按学院范围汇总干预建议进度与风险预警状态</div>
        </div>
        <div class="flex items-center gap-3">
          <div class="text-xs text-slate-500 flex items-center gap-2">
            显示已完成
            <ElSwitch v-model="includeDone" />
          </div>
          <ElButton :loading="loading" @click="load">刷新</ElButton>
        </div>
      </div>
    </div>

    <ElAlert
      v-if="unAckHighCount"
      :title="`预警提醒：当前有 ${unAckHighCount} 条“高风险”预警未确认，请及时督促跟进。`"
      type="warning"
      show-icon
    />
    <ElAlert v-else title="当前暂无未确认的高风险预警。" type="success" show-icon />

    <div v-if="displayPlans.length" class="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
      <ElTable :data="displayPlans" style="width: 100%">
        <ElTableColumn label="学生">
          <template #default="{ row }">
            <div class="font-bold text-slate-800">{{ row.student?.real_name || row.student?.username }}</div>
            <div class="text-[10px] text-slate-400">{{ row.student?.college?.name || '—' }}</div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="负责辅导员">
          <template #default="{ row }">
            {{ row.counselor?.real_name || row.counselor?.username || '—' }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="干预进度">
          <template #default="{ row }">
            <ElProgress :percentage="interventionProgressPercent(row.status)" :status="progressStatus(row.status)" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="状态">
          <template #default="{ row }">
            <ElTag size="small" effect="light" :type="interventionStatusType(row.status)">
              {{ interventionStatusLabel(row.status) }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="最新预警">
          <template #default="{ row }">
            <div v-if="latestAlertByStudent.get(row.student?.id)" class="space-y-1">
              <span
                class="inline-flex text-[10px] font-bold px-2 py-1 rounded-lg border"
                :class="riskPillClass(latestAlertByStudent.get(row.student?.id)?.level || '')"
              >
                {{ riskLabel(latestAlertByStudent.get(row.student?.id)?.level || '') }}
              </span>
              <div class="text-[10px] text-slate-400">
                {{ latestAlertByStudent.get(row.student?.id)?.is_acknowledged ? '已处理' : '未处理' }}
              </div>
            </div>
            <div v-else class="text-xs text-slate-400">—</div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="预警说明">
          <template #default="{ row }">
            <div class="text-xs text-slate-500 leading-relaxed">
              {{ latestAlertByStudent.get(row.student?.id)?.message || '暂无预警说明' }}
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="更新时间" width="160">
          <template #default="{ row }">
            <span class="text-xs text-slate-500 font-mono">{{ fmtDateTime(row.updated_at) }}</span>
          </template>
        </ElTableColumn>
      </ElTable>
    </div>

    <EmptyState
      v-else
      title="暂无干预数据"
      desc="当咨询教师创建干预建议后，这里将展示跟踪进度与预警状态。"
      icon="shield-check"
    />
  </div>
</template>
