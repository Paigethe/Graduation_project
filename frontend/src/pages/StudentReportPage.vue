<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElDrawer, ElMessage, ElSelect, ElTag } from 'element-plus'

import { api } from '../api/client'
import type { AssessmentResult, PageResp, RiskAlert } from '../api/types'
import { clampText, fmtDateTime } from '../app/format'
import { riskLabel, riskPillClass, riskTone } from '../app/risk'
import EmptyState from '../components/EmptyState.vue'
import LucideIcon from '../components/LucideIcon.vue'

const loading = ref(false)
const items = ref<AssessmentResult[]>([])
const alerts = ref<RiskAlert[]>([])

const filter = ref<'all' | 'low' | 'medium' | 'high'>('all')
const selected = ref<AssessmentResult | null>(null)
const drawerOpen = ref(false)

function toList<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) return payload as T[]
  if (payload && typeof payload === 'object' && Array.isArray((payload as any).results)) {
    return (payload as any).results as T[]
  }
  return []
}

const filtered = computed(() => {
  if (filter.value === 'all') return items.value
  return items.value.filter((i) => i.risk_level === filter.value)
})

const dims = computed(() => {
  const d = selected.value?.dimension_scores ?? {}
  return Object.entries(d).sort((a, b) => b[1] - a[1])
})

function dimLabel(key: string) {
  const map: Record<string, string> = {
    overall: '总体',
    anxiety: '焦虑',
    depression: '抑郁',
    somatization: '躯体化',
    interpersonal: '人际敏感',
    compulsive: '强迫症状',
    hostility: '敌对',
    paranoid: '偏执',
    psychoticism: '精神病性',
    sleep: '睡眠',
    stress: '压力',
  }
  return map[key] ?? key
}

function topDimText(a: AssessmentResult) {
  const entries = Object.entries(a.dimension_scores ?? {}).sort((x, y) => y[1] - x[1])
  const top = entries[0]
  if (!top) return '维度最高：—'
  return `维度最高：${dimLabel(top[0])} (${Number(top[1]).toFixed(2)})`
}

function fmtConfidence(value: unknown) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  const clamped = Math.min(1, Math.max(0, n))
  return `${(clamped * 100).toFixed(1)}%`
}

async function load() {
  loading.value = true
  try {
    const [aResp, alertResp] = await Promise.all([
      api.get<PageResp<AssessmentResult>>('/api/assessments/results/'),
      api.get<PageResp<RiskAlert>>('/api/assessments/alerts/'),
    ])
    items.value = toList<AssessmentResult>(aResp.data)
    alerts.value = toList<RiskAlert>(alertResp.data)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function openDetail(a: AssessmentResult) {
  selected.value = a
  drawerOpen.value = true
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-900 tracking-tight">分析报告</div>
          <div class="text-xs text-slate-400 mt-1">查看测评评估结果、维度得分与风险预警</div>
        </div>
        <div class="flex items-center gap-2 flex-wrap justify-end">
          <div class="flex items-center gap-2 px-3 py-2 rounded-xl border bg-slate-50">
            <LucideIcon name="filter" class="w-4 h-4 text-slate-500" />
            <ElSelect v-model="filter" size="small" class="w-28">
              <el-option label="全部" value="all" />
              <el-option label="安全" value="low" />
              <el-option label="关注" value="medium" />
              <el-option label="高风险" value="high" />
            </ElSelect>
          </div>
          <ElButton :loading="loading" @click="load">刷新</ElButton>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 space-y-4">
        <div v-if="filtered.length" class="space-y-3">
          <button
            v-for="a in filtered"
            :key="a.id"
            class="w-full text-left bg-white rounded-2xl border border-slate-100 shadow-sm p-6 hover:shadow-md transition"
            @click="openDetail(a)"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <div class="font-bold text-slate-900 truncate">{{ a.questionnaire?.title }}</div>
                <div class="text-xs text-slate-400 mt-1">
                  {{ fmtDateTime(a.created_at) }} · 平均得分 {{ a.avg_score?.toFixed?.(2) ?? a.avg_score }}
                </div>
                <div class="mt-3 text-sm text-slate-600">
                  {{ clampText(topDimText(a), 60) }}
                </div>
              </div>
              <div class="flex-shrink-0 text-right">
                <div class="text-xs font-bold px-2 py-1 rounded-lg border" :class="riskPillClass(a.risk_level)">
                  {{ riskLabel(a.risk_level) }}
                </div>
                <div class="mt-2 text-[10px] text-slate-400">
                  预测：{{ riskLabel(a.predicted_risk_level) }} · 置信度：{{ fmtConfidence(a.model_meta?.confidence) }}
                </div>
              </div>
            </div>
          </button>
        </div>

        <EmptyState
          v-else
          title="暂无评估报告"
          desc="先完成一次在线测评，系统会自动生成评估结果与风险等级。"
          icon="file-text"
        />
      </div>

      <div class="space-y-4">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="font-bold text-slate-800">风险预警</div>
          <div v-if="alerts.length" class="mt-4 space-y-3">
            <div
              v-for="a in alerts.slice(0, 6)"
              :key="a.id"
              class="p-4 rounded-xl border border-slate-100 bg-slate-50/50"
            >
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold px-2 py-1 rounded-lg border" :class="riskPillClass(a.level)">
                  {{ riskLabel(a.level) }}
                </span>
                <span class="text-[10px] font-mono text-slate-400">{{ fmtDateTime(a.created_at) }}</span>
                <ElTag v-if="a.is_acknowledged" size="small" type="success" effect="light">已确认</ElTag>
              </div>
              <div class="mt-2 text-xs text-slate-600 leading-relaxed">{{ a.message }}</div>
            </div>
          </div>
          <div v-else class="mt-4">
            <EmptyState title="暂无预警" desc="系统未检测到需要跟进的风险表述。" icon="shield-check" />
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="font-bold text-slate-800">建议</div>
          <div class="mt-3 text-xs text-slate-500 leading-relaxed space-y-2">
            <p>1) 风险等级为“关注/高风险”时，建议尽快联系咨询教师并持续跟进。</p>
            <p>2) 评估结果仅用于筛查与辅助决策，不替代专业诊断。</p>
          </div>
        </div>
      </div>
    </div>

    <ElDrawer v-model="drawerOpen" size="520px" :with-header="false">
      <div v-if="selected" class="p-6 space-y-4">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="text-sm font-black text-slate-900 truncate">{{ selected.questionnaire?.title }}</div>
            <div class="text-xs text-slate-400 mt-1">{{ fmtDateTime(selected.created_at) }}</div>
          </div>
          <div class="text-right flex-shrink-0">
            <div class="text-xs font-bold px-2 py-1 rounded-lg border" :class="riskPillClass(selected.risk_level)">
              {{ riskLabel(selected.risk_level) }}
            </div>
            <div class="mt-2 text-[10px] text-slate-400">
              预测：{{ riskLabel(selected.predicted_risk_level) }} · 置信度：{{ fmtConfidence(selected.model_meta?.confidence) }}
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="bg-slate-50 rounded-xl border border-slate-100 p-4">
            <div class="text-[10px] font-bold tracking-widest text-slate-400">总分</div>
            <div class="mt-1 text-lg font-black text-slate-900">{{ selected.total_score?.toFixed?.(2) ?? selected.total_score }}</div>
          </div>
          <div class="bg-slate-50 rounded-xl border border-slate-100 p-4">
            <div class="text-[10px] font-bold tracking-widest text-slate-400">平均分</div>
            <div class="mt-1 text-lg font-black text-slate-900">{{ selected.avg_score?.toFixed?.(2) ?? selected.avg_score }}</div>
          </div>
        </div>

        <div class="bg-slate-50 rounded-xl border border-slate-100 p-4">
          <div class="text-[10px] font-bold tracking-widest text-slate-400">模型信息</div>
          <div class="mt-2 text-xs text-slate-600">
            版本：{{ selected.model_meta?.model_version || '—' }} · 置信度：{{ fmtConfidence(selected.model_meta?.confidence) }}
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <div class="font-bold text-slate-800">维度得分</div>
          <div v-if="dims.length" class="mt-4 space-y-3">
            <div v-for="[k, v] in dims" :key="k" class="space-y-1">
              <div class="flex items-center justify-between gap-3">
                <div class="text-xs font-bold text-slate-600">{{ dimLabel(k) }}</div>
                <div class="text-xs font-mono text-slate-400">{{ Number(v).toFixed(2) }}</div>
              </div>
              <div class="h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  class="h-2 rounded-full"
                  :class="selected.risk_level === 'high' ? 'bg-rose-500' : selected.risk_level === 'medium' ? 'bg-amber-500' : 'bg-emerald-500'"
                  :style="{ width: Math.min(100, Math.max(0, Number(v) / 5 * 100)) + '%' }"
                />
              </div>
            </div>
          </div>
          <div v-else class="mt-4 text-xs text-slate-400">暂无维度数据</div>
        </div>

        <div class="flex gap-2">
          <ElButton class="flex-1" @click="drawerOpen = false">关闭</ElButton>
          <ElButton class="flex-1" :type="riskTone(selected.risk_level)" @click="drawerOpen = false">
            {{ selected.risk_level === 'high' ? '建议发起咨询' : '我知道了' }}
          </ElButton>
        </div>
      </div>
    </ElDrawer>
  </div>
</template>
