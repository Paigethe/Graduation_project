<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElMessage, ElTag } from 'element-plus'

import { api } from '../api/client'
import type { AssessmentResult, InterventionPlan, PageResp, Questionnaire, RiskAlert } from '../api/types'
import { fmtDateTime } from '../app/format'
import { interventionSeenStorageKey } from '../app/intervention'
import { riskLabel, riskPillClass } from '../app/risk'
import LucideIcon from '../components/LucideIcon.vue'
import EmptyState from '../components/EmptyState.vue'
import StatCard from '../components/StatCard.vue'
import type { MenuId } from '../app/menu'
import { useAuthStore } from '../stores/auth'

const props = defineProps<{ onNavigate?: (id: MenuId) => void }>()
const auth = useAuthStore()

const loading = ref(false)
const questionnairesCount = ref<number>(0)
const assessments = ref<AssessmentResult[]>([])
const alerts = ref<RiskAlert[]>([])
const plans = ref<InterventionPlan[]>([])

const latestAssessment = computed(() => assessments.value[0])
const latestPendingHighAlert = computed(() => alerts.value.find((alert) => alert.level === 'high' && !alert.is_acknowledged))
const latestMediumAssessment = computed(() => assessments.value.find((item) => item.risk_level === 'medium'))
const seenAt = computed(() => {
  const key = interventionSeenStorageKey(auth.me?.id)
  return localStorage.getItem(key) || ''
})
const newPlanCount = computed(() =>
  plans.value.filter((plan) => {
    const current = String(plan.updated_at || plan.created_at || '')
    return Boolean(current) && current > seenAt.value
  }).length,
)
const currentRiskState = computed(() => {
  const alert = latestPendingHighAlert.value
  const mediumAssessment = latestMediumAssessment.value
  const alertTime = alert?.created_at || ''
  const mediumTime = mediumAssessment?.created_at || ''

  if (alert && (!mediumAssessment || alertTime >= mediumTime)) {
    return {
      label: riskLabel(alert.level),
      tone: 'rose' as const,
      hint: `未确认高风险预警：${fmtDateTime(alert.created_at)}`,
    }
  }
  if (mediumAssessment) {
    return {
      label: riskLabel(mediumAssessment.risk_level),
      tone: 'amber' as const,
      hint: `最近中风险评估：${fmtDateTime(mediumAssessment.created_at)}`,
    }
  }
  if (latestAssessment.value) {
    const risk = latestAssessment.value.risk_level
    return {
      label: riskLabel(risk),
      tone: (risk === 'high' ? 'rose' : risk === 'medium' ? 'amber' : 'emerald') as 'rose' | 'amber' | 'emerald',
      hint: `最近评估：${fmtDateTime(latestAssessment.value.created_at)}`,
    }
  }
  return {
    label: '安全',
    tone: 'emerald' as const,
    hint: '暂未生成评估结果',
  }
})

async function load() {
  loading.value = true
  try {
    const [qResp, aResp, alertResp, planResp] = await Promise.all([
      api.get<PageResp<Questionnaire>>('/api/surveys/questionnaires/'),
      api.get<PageResp<AssessmentResult>>('/api/assessments/results/'),
      api.get<PageResp<RiskAlert>>('/api/assessments/alerts/'),
      api.get<PageResp<InterventionPlan>>('/api/interventions/plans/'),
    ])
    questionnairesCount.value = qResp.data.count ?? (qResp.data.results?.length ?? 0)
    assessments.value = aResp.data.results ?? []
    alerts.value = alertResp.data.results ?? []
    plans.value = planResp.data.results ?? []
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
          <div class="text-sm font-black text-slate-900 tracking-tight">系统首页</div>
          <div class="text-xs text-slate-400 mt-1">
            你的心理健康状态概览（评估 → 预警 → 干预 → 咨询）
          </div>
        </div>

        <div class="flex items-center gap-2">
          <ElButton :loading="loading" @click="load">刷新</ElButton>
          <ElButton type="primary" @click="nav('survey')">开始测评</ElButton>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <StatCard
        icon="clipboard-list"
        label="可用测评"
        :value="questionnairesCount"
        hint="按学院发布的在有效期内问卷"
        clickable
        @click="nav('survey')"
      />
      <StatCard
        icon="file-text"
        label="测评报告"
        :value="assessments.length"
        hint="自动生成评估结果与趋势"
        tone="slate"
        clickable
        @click="nav('report')"
      />
      <StatCard
        icon="shield-check"
        label="当前状态"
        :value="currentRiskState.label"
        :hint="currentRiskState.hint"
        :tone="currentRiskState.tone"
        clickable
        @click="nav('report')"
      />
      <StatCard
        icon="message-circle"
        label="干预建议"
        :value="plans.length"
        hint="来自咨询教师/学院的跟进建议"
        tone="indigo"
        :badge="newPlanCount"
        clickable
        @click="nav('intervention')"
      />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 space-y-4">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div class="font-bold text-slate-800">近期预警</div>
            <ElButton size="small" @click="nav('report')">查看报告</ElButton>
          </div>

          <div v-if="alerts.length" class="mt-4 space-y-3">
            <div
              v-for="a in alerts.slice(0, 6)"
              :key="a.id"
              class="flex items-start justify-between gap-4 p-4 rounded-xl border border-slate-100 bg-slate-50/50"
            >
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-bold px-2 py-1 rounded-lg border" :class="riskPillClass(a.level)">
                    {{ riskLabel(a.level) }}
                  </span>
                  <span class="text-xs text-slate-400">{{ fmtDateTime(a.created_at) }}</span>
                  <ElTag v-if="a.is_acknowledged" size="small" type="success" effect="light">已确认</ElTag>
                  <ElTag v-else size="small" type="warning" effect="light">待确认</ElTag>
                </div>
                <div class="mt-2 text-sm text-slate-700 leading-relaxed">{{ a.message }}</div>
              </div>
            </div>
          </div>

          <div v-else class="mt-4">
            <EmptyState title="暂无预警" desc="保持良好的作息与运动，定期完成测评。" icon="shield-check" />
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div class="flex items-center gap-2">
              <div class="font-bold text-slate-800">干预建议与跟进</div>
              <span
                v-if="newPlanCount"
                class="inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full bg-rose-500 text-white text-[10px] font-bold"
              >
                {{ newPlanCount }}
              </span>
            </div>
            <div class="flex items-center gap-2">
              <ElButton size="small" @click="nav('intervention')">查看全部</ElButton>
              <ElButton size="small" @click="nav('consult')">人工咨询</ElButton>
            </div>
          </div>

          <div v-if="plans.length" class="mt-4 space-y-3">
            <button
              v-for="p in plans.slice(0, 4)"
              :key="p.id"
              class="w-full text-left p-4 rounded-xl border border-slate-100 hover:border-indigo-200 hover:bg-indigo-50/30 transition"
              @click="nav('intervention')"
            >
              <div class="flex items-center justify-between gap-3 flex-wrap">
                <div class="flex items-center gap-2 min-w-0">
                  <div class="font-bold text-slate-800 truncate">{{ p.title }}</div>
                  <span
                    v-if="String(p.updated_at || p.created_at || '') > seenAt"
                    class="inline-flex w-2.5 h-2.5 rounded-full bg-rose-500 flex-shrink-0"
                  />
                </div>
                <div class="text-[10px] font-mono text-slate-400">
                  更新：{{ fmtDateTime(p.updated_at) || fmtDateTime(p.created_at) }}
                </div>
              </div>
              <div class="mt-2 text-sm text-slate-600 whitespace-pre-wrap leading-relaxed">{{ p.content }}</div>
              <div class="mt-3 flex items-center justify-between gap-3 flex-wrap">
                <span class="text-xs text-slate-400">
                  咨询教师：{{ p.counselor?.real_name || p.counselor?.username || '—' }}
                </span>
                <span
                  v-if="p.knowledge_article?.title"
                  class="text-xs text-indigo-600 font-semibold truncate"
                >
                  已关联知识卡片：{{ p.knowledge_article.title }}
                </span>
              </div>
            </button>
          </div>

          <div v-else class="mt-4">
            <EmptyState title="暂无干预建议" desc="完成测评后，系统会在需要时生成预警并通知教师跟进。" icon="sparkles" />
          </div>
        </div>
      </div>

      <div class="space-y-4">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="font-bold text-slate-800">快捷入口</div>
          <div class="mt-4 grid grid-cols-1 gap-3">
            <button
              class="w-full flex items-center justify-between gap-3 p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white transition"
              @click="nav('knowledge')"
            >
              <div class="flex items-center gap-3">
                <span class="p-2 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100">
                  <LucideIcon name="book-open" class="w-4 h-4" />
                </span>
                <div class="text-left">
                  <div class="font-bold text-sm text-slate-800">心理知识库</div>
                  <div class="text-xs text-slate-400 mt-0.5">情绪调节 / 压力缓解 / 人际适应</div>
                </div>
              </div>
              <span class="text-xs text-slate-400">进入</span>
            </button>

            <button
              class="w-full flex items-center justify-between gap-3 p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white transition"
              @click="nav('ai_chat')"
            >
              <div class="flex items-center gap-3">
                <span class="p-2 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100">
                  <LucideIcon name="brain-circuit" class="w-4 h-4" />
                </span>
                <div class="text-left">
                  <div class="font-bold text-sm text-slate-800">AI 自助咨询</div>
                  <div class="text-xs text-slate-400 mt-0.5">24 小时支持 + 风险初筛提示</div>
                </div>
              </div>
              <span class="text-xs text-slate-400">进入</span>
            </button>

            <button
              class="w-full flex items-center justify-between gap-3 p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white transition"
              @click="nav('consult')"
            >
              <div class="flex items-center gap-3">
                <span class="p-2 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100">
                  <LucideIcon name="users" class="w-4 h-4" />
                </span>
                <div class="text-left">
                  <div class="font-bold text-sm text-slate-800">人工咨询</div>
                  <div class="text-xs text-slate-400 mt-0.5">与已分配的咨询教师沟通</div>
                </div>
              </div>
              <span class="text-xs text-slate-400">进入</span>
            </button>
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="font-bold text-slate-800">提示</div>
          <div class="mt-3 text-xs text-slate-500 leading-relaxed">
            系统不会替代专业诊断。若你出现持续失眠、情绪低落或强烈自伤念头，请优先联系学校心理老师或拨打当地紧急求助电话。
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
