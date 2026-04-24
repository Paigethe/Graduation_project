<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElMessage, ElTag } from 'element-plus'

import { api } from '../api/client'
import { fetchAll } from '../api/pagination'
import type { AssessmentResult, InterventionPlan, PageResp, Questionnaire, RiskAlert } from '../api/types'
import type { MenuId } from '../app/menu'
import { fmtDateTime } from '../app/format'
import { riskLabel, riskPillClass } from '../app/risk'
import EmptyState from '../components/EmptyState.vue'
import StatCard from '../components/StatCard.vue'

const props = defineProps<{ onNavigate?: (id: MenuId) => void }>()

const loading = ref(false)
const assessments = ref<AssessmentResult[]>([])
const alerts = ref<RiskAlert[]>([])
const plans = ref<InterventionPlan[]>([])
const questionnairesCount = ref(0)
const knowledgeCount = ref(0)

const unAckAlerts = computed(() => alerts.value.filter((a) => !a.is_acknowledged))

const riskDist = computed(() => {
  const dist = { low: 0, medium: 0, high: 0 }
  for (const a of assessments.value) {
    if (a.risk_level === 'high') dist.high += 1
    else if (a.risk_level === 'medium') dist.medium += 1
    else dist.low += 1
  }
  return dist
})
const riskTotal = computed(() => riskDist.value.low + riskDist.value.medium + riskDist.value.high || 1)

function pct(n: number) {
  return Math.round((n / riskTotal.value) * 100)
}

async function load() {
  loading.value = true
  try {
    const [assessAll, alertResp, planResp, qResp, kResp] = await Promise.all([
      fetchAll<AssessmentResult>('/api/assessments/results/', 20),
      api.get<PageResp<RiskAlert>>('/api/assessments/alerts/'),
      api.get<PageResp<InterventionPlan>>('/api/interventions/plans/'),
      api.get<PageResp<Questionnaire>>('/api/surveys/questionnaires/'),
      api.get<PageResp<any>>('/api/knowledge/articles/'),
    ])
    assessments.value = assessAll
    alerts.value = alertResp.data.results ?? []
    plans.value = planResp.data.results ?? []
    questionnairesCount.value = qResp.data.count ?? (qResp.data.results?.length ?? 0)
    knowledgeCount.value = kResp.data.count ?? (kResp.data.results?.length ?? 0)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function nav(id: MenuId) {
  props.onNavigate?.(id)
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-900 tracking-tight">学院看板</div>
          <div class="text-xs text-slate-400 mt-1">学院范围内的风险分布、预警跟进、干预进度与报表入口</div>
        </div>
        <div class="flex items-center gap-2">
          <ElButton :loading="loading" @click="load">刷新</ElButton>
          <ElButton type="primary" @click="nav('reports')">生成报表</ElButton>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
      <StatCard icon="file-text" label="评估结果" :value="assessments.length" hint="当前可见范围评估总数" tone="slate" />
      <StatCard icon="alert-triangle" label="待确认预警" :value="unAckAlerts.length" hint="需要学院侧关注/督办" tone="rose" />
      <StatCard icon="shield-check" label="干预建议" :value="plans.length" hint="学院范围内的干预记录" tone="amber" />
      <StatCard icon="clipboard-list" label="已发布问卷" :value="questionnairesCount" hint="学院/全局问卷" tone="indigo" />
      <StatCard icon="book-open" label="知识文章" :value="knowledgeCount" hint="学院推送/全局可见" tone="emerald" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 space-y-4">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div class="font-bold text-slate-800">风险分布</div>
            <ElTag type="info" effect="light">学院范围</ElTag>
          </div>

          <div class="mt-4">
            <div class="h-3 rounded-full overflow-hidden bg-slate-100 flex">
              <div class="h-3 bg-emerald-500" :style="{ width: pct(riskDist.low) + '%' }"></div>
              <div class="h-3 bg-amber-500" :style="{ width: pct(riskDist.medium) + '%' }"></div>
              <div class="h-3 bg-rose-500" :style="{ width: pct(riskDist.high) + '%' }"></div>
            </div>
            <div class="mt-3 grid grid-cols-3 gap-2 text-xs">
              <div class="text-emerald-700">
                安全 <span class="font-mono text-slate-400">({{ riskDist.low }})</span>
              </div>
              <div class="text-amber-700 text-center">
                关注 <span class="font-mono text-slate-400">({{ riskDist.medium }})</span>
              </div>
              <div class="text-rose-700 text-right">
                高风险 <span class="font-mono text-slate-400">({{ riskDist.high }})</span>
              </div>
            </div>
          </div>

          <div class="mt-5 flex gap-2">
            <ElButton size="small" @click="nav('analysis')">进入深度分析</ElButton>
            <ElButton size="small" type="warning" plain @click="nav('progress')">查看干预进度</ElButton>
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div class="font-bold text-slate-800">预警列表（最新）</div>
            <ElButton size="small" @click="nav('progress')">进度监控</ElButton>
          </div>

          <div v-if="alerts.length" class="mt-4 space-y-3">
            <div
              v-for="a in alerts.slice(0, 8)"
              :key="a.id"
              class="p-4 rounded-xl border border-slate-100 bg-slate-50/50 flex items-start justify-between gap-4"
            >
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-xs font-bold px-2 py-1 rounded-lg border" :class="riskPillClass(a.level)">
                    {{ riskLabel(a.level) }}
                  </span>
                  <span class="text-xs font-bold text-slate-700">
                    {{ a.student?.real_name || a.student?.username }}
                  </span>
                  <span class="text-[10px] font-mono text-slate-400">{{ fmtDateTime(a.created_at) }}</span>
                  <ElTag v-if="a.is_acknowledged" size="small" type="success" effect="light">已确认</ElTag>
                  <ElTag v-else size="small" type="warning" effect="light">待确认</ElTag>
                </div>
                <div class="mt-2 text-sm text-slate-600 leading-relaxed">{{ a.message }}</div>
              </div>
            </div>
          </div>

          <div v-else class="mt-4">
            <EmptyState title="暂无预警" desc="系统未检测到需要学院侧跟进的风险事件。" icon="shield-check" />
          </div>
        </div>
      </div>

      <div class="space-y-4">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="font-bold text-slate-800">操作入口</div>
          <div class="mt-4 grid grid-cols-1 gap-3">
            <button class="w-full p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white transition text-left" @click="nav('analysis')">
              <div class="font-bold text-sm text-slate-800">深度统计分析</div>
              <div class="text-xs text-slate-400 mt-0.5">风险分布 / 趋势 / 维度表现</div>
            </button>
            <button class="w-full p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white transition text-left" @click="nav('reports')">
              <div class="font-bold text-sm text-slate-800">月度报表生成</div>
              <div class="text-xs text-slate-400 mt-0.5">一键计算并导出报表</div>
            </button>
            <button class="w-full p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white transition text-left" @click="nav('backup')">
              <div class="font-bold text-sm text-slate-800">学院数据备份</div>
              <div class="text-xs text-slate-400 mt-0.5">导出问卷/评估/干预等数据</div>
            </button>
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="font-bold text-slate-800">说明</div>
          <div class="mt-3 text-xs text-slate-500 leading-relaxed">
            学院侧主要职责是督办风险预警与干预进度，并通过月度报表提供决策支撑；具体咨询内容在人工咨询模块留痕保存。
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
