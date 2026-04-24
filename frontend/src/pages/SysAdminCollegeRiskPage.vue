<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElMessage, ElProgress, ElSelect, ElTable, ElTableColumn, ElTag } from 'element-plus'

import { api } from '../api/client'
import EmptyState from '../components/EmptyState.vue'

type CollegeRiskItem = {
  college_id: number
  college_name: string
  assessments_count: number
  high_risk_count: number
  high_risk_rate: number
  unack_alert_count: number
  open_intervention_count: number
}

const loading = ref(false)
const days = ref(90)
const items = ref<CollegeRiskItem[]>([])

const totalAssessments = computed(() => items.value.reduce((acc, cur) => acc + Number(cur.assessments_count || 0), 0))
const totalHighRisk = computed(() => items.value.reduce((acc, cur) => acc + Number(cur.high_risk_count || 0), 0))
const avgHighRate = computed(() => {
  if (!items.value.length) return 0
  const v = items.value.reduce((acc, cur) => acc + Number(cur.high_risk_rate || 0), 0)
  return v / items.value.length
})

function pct(v: number) {
  const n = Math.max(0, Math.min(1, Number(v || 0)))
  return Number((n * 100).toFixed(2))
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<{ items: CollegeRiskItem[] }>('/api/reports/college-risk-overview/', {
      params: { days: days.value },
    })
    items.value = data.items ?? []
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-900 tracking-tight">学院风险分析</div>
          <div class="text-xs text-slate-400 mt-1">系统管理员视角：按学院对比风险率、未确认预警与干预积压</div>
        </div>
        <div class="flex items-center gap-2">
          <ElSelect v-model="days" class="w-36">
            <el-option :value="30" label="近 30 天" />
            <el-option :value="90" label="近 90 天" />
            <el-option :value="180" label="近 180 天" />
          </ElSelect>
          <ElButton :loading="loading" @click="load">刷新</ElButton>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="p-5 rounded-2xl shadow-sm border border-slate-100 bg-gradient-to-br from-white to-slate-50">
        <p class="text-[10px] font-bold tracking-widest text-slate-400 mb-1">评估样本</p>
        <p class="text-2xl font-black text-slate-900">{{ totalAssessments }}</p>
      </div>
      <div class="p-5 rounded-2xl shadow-sm border border-slate-100 bg-gradient-to-br from-white to-slate-50">
        <p class="text-[10px] font-bold tracking-widest text-slate-400 mb-1">高风险人数</p>
        <p class="text-2xl font-black text-rose-700">{{ totalHighRisk }}</p>
      </div>
      <div class="p-5 rounded-2xl shadow-sm border border-slate-100 bg-gradient-to-br from-white to-slate-50">
        <p class="text-[10px] font-bold tracking-widest text-slate-400 mb-1">平均高风险占比</p>
        <p class="text-2xl font-black text-slate-900">{{ pct(avgHighRate) }}%</p>
      </div>
    </div>

    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <ElTable v-if="items.length" :data="items" style="width: 100%">
        <ElTableColumn label="学院" min-width="180">
          <template #default="{ row }">
            <div class="font-semibold text-slate-800">{{ row.college_name }}</div>
            <div class="text-xs text-slate-400">#{{ row.college_id }}</div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="评估样本" prop="assessments_count" width="120" />
        <ElTableColumn label="高风险" prop="high_risk_count" width="110" />
        <ElTableColumn label="高风险率" min-width="220">
          <template #default="{ row }">
            <div class="flex items-center gap-3">
              <ElProgress :percentage="pct(row.high_risk_rate)" :show-text="false" :stroke-width="8" color="#e11d48" class="w-40" />
              <span class="text-xs font-mono text-slate-600">{{ pct(row.high_risk_rate) }}%</span>
            </div>
          </template>
        </ElTableColumn>
        <ElTableColumn label="未确认预警" width="130">
          <template #default="{ row }">
            <ElTag :type="row.unack_alert_count > 0 ? 'warning' : 'success'" effect="light">{{ row.unack_alert_count }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="进行中干预" width="130">
          <template #default="{ row }">
            <ElTag :type="row.open_intervention_count > 0 ? 'danger' : 'info'" effect="light">{{ row.open_intervention_count }}</ElTag>
          </template>
        </ElTableColumn>
      </ElTable>

      <EmptyState
        v-else
        title="暂无学院风险数据"
        desc="请先让学生产生评估结果，或切换统计窗口后刷新。"
        icon="bar-chart-3"
      />
    </div>
  </div>
</template>
