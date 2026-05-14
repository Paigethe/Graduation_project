<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElCard, ElCheckbox, ElCheckboxGroup, ElDatePicker, ElForm, ElFormItem, ElMessage, ElTag } from 'element-plus'

import { api, downloadWithAuth } from '../api/client'
import { fmtDateTime } from '../app/format'
import EmptyState from '../components/EmptyState.vue'
import LucideIcon from '../components/LucideIcon.vue'

type ReportMetric = '风险分布' | '干预效果' | '预警趋势' | '问卷提交' | '复测改善'

const ALL_REPORT_METRICS: ReportMetric[] = ['风险分布', '干预效果', '预警趋势', '问卷提交', '复测改善']

type ReportSummary = {
  metrics?: ReportMetric[]
  period?: {
    label?: string
    month_start?: string
    month_end?: string
  }
  assessments?: {
    count?: number
    avg_score?: number
    risk_distribution?: {
      low?: number
      medium?: number
      high?: number
      low_ratio?: number
      medium_ratio?: number
      high_ratio?: number
    }
    top_dimensions?: Array<{
      key: string
      name: string
      avg_score: number
      sample_count: number
    }>
  }
  alerts?: {
    count?: number
    unack_count?: number
    high_unack_count?: number
    trend?: {
      previous_period_label?: string | null
      alert_change_pct?: number | null
      high_unack_change_pct?: number | null
    }
  }
  interventions?: {
    count?: number
    intervention_rate?: number
    counselor_involved_rate?: number
    high_risk_student_count?: number
    intervened_high_risk_student_count?: number
    feedback_status_distribution?: {
      draft?: number
      sent?: number
      in_progress?: number
      done?: number
      no_intervention?: number
    }
  }
  retest?: {
    completed_task_count?: number
    baseline_high_risk_count?: number
    improved_count?: number
    improved_to_safe_count?: number
    improvement_rate?: number
  }
  comparisons?: {
    previous_period_label?: string | null
    assessment_change_pct?: number | null
    high_risk_change_pct?: number | null
  }
  questionnaires?: {
    questionnaires_count?: number
    responses_count?: number
  }
}

type ReportItem = {
  name: string
  pdf_name?: string | null
  meta: {
    college_id: number
    college_name?: string
    month?: string | null
    month_start?: string
    month_end?: string
    period_label?: string
    created_at: string
  }
  summary: ReportSummary
}

const loading = ref(false)
const generating = ref(false)

const reportRange = ref<string[]>([])
const reportMetrics = ref<string[]>(['风险分布', '干预效果', '预警趋势', '复测改善'])

const items = ref<ReportItem[]>([])
const latest = computed(() => items.value[0])
const latestMetrics = computed(() => selectedMetrics(latest.value))

function percentText(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${Number(value).toFixed(2)}%`
}

function periodText(meta?: ReportItem['meta']) {
  if (!meta) return '—'
  return meta.period_label || meta.month || [meta.month_start, meta.month_end].filter(Boolean).join(' 至 ') || '—'
}

function selectedMetrics(report?: ReportItem | null): ReportMetric[] {
  const metrics = report?.summary?.metrics
  if (Array.isArray(metrics) && metrics.length) return metrics
  return ALL_REPORT_METRICS
}

function hasMetric(report: ReportItem | null | undefined, metric: ReportMetric) {
  return selectedMetrics(report).includes(metric)
}

async function loadList() {
  loading.value = true
  try {
    const { data } = await api.get<{ results: ReportItem[] }>('/api/reports/list/')
    items.value = data.results ?? []
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载报表列表失败')
  } finally {
    loading.value = false
  }
}

async function generateReport() {
  if (!Array.isArray(reportRange.value) || reportRange.value.length !== 2) {
    return ElMessage.warning('请选择统计月份范围')
  }
  if (!reportMetrics.value.length) {
    return ElMessage.warning('请至少选择一个报表指标')
  }
  generating.value = true
  try {
    const [month_start, month_end] = reportRange.value
    const { data } = await api.post<ReportItem>('/api/reports/monthly/', {
      month_start,
      month_end,
      metrics: reportMetrics.value,
      format: 'pdf',
    })
    items.value = [data, ...items.value.filter((item) => item.name !== data.name)]
    ElMessage.success('报表已生成')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

function downloadHref(name: string) {
  return `/api/reports/download/?name=${encodeURIComponent(name)}`
}

async function downloadReport(name: string) {
  try {
    await downloadWithAuth(downloadHref(name), name)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '下载失败')
  }
}

onMounted(loadList)
</script>

<template>
  <div class="space-y-6">
    <ElCard shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-bold">月度心理健康分析报告生成</span>
          <ElTag type="success" effect="light">仅导出报告文件</ElTag>
        </div>
      </template>

      <ElForm label-position="left" label-width="100px" class="max-w-2xl">
        <ElFormItem label="统计月份">
          <ElDatePicker
            v-model="reportRange"
            type="monthrange"
            value-format="YYYY-MM"
            start-placeholder="开始月份"
            end-placeholder="结束月份"
            unlink-panels
            class="!w-full"
          />
        </ElFormItem>
        <ElFormItem label="包含指标">
          <ElCheckboxGroup v-model="reportMetrics">
            <ElCheckbox label="风险分布" />
            <ElCheckbox label="干预效果" />
            <ElCheckbox label="预警趋势" />
            <ElCheckbox label="问卷提交" />
            <ElCheckbox label="复测改善" />
          </ElCheckboxGroup>
        </ElFormItem>
        <div class="flex gap-2">
          <ElButton type="primary" class="h-11" :loading="generating" @click="generateReport">
            <LucideIcon name="sparkles" class="w-4 h-4" />
            生成分析报告
          </ElButton>
          <ElButton class="h-11" :loading="loading" @click="loadList">刷新列表</ElButton>
        </div>
      </ElForm>
    </ElCard>

    <div v-if="latest" class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-5">
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <div class="font-bold text-slate-900">最新报告</div>
          <div class="text-xs text-slate-400 mt-1">
            周期：{{ periodText(latest.meta) }} · 生成时间：{{ fmtDateTime(latest.meta.created_at) }}
          </div>
        </div>
        <div class="flex items-center gap-2 flex-wrap justify-end">
          <ElTag v-for="metric in latestMetrics" :key="metric" effect="light" type="info">
            {{ metric }}
          </ElTag>
          <button
            v-if="latest.pdf_name"
            class="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-white transition"
            @click="downloadReport(latest.pdf_name)"
          >
            <LucideIcon name="download" class="w-4 h-4 text-slate-600" />
            <span class="text-sm font-semibold text-slate-700">下载报告文件</span>
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        <div v-if="hasMetric(latest, '风险分布')" class="p-4 rounded-xl border border-slate-100 bg-slate-50/50">
          <div class="text-[10px] font-bold tracking-widest text-slate-400">评估样本</div>
          <div class="mt-1 text-lg font-black text-slate-900">{{ latest.summary?.assessments?.count ?? '—' }}</div>
        </div>
        <div v-if="hasMetric(latest, '风险分布')" class="p-4 rounded-xl border border-slate-100 bg-slate-50/50">
          <div class="text-[10px] font-bold tracking-widest text-slate-400">高风险占比</div>
          <div class="mt-1 text-lg font-black text-slate-900">
            {{ percentText(latest.summary?.assessments?.risk_distribution?.high_ratio) }}
          </div>
        </div>
        <div v-if="hasMetric(latest, '预警趋势')" class="p-4 rounded-xl border border-slate-100 bg-slate-50/50">
          <div class="text-[10px] font-bold tracking-widest text-slate-400">预警总数</div>
          <div class="mt-1 text-lg font-black text-slate-900">{{ latest.summary?.alerts?.count ?? '—' }}</div>
        </div>
        <div v-if="hasMetric(latest, '干预效果')" class="p-4 rounded-xl border border-slate-100 bg-slate-50/50">
          <div class="text-[10px] font-bold tracking-widest text-slate-400">干预介入率</div>
          <div class="mt-1 text-lg font-black text-slate-900">
            {{ percentText(latest.summary?.interventions?.intervention_rate) }}
          </div>
        </div>
        <div v-if="hasMetric(latest, '问卷提交')" class="p-4 rounded-xl border border-slate-100 bg-slate-50/50">
          <div class="text-[10px] font-bold tracking-widest text-slate-400">问卷作答数</div>
          <div class="mt-1 text-lg font-black text-slate-900">
            {{ latest.summary?.questionnaires?.responses_count ?? '—' }}
          </div>
        </div>
        <div v-if="hasMetric(latest, '复测改善')" class="p-4 rounded-xl border border-slate-100 bg-slate-50/50">
          <div class="text-[10px] font-bold tracking-widest text-slate-400">复测改善率</div>
          <div class="mt-1 text-lg font-black text-slate-900">
            {{ percentText(latest.summary?.retest?.improvement_rate) }}
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div v-if="hasMetric(latest, '风险分布')" class="rounded-2xl border border-slate-100 bg-slate-50/40 p-5">
          <div class="font-bold text-slate-800">风险分布与维度表现</div>
          <div class="mt-4 space-y-2 text-sm text-slate-600">
            <div>评估样本：{{ latest.summary?.assessments?.count ?? 0 }} 份</div>
            <div>高风险占比：{{ percentText(latest.summary?.assessments?.risk_distribution?.high_ratio) }}</div>
            <div v-if="latest.summary?.comparisons?.previous_period_label">
              上一周期：{{ latest.summary?.comparisons?.previous_period_label }}
            </div>
            <div v-if="latest.summary?.comparisons?.previous_period_label">
              评估样本变化：{{ percentText(latest.summary?.comparisons?.assessment_change_pct) }}
            </div>
            <div v-if="latest.summary?.comparisons?.previous_period_label">
              高风险人数变化：{{ percentText(latest.summary?.comparisons?.high_risk_change_pct) }}
            </div>
          </div>
          <div v-if="latest.summary?.assessments?.top_dimensions?.length" class="mt-4 space-y-3">
            <div
              v-for="item in latest.summary.assessments.top_dimensions"
              :key="item.key"
              class="flex items-center justify-between gap-3 text-sm"
            >
              <div class="text-slate-700">
                {{ item.name }}
                <span class="text-xs text-slate-400">（{{ item.sample_count }} 份样本）</span>
              </div>
              <div class="font-semibold text-slate-900">{{ Number(item.avg_score).toFixed(2) }}</div>
            </div>
          </div>
          <div v-else class="mt-4 text-sm text-slate-400">暂无维度统计数据</div>
        </div>

        <div v-if="hasMetric(latest, '预警趋势')" class="rounded-2xl border border-slate-100 bg-slate-50/40 p-5">
          <div class="font-bold text-slate-800">预警趋势</div>
          <div class="mt-4 space-y-2 text-sm text-slate-600">
            <div>预警总数：{{ latest.summary?.alerts?.count ?? 0 }} 条</div>
            <div>未处理预警：{{ latest.summary?.alerts?.unack_count ?? 0 }} 条</div>
            <div>高风险未处理：{{ latest.summary?.alerts?.high_unack_count ?? 0 }} 条</div>
            <div v-if="latest.summary?.alerts?.trend?.previous_period_label">
              上一周期：{{ latest.summary?.alerts?.trend?.previous_period_label }}
            </div>
            <div v-if="latest.summary?.alerts?.trend?.previous_period_label">
              预警总数变化：{{ percentText(latest.summary?.alerts?.trend?.alert_change_pct) }}
            </div>
            <div v-if="latest.summary?.alerts?.trend?.previous_period_label">
              高风险未处理变化：{{ percentText(latest.summary?.alerts?.trend?.high_unack_change_pct) }}
            </div>
          </div>
        </div>

        <div v-if="hasMetric(latest, '干预效果')" class="rounded-2xl border border-slate-100 bg-slate-50/40 p-5">
          <div class="font-bold text-slate-800">干预与反馈</div>
          <div class="mt-4 space-y-2 text-sm text-slate-600">
            <div>高风险学生：{{ latest.summary?.interventions?.high_risk_student_count ?? 0 }} 人</div>
            <div>已介入人数：{{ latest.summary?.interventions?.intervened_high_risk_student_count ?? 0 }} 人</div>
            <div>辅导员介入率：{{ percentText(latest.summary?.interventions?.counselor_involved_rate) }}</div>
            <div>
              学生反馈留痕：
              进行中 {{ latest.summary?.interventions?.feedback_status_distribution?.in_progress ?? 0 }}，
              已完成 {{ latest.summary?.interventions?.feedback_status_distribution?.done ?? 0 }}，
              未介入 {{ latest.summary?.interventions?.feedback_status_distribution?.no_intervention ?? 0 }}
            </div>
          </div>
        </div>

        <div v-if="hasMetric(latest, '问卷提交')" class="rounded-2xl border border-slate-100 bg-slate-50/40 p-5">
          <div class="font-bold text-slate-800">问卷提交</div>
          <div class="mt-4 space-y-2 text-sm text-slate-600">
            <div>统计范围内问卷数：{{ latest.summary?.questionnaires?.questionnaires_count ?? 0 }} 份</div>
            <div>统计范围内作答数：{{ latest.summary?.questionnaires?.responses_count ?? 0 }} 次</div>
          </div>
        </div>

        <div v-if="hasMetric(latest, '复测改善')" class="rounded-2xl border border-slate-100 bg-slate-50/40 p-5">
          <div class="font-bold text-slate-800">复测改善</div>
          <div class="mt-4 space-y-2 text-sm text-slate-600">
            <div>已完成复测：{{ latest.summary?.retest?.completed_task_count ?? 0 }} 条</div>
            <div>基线高风险人数：{{ latest.summary?.retest?.baseline_high_risk_count ?? 0 }} 人</div>
            <div>风险下降人数：{{ latest.summary?.retest?.improved_count ?? 0 }} 人</div>
            <div>恢复为安全人数：{{ latest.summary?.retest?.improved_to_safe_count ?? 0 }} 人</div>
            <div>改善率：{{ percentText(latest.summary?.retest?.improvement_rate) }}</div>
          </div>
        </div>
      </div>
    </div>

<!--    <div class="bg-amber-50/70 rounded-2xl border border-amber-100 shadow-sm p-6 space-y-4">-->
<!--      <div class="flex items-start justify-between gap-4 flex-wrap">-->
<!--        <div>-->
<!--          <div class="font-bold text-amber-900">当前勾选预览（Mock）</div>-->
<!--          <div class="text-xs text-amber-700/80 mt-1">-->
<!--            这是前端模拟预览，只用于确认复选框是否生效；真实报表仍以点击“生成分析报告”后的结果为准。-->
<!--          </div>-->
<!--        </div>-->
<!--        <div class="flex items-center gap-2 flex-wrap justify-end">-->
<!--          <ElTag v-for="metric in mockPreviewMetrics" :key="metric" effect="light" type="warning">-->
<!--            {{ metric }}-->
<!--          </ElTag>-->
<!--        </div>-->
<!--      </div>-->

<!--      <div class="text-sm text-amber-900">-->
<!--        统计周期：<span class="font-semibold">{{ mockPreview.period?.label }}</span>-->
<!--      </div>-->

<!--      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">-->
<!--        <div v-if="mockPreviewMetrics.includes('风险分布')" class="p-4 rounded-xl border border-amber-100 bg-white/80">-->
<!--          <div class="text-[10px] font-bold tracking-widest text-amber-700">风险分布</div>-->
<!--          <div class="mt-2 text-sm text-slate-700">-->
<!--            评估样本 {{ mockPreview.assessments?.count }} 份，高风险占比 {{ percentText(mockPreview.assessments?.risk_distribution?.high_ratio) }}-->
<!--          </div>-->
<!--        </div>-->
<!--        <div v-if="mockPreviewMetrics.includes('干预效果')" class="p-4 rounded-xl border border-amber-100 bg-white/80">-->
<!--          <div class="text-[10px] font-bold tracking-widest text-amber-700">干预效果</div>-->
<!--          <div class="mt-2 text-sm text-slate-700">-->
<!--            干预介入率 {{ percentText(mockPreview.interventions?.intervention_rate) }}，辅导员介入率 {{ percentText(mockPreview.interventions?.counselor_involved_rate) }}-->
<!--          </div>-->
<!--        </div>-->
<!--        <div v-if="mockPreviewMetrics.includes('预警趋势')" class="p-4 rounded-xl border border-amber-100 bg-white/80">-->
<!--          <div class="text-[10px] font-bold tracking-widest text-amber-700">预警趋势</div>-->
<!--          <div class="mt-2 text-sm text-slate-700">-->
<!--            预警总数 {{ mockPreview.alerts?.count }} 条，高风险未处理 {{ mockPreview.alerts?.high_unack_count }} 条-->
<!--          </div>-->
<!--        </div>-->
<!--        <div v-if="mockPreviewMetrics.includes('问卷提交')" class="p-4 rounded-xl border border-amber-100 bg-white/80">-->
<!--          <div class="text-[10px] font-bold tracking-widest text-amber-700">问卷提交</div>-->
<!--          <div class="mt-2 text-sm text-slate-700">-->
<!--            问卷 {{ mockPreview.questionnaires?.questionnaires_count }} 份，作答 {{ mockPreview.questionnaires?.responses_count }} 次-->
<!--          </div>-->
<!--        </div>-->
<!--        <div v-if="mockPreviewMetrics.includes('复测改善')" class="p-4 rounded-xl border border-amber-100 bg-white/80">-->
<!--          <div class="text-[10px] font-bold tracking-widest text-amber-700">复测改善</div>-->
<!--          <div class="mt-2 text-sm text-slate-700">-->
<!--            改善率 {{ percentText(mockPreview.retest?.improvement_rate) }}，恢复为安全 {{ mockPreview.retest?.improved_to_safe_count }} 人-->
<!--          </div>-->
<!--        </div>-->
<!--      </div>-->
<!--    </div>-->

    <div v-if="items.length" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div
        v-for="report in items"
        :key="report.name"
        class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 hover:shadow-md transition"
      >
        <div class="flex items-center justify-between gap-4">
          <div class="min-w-0">
            <div class="font-bold text-slate-900 truncate">学院报告 · {{ periodText(report.meta) }}</div>
            <div class="text-xs text-slate-400 mt-1 truncate">{{ report.meta.college_name || `学院 #${report.meta.college_id}` }}</div>
          </div>
          <button
            v-if="report.pdf_name"
            class="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-white transition"
            @click="downloadReport(report.pdf_name)"
          >
            <LucideIcon name="download" class="w-4 h-4 text-slate-600" />
            <span class="text-xs font-semibold text-slate-700">下载</span>
          </button>
        </div>
        <div class="mt-3 text-xs text-slate-500">
          生成时间：<span class="font-mono">{{ fmtDateTime(report.meta.created_at) }}</span>
        </div>
        <div class="mt-3 flex flex-wrap gap-2">
          <ElTag v-for="metric in selectedMetrics(report)" :key="metric" size="small" effect="light" type="info">
            {{ metric }}
          </ElTag>
        </div>
        <div class="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-600">
          <div v-if="hasMetric(report, '风险分布')">评估样本：{{ report.summary?.assessments?.count ?? 0 }}</div>
          <div v-if="hasMetric(report, '风险分布')">高风险占比：{{ percentText(report.summary?.assessments?.risk_distribution?.high_ratio) }}</div>
          <div v-if="hasMetric(report, '预警趋势')">预警总数：{{ report.summary?.alerts?.count ?? 0 }}</div>
          <div v-if="hasMetric(report, '干预效果')">干预介入率：{{ percentText(report.summary?.interventions?.intervention_rate) }}</div>
          <div v-if="hasMetric(report, '问卷提交')">问卷作答数：{{ report.summary?.questionnaires?.responses_count ?? 0 }}</div>
          <div v-if="hasMetric(report, '复测改善')">复测改善率：{{ percentText(report.summary?.retest?.improvement_rate) }}</div>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      title="暂无报告"
      desc="选择月份范围后点击生成，系统将输出一份可下载的分析报告。"
      icon="file-text"
    />
  </div>
</template>
