<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import dayjs from 'dayjs'
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElSelect,
  ElTabPane,
  ElTabs,
  ElTag,
  ElTable,
  ElTableColumn,
} from 'element-plus'

import { api } from '../api/client'
import { fetchAll } from '../api/pagination'
import type {
  AssessmentResult,
  KnowledgeArticle,
  KnowledgeCategory,
  PageResp,
  Questionnaire,
  QuestionnaireTemplate,
} from '../api/types'
import { fmtDateTime } from '../app/format'
import { riskLabel, riskPillClass } from '../app/risk'
import EmptyState from '../components/EmptyState.vue'
import LucideIcon from '../components/LucideIcon.vue'
import StatCard from '../components/StatCard.vue'

const tab = ref<'stats' | 'surveys' | 'knowledge'>('stats')

const loading = ref(false)
const assessments = ref<AssessmentResult[]>([])
const questionnaires = ref<Questionnaire[]>([])
const templates = ref<QuestionnaireTemplate[]>([])
const categories = ref<KnowledgeCategory[]>([])
const articles = ref<KnowledgeArticle[]>([])

type PendingStudent = {
  id: number
  username: string
  real_name: string
  student_no: string
  college_id: number | null
  college__name: string | null
}

type QuestionnaireStats = {
  questionnaire_id: number
  total_students: number
  submitted_count: number
  pending_count: number
  submitted_rate: number
  pending_students: PendingStudent[]
  risk_distribution: { low: number; medium: number; high: number }
  score_distribution: Record<string, number>
}

const qStatsLoading = ref(false)
const qStats = ref<QuestionnaireStats | null>(null)
const selectedQuestionnaireId = ref<number | null>(null)
const detailDialog = ref(false)
const detailTitle = ref('')
const detailRows = ref<AssessmentResult[]>([])
const detailDimensionKey = ref<string | null>(null)

const dist = computed(() => {
  const out = { low: 0, medium: 0, high: 0 }
  for (const a of assessments.value) {
    if (a.risk_level === 'high') out.high += 1
    else if (a.risk_level === 'medium') out.medium += 1
    else out.low += 1
  }
  return out
})
const total = computed(() => dist.value.low + dist.value.medium + dist.value.high || 1)
const avgScore = computed(() => {
  if (!assessments.value.length) return 0
  const sum = assessments.value.reduce((acc, a) => acc + Number(a.avg_score || 0), 0)
  return sum / assessments.value.length
})

const topDims = computed(() => {
  const agg: Record<string, { sum: number; cnt: number }> = {}
  for (const a of assessments.value) {
    for (const [k, v] of Object.entries(a.dimension_scores ?? {})) {
      agg[k] = agg[k] || { sum: 0, cnt: 0 }
      agg[k].sum += Number(v || 0)
      agg[k].cnt += 1
    }
  }
  return Object.entries(agg)
    .map(([k, it]) => ({ key: k, avg: it.cnt ? it.sum / it.cnt : 0 }))
    .sort((a, b) => b.avg - a.avg)
    .slice(0, 8)
})

const trend = computed(() => {
  const now = dayjs()
  const months = [now.subtract(2, 'month'), now.subtract(1, 'month'), now].map((m) => m.format('YYYY-MM'))
  const map: Record<string, { low: number; medium: number; high: number }> = {}
  for (const m of months) map[m] = { low: 0, medium: 0, high: 0 }
  for (const a of assessments.value) {
    const m = dayjs(a.created_at).format('YYYY-MM')
    if (!map[m]) continue
    if (a.risk_level === 'high') map[m].high += 1
    else if (a.risk_level === 'medium') map[m].medium += 1
    else map[m].low += 1
  }
  return months.map((m) => {
    const item = map[m] ?? { low: 0, medium: 0, high: 0 }
    return {
      month: m,
      low: item.low,
      medium: item.medium,
      high: item.high,
    }
  })
})

function pct(n: number) {
  return Math.round((n / total.value) * 100)
}

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
    phobic: '恐怖',
    additional: '附加项',
    obsession: '强迫症状',
    obsessional: '强迫症状',
    phobic_anxiety: '恐怖',
  }
  return map[key] ?? key
}

function openRiskBreakdown(level: 'low' | 'medium' | 'high') {
  detailDimensionKey.value = null
  detailTitle.value = `${riskLabel(level)}学生明细`
  detailRows.value = assessments.value
    .filter((item) => item.risk_level === level)
    .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
  detailDialog.value = true
}

function openDimensionBreakdown(key: string) {
  detailDimensionKey.value = key
  detailTitle.value = `${dimLabel(key)}维度明细`
  detailRows.value = assessments.value
    .filter((item) => Number(item.dimension_scores?.[key] || 0) > 0)
    .sort((a, b) => Number(b.dimension_scores?.[key] || 0) - Number(a.dimension_scores?.[key] || 0))
  detailDialog.value = true
}

function openTrendBreakdown(month: string, level: 'low' | 'medium' | 'high') {
  detailDimensionKey.value = null
  detailTitle.value = `${month} ${riskLabel(level)}学生明细`
  detailRows.value = assessments.value
    .filter((item) => dayjs(item.created_at).format('YYYY-MM') === month && item.risk_level === level)
    .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
  detailDialog.value = true
}

const scoreBuckets = ['0-1', '1-2', '2-3', '3-4', '4-5']
const scoreTotal = computed(() => {
  if (!qStats.value?.score_distribution) return 1
  return scoreBuckets.reduce((acc, k) => acc + Number(qStats.value?.score_distribution?.[k] || 0), 0) || 1
})

async function loadQuestionnaireStats(id: number) {
  qStatsLoading.value = true
  try {
    const { data } = await api.get<QuestionnaireStats>(`/api/surveys/questionnaires/${id}/stats/`)
    qStats.value = data
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载问卷统计失败')
  } finally {
    qStatsLoading.value = false
  }
}

async function loadAll() {
  loading.value = true
  try {
    const [assessAll, qResp, tResp, catResp, artResp] = await Promise.all([
      fetchAll<AssessmentResult>('/api/assessments/results/', 20),
      api.get<PageResp<Questionnaire>>('/api/surveys/questionnaires/'),
      api.get<PageResp<QuestionnaireTemplate>>('/api/surveys/templates/'),
      api.get<PageResp<KnowledgeCategory>>('/api/knowledge/categories/'),
      api.get<PageResp<KnowledgeArticle>>('/api/knowledge/articles/'),
    ])
    assessments.value = assessAll
    questionnaires.value = qResp.data.results ?? []
    templates.value = tResp.data.results ?? []
    categories.value = catResp.data.results ?? []
    articles.value = artResp.data.results ?? []
    if (!selectedQuestionnaireId.value && questionnaires.value.length > 0) {
      const firstQ = questionnaires.value[0]
      if (firstQ) {
        selectedQuestionnaireId.value = firstQ.id
        await loadQuestionnaireStats(firstQ.id)
      }
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

// Questionnaire create
const surveyDialog = ref(false)
const surveySaving = ref(false)
const surveyForm = reactive({
  title: '',
  description: '',
  template_id: undefined as number | undefined,
  is_active: true,
})

function openSurveyCreate() {
  surveyForm.title = ''
  surveyForm.description = ''
  surveyForm.template_id = templates.value[0]?.id
  surveyForm.is_active = true
  surveyDialog.value = true
}

async function createSurvey() {
  if (!surveyForm.title.trim()) return ElMessage.warning('请填写标题')
  if (!surveyForm.template_id) return ElMessage.warning('请选择模板')
  surveySaving.value = true
  try {
    const { data } = await api.post<Questionnaire>('/api/surveys/questionnaires/', {
      title: surveyForm.title.trim(),
      description: surveyForm.description.trim(),
      template_id: surveyForm.template_id,
      is_active: surveyForm.is_active,
    })
    questionnaires.value = [data, ...questionnaires.value]
    ElMessage.success('已发布问卷')
    surveyDialog.value = false
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '发布失败')
  } finally {
    surveySaving.value = false
  }
}

// Knowledge create
const articleDialog = ref(false)
const articleSaving = ref(false)
const articleForm = reactive({
  title: '',
  summary: '',
  content: '',
  document: null as File | null,
  category_id: undefined as number | undefined,
  is_published: true,
})

function openArticleCreate() {
  articleForm.title = ''
  articleForm.summary = ''
  articleForm.content = ''
  articleForm.document = null
  articleForm.category_id = categories.value[0]?.id
  articleForm.is_published = true
  articleDialog.value = true
}

function onArticleFileChange(evt: Event) {
  const input = evt.target as HTMLInputElement
  const file = input?.files?.[0] || null
  articleForm.document = file
}

async function createArticle() {
  if (!articleForm.title.trim()) return ElMessage.warning('请填写标题')
  if (!articleForm.content.trim() && !articleForm.document) return ElMessage.warning('请填写正文或上传文档')
  articleSaving.value = true
  try {
    const form = new FormData()
    form.append('title', articleForm.title.trim())
    form.append('summary', articleForm.summary.trim())
    form.append('content', articleForm.content || '')
    if (articleForm.category_id) form.append('category_id', String(articleForm.category_id))
    form.append('is_published', articleForm.is_published ? 'true' : 'false')
    if (articleForm.document) form.append('document', articleForm.document)

    const { data } = await api.post<KnowledgeArticle>('/api/knowledge/articles/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    articles.value = [data, ...articles.value]
    ElMessage.success('已发布文章')
    articleDialog.value = false
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '发布失败')
  } finally {
    articleSaving.value = false
  }
}

onMounted(loadAll)

watch(selectedQuestionnaireId, (id) => {
  if (id) loadQuestionnaireStats(id)
})
</script>

<template>
  <div class="space-y-4">
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-900 tracking-tight">深度统计分析</div>
          <div class="text-xs text-slate-400 mt-1">风险分布、维度表现、问卷发布与知识推送</div>
        </div>
        <div class="flex items-center gap-2">
          <ElButton :loading="loading" @click="loadAll">刷新</ElButton>
          <ElButton type="primary" @click="tab = 'surveys'">发布问卷</ElButton>
        </div>
      </div>
    </div>

    <ElTabs v-model="tab">
      <ElTabPane label="统计分析" name="stats">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard icon="file-text" label="评估样本" :value="assessments.length" hint="学院范围可见评估结果" tone="slate" />
          <StatCard icon="shield-check" label="平均得分" :value="avgScore.toFixed(2)" hint="基于 avg_score 计算" tone="indigo" />
          <StatCard icon="alert-triangle" label="高风险占比" :value="pct(dist.high) + '%'" hint="高风险 / 总评估" tone="rose" />
          <StatCard icon="clipboard-list" label="已发布问卷" :value="questionnaires.length" hint="学院/全局问卷列表" tone="amber" />
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
          <div class="lg:col-span-2 bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
            <div class="flex items-center justify-between gap-4 flex-wrap">
              <div class="font-bold text-slate-800">风险分布</div>
              <ElTag type="info" effect="light">学院范围</ElTag>
            </div>

            <div class="mt-4">
              <div class="h-3 rounded-full overflow-hidden bg-slate-100 flex">
                <div class="h-3 bg-emerald-500" :style="{ width: pct(dist.low) + '%' }"></div>
                <div class="h-3 bg-amber-500" :style="{ width: pct(dist.medium) + '%' }"></div>
                <div class="h-3 bg-rose-500" :style="{ width: pct(dist.high) + '%' }"></div>
              </div>
              <div class="mt-3 grid grid-cols-3 gap-2 text-xs">
                <button class="text-emerald-700 text-left" @click="openRiskBreakdown('low')">
                  安全 <span class="font-mono text-slate-400">({{ dist.low }})</span>
                </button>
                <button class="text-amber-700 text-center" @click="openRiskBreakdown('medium')">
                  关注 <span class="font-mono text-slate-400">({{ dist.medium }})</span>
                </button>
                <button class="text-rose-700 text-right" @click="openRiskBreakdown('high')">
                  高风险 <span class="font-mono text-slate-400">({{ dist.high }})</span>
                </button>
              </div>
            </div>

            <div class="mt-6">
              <div class="font-bold text-slate-800">维度表现（前列）</div>
              <div v-if="topDims.length" class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                <button
                  v-for="d in topDims"
                  :key="d.key"
                  class="p-4 rounded-xl border border-slate-100 bg-slate-50/50 text-left hover:border-indigo-200 hover:bg-white transition"
                  @click="openDimensionBreakdown(d.key)"
                >
                  <div class="flex items-center justify-between gap-3">
                    <div class="text-xs font-bold text-slate-700 truncate">{{ dimLabel(d.key) }}</div>
                    <div class="text-xs font-mono text-slate-400">{{ d.avg.toFixed(2) }}</div>
                  </div>
                  <div class="mt-2 h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div class="h-2 rounded-full bg-indigo-500" :style="{ width: Math.min(100, Math.max(0, d.avg / 5 * 100)) + '%' }" />
                  </div>
                </button>
              </div>
              <div v-else class="mt-4">
                <EmptyState title="暂无数据" desc="学院尚未产生评估结果。" icon="bar-chart-3" />
              </div>
            </div>

            <div class="mt-6">
              <div class="font-bold text-slate-800">近 3 个月风险趋势</div>
              <div class="mt-3 space-y-3">
                <div v-for="t in trend" :key="t.month" class="space-y-1">
                  <div class="flex items-center justify-between text-xs text-slate-600">
                    <span>{{ t.month }}</span>
                    <span class="font-mono">{{ t.low + t.medium + t.high }}</span>
                  </div>
                  <div class="h-2 rounded-full overflow-hidden bg-slate-100 flex">
                    <div
                      class="h-2 bg-emerald-500"
                      :style="{ width: Math.round((t.low / Math.max(1, t.low + t.medium + t.high)) * 100) + '%' }"
                      @click="openTrendBreakdown(t.month, 'low')"
                    ></div>
                    <div
                      class="h-2 bg-amber-500"
                      :style="{ width: Math.round((t.medium / Math.max(1, t.low + t.medium + t.high)) * 100) + '%' }"
                      @click="openTrendBreakdown(t.month, 'medium')"
                    ></div>
                    <div
                      class="h-2 bg-rose-500"
                      :style="{ width: Math.round((t.high / Math.max(1, t.low + t.medium + t.high)) * 100) + '%' }"
                      @click="openTrendBreakdown(t.month, 'high')"
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
            <div class="font-bold text-slate-800">说明</div>
            <div class="mt-3 text-xs text-slate-500 leading-relaxed space-y-2">
              <p>1) 本页统计基于当前账号权限范围内的评估结果汇总计算。</p>
              <p>2) 维度定义来自问卷模板（示例版）。</p>
              <p>3) 风险等级为筛查参考，建议结合人工咨询结论综合判断。</p>
            </div>
          </div>
        </div>

        <div class="mt-4 bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div class="font-bold text-slate-800">问卷提交统计</div>
              <div class="text-xs text-slate-400 mt-1">提交率 / 未提交名单 / 得分分布</div>
            </div>
            <div class="flex items-center gap-2">
              <ElSelect v-model="selectedQuestionnaireId" filterable class="!w-72" placeholder="选择问卷">
                <el-option v-for="q in questionnaires" :key="q.id" :label="q.title" :value="q.id" />
              </ElSelect>
              <ElButton :loading="qStatsLoading" @click="selectedQuestionnaireId && loadQuestionnaireStats(selectedQuestionnaireId)">
                刷新
              </ElButton>
            </div>
          </div>

          <div v-if="qStatsLoading" class="mt-4 text-sm text-slate-400">加载中…</div>
          <div v-else-if="qStats" class="mt-4 space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
              <StatCard icon="users" label="总学生数" :value="qStats.total_students" hint="学院范围" tone="slate" />
              <StatCard icon="clipboard-list" label="已提交" :value="qStats.submitted_count" hint="提交问卷人数" tone="emerald" />
              <StatCard icon="alert-triangle" label="未提交" :value="qStats.pending_count" hint="待完成学生" tone="rose" />
              <StatCard icon="bar-chart-3" label="提交率" :value="Math.round(qStats.submitted_rate * 100) + '%'" hint="已提交 / 总人数" tone="indigo" />
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div class="lg:col-span-1 bg-slate-50/60 border border-slate-100 rounded-2xl p-4">
                <div class="font-bold text-slate-800">得分分布</div>
                <div class="mt-3 space-y-3">
                  <div v-for="b in scoreBuckets" :key="b">
                    <div class="flex items-center justify-between text-xs text-slate-600">
                      <span>{{ b }}</span>
                      <span class="font-mono">{{ qStats.score_distribution?.[b] || 0 }}</span>
                    </div>
                    <div class="mt-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div
                        class="h-2 rounded-full bg-indigo-500"
                        :style="{ width: Math.round(((qStats.score_distribution?.[b] || 0) / scoreTotal) * 100) + '%' }"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div class="lg:col-span-2 bg-white border border-slate-100 rounded-2xl p-4">
                <div class="font-bold text-slate-800">未提交名单（前 10 名）</div>
                <div v-if="qStats.pending_students?.length" class="mt-3">
                  <ElTable :data="qStats.pending_students.slice(0, 10)" style="width: 100%">
                    <ElTableColumn label="姓名">
                      <template #default="{ row }">
                        {{ row.real_name || row.username }}
                      </template>
                    </ElTableColumn>
                    <ElTableColumn label="账号" prop="username" />
                    <ElTableColumn label="学号" prop="student_no" />
                    <ElTableColumn label="学院">
                      <template #default="{ row }">
                        {{ row.college__name || '—' }}
                      </template>
                    </ElTableColumn>
                  </ElTable>
                </div>
                <div v-else class="mt-3 text-sm text-slate-400">暂无未提交学生</div>
              </div>
            </div>
          </div>
          <div v-else class="mt-4">
            <EmptyState title="暂无数据" desc="请选择问卷或等待学生提交后再查看统计。" icon="clipboard-list" />
          </div>
        </div>
      </ElTabPane>

      <ElTabPane label="问卷发布" name="surveys">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div class="font-bold text-slate-800">问卷管理</div>
              <div class="text-xs text-slate-400 mt-1">选择模板发布问卷，并在学生端完成填写与评估闭环</div>
            </div>
            <ElButton type="primary" @click="openSurveyCreate">
              <LucideIcon name="plus" class="w-4 h-4" />
              发布问卷
            </ElButton>
          </div>
        </div>

        <div v-if="questionnaires.length" class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="q in questionnaires"
            :key="q.id"
            class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 hover:shadow-md transition"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="font-bold text-slate-900 truncate">{{ q.title }}</div>
                <div class="text-xs text-slate-400 mt-1 truncate">{{ q.description }}</div>
              </div>
              <ElTag size="small" effect="light" :type="q.is_active ? 'success' : 'info'">{{ q.is_active ? '生效中' : '已关闭' }}</ElTag>
            </div>
            <div class="mt-3 text-xs text-slate-500">
              模板：<span class="font-semibold">{{ q.template?.name }}</span>
              <span class="mx-2 text-slate-300">·</span>
              创建：{{ fmtDateTime(q.created_at) }}
            </div>
          </div>
        </div>
        <div v-else class="mt-4">
          <EmptyState title="暂无问卷" desc="发布第一份问卷后，学生端即可在线填写并生成评估报告。" icon="clipboard-list" />
        </div>
      </ElTabPane>

      <ElTabPane label="知识推送" name="knowledge">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div class="font-bold text-slate-800">知识推送</div>
              <div class="text-xs text-slate-400 mt-1">面向学院学生推送心理知识内容（支持分类）</div>
            </div>
            <ElButton type="primary" @click="openArticleCreate">
              <LucideIcon name="plus" class="w-4 h-4" />
              新建文章
            </ElButton>
          </div>
        </div>

        <div v-if="articles.length" class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="a in articles"
            :key="a.id"
            class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 hover:shadow-md transition"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="font-bold text-slate-900 truncate">{{ a.title }}</div>
                <div class="text-xs text-slate-400 mt-1 truncate">{{ a.summary }}</div>
              </div>
              <ElTag size="small" effect="light" type="info">{{ a.category?.name || '未分类' }}</ElTag>
            </div>
            <div class="mt-3 text-xs text-slate-500">
              范围：{{ a.target_college?.name || '全校可见' }}
              <span class="mx-2 text-slate-300">·</span>
              时间：{{ fmtDateTime(a.created_at) }}
            </div>
            <div class="mt-3 text-sm text-slate-600 whitespace-pre-wrap leading-relaxed">
              {{ a.content }}
            </div>
            <div v-if="a.document_url || a.document" class="mt-3">
              <a
                class="inline-flex items-center gap-2 text-xs font-semibold text-indigo-600 hover:text-indigo-500"
                :href="a.document_url || a.document || '#'"
                target="_blank"
                rel="noreferrer"
              >
                <LucideIcon name="download" class="w-3 h-3" />
                下载附件
              </a>
            </div>
          </div>
        </div>
        <div v-else class="mt-4">
          <EmptyState title="暂无文章" desc="创建文章后，学生端「心理知识库」将按学院展示与收藏。" icon="book-open" />
        </div>
      </ElTabPane>
    </ElTabs>

    <ElDialog v-model="surveyDialog" title="发布问卷" width="640px">
      <ElForm label-position="top">
        <ElFormItem label="标题">
          <ElInput v-model="surveyForm.title" placeholder="例如：2026 春季心理健康筛查问卷" />
        </ElFormItem>
        <ElFormItem label="描述">
          <ElInput v-model="surveyForm.description" placeholder="给学生的说明…" />
        </ElFormItem>
        <ElFormItem label="问卷模板">
          <ElSelect v-model="surveyForm.template_id" filterable class="w-full" placeholder="选择模板">
            <el-option v-for="t in templates" :key="t.id" :label="`${t.name}（${t.scale_type}）`" :value="t.id" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="surveyDialog = false">取消</ElButton>
          <ElButton type="primary" :loading="surveySaving" @click="createSurvey">发布</ElButton>
        </div>
      </template>
    </ElDialog>

    <ElDialog v-model="articleDialog" title="新建知识文章" width="720px">
      <ElForm label-position="top">
        <ElFormItem label="标题">
          <ElInput v-model="articleForm.title" placeholder="例如：考研季压力缓解专题" />
        </ElFormItem>
        <ElFormItem label="摘要">
          <ElInput v-model="articleForm.summary" placeholder="一句话概述…" />
        </ElFormItem>
        <ElFormItem label="分类">
          <ElSelect v-model="articleForm.category_id" filterable class="w-full" placeholder="选择分类">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="正文">
          <ElInput v-model="articleForm.content" type="textarea" :rows="8" placeholder="正文内容（支持换行）…" />
        </ElFormItem>
        <ElFormItem label="上传文档（可选）">
          <input type="file" @change="onArticleFileChange" />
          <div class="text-xs text-slate-400 mt-1">支持上传文章文档，学生端可直接下载查看。</div>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="articleDialog = false">取消</ElButton>
          <ElButton type="primary" :loading="articleSaving" @click="createArticle">发布</ElButton>
        </div>
      </template>
    </ElDialog>

    <ElDialog v-model="detailDialog" width="960px" :title="detailTitle">
      <div class="space-y-4">
        <div class="text-xs text-slate-400">
          点击分段后查看到的明细，按学生、专业、班级与风险结果展开。
        </div>

        <ElTable :data="detailRows" style="width: 100%">
          <ElTableColumn label="学生">
            <template #default="{ row }">
              <div class="font-semibold text-slate-800">{{ row.student?.real_name || row.student?.username }}</div>
              <div class="text-[10px] text-slate-400">{{ row.student?.username }}</div>
            </template>
          </ElTableColumn>
          <ElTableColumn label="专业">
            <template #default="{ row }">
              {{ row.student?.major?.name || '—' }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="班级">
            <template #default="{ row }">
              {{ row.student?.class_group?.name || '—' }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="风险等级" width="110">
            <template #default="{ row }">
              <span class="text-xs font-bold px-2 py-1 rounded-lg border" :class="riskPillClass(row.risk_level)">
                {{ riskLabel(row.risk_level) }}
              </span>
            </template>
          </ElTableColumn>
          <ElTableColumn label="平均分" width="100">
            <template #default="{ row }">
              {{ Number(row.avg_score || 0).toFixed(2) }}
            </template>
          </ElTableColumn>
          <ElTableColumn v-if="detailDimensionKey" :label="`${dimLabel(detailDimensionKey)}得分`" width="120">
            <template #default="{ row }">
              {{ Number(row.dimension_scores?.[detailDimensionKey || ''] || 0).toFixed(2) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="评估时间" width="170">
            <template #default="{ row }">
              {{ fmtDateTime(row.created_at) }}
            </template>
          </ElTableColumn>
        </ElTable>

        <EmptyState
          v-if="!detailRows.length"
          title="暂无明细"
          desc="当前分段下没有匹配到学生数据。"
          icon="bar-chart-3"
        />
      </div>
    </ElDialog>
  </div>
</template>
