<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElCard, ElMessage, ElProgress, ElSwitch, ElTag } from 'element-plus'

import { api } from '../api/client'
import { fetchAll } from '../api/pagination'
import type { MenuId } from '../app/menu'
import { useAuthStore } from '../stores/auth'
import LucideIcon from '../components/LucideIcon.vue'

type Question = { id: number; text: string }
type Template = { id: number; name: string; questions: Question[] }
type Questionnaire = { id: number; title: string; description: string; template: Template }
type AssessmentLite = { questionnaire?: { id?: number } | null }
type RetestTaskLite = { questionnaire?: { id?: number } | null; status?: string }

const props = defineProps<{ onNavigate?: (id: MenuId) => void }>()

const auth = useAuthStore()
const role = computed(() => auth.me?.role)

const loading = ref(false)
const submitting = ref(false)
const questionnaires = ref<Questionnaire[]>([])
const submittedQuestionnaireIds = ref<Set<number>>(new Set())
const pendingRetestQuestionnaireIds = ref<Set<number>>(new Set())
const onlyPending = ref(false)

const isAnswering = ref(false)
const currentQIndex = ref(0)
const currentQuestionnaire = ref<Questionnaire | null>(null)
const answers = ref<Record<string, number>>({})

const questions = computed(() => currentQuestionnaire.value?.template?.questions ?? [])
const currentQuestion = computed(() => questions.value[currentQIndex.value])
const submittedCount = computed(() => {
  return questionnaires.value.filter((q) => isSubmitted(q.id)).length
})
const questionnaireList = computed(() => {
  const sorted = [...questionnaires.value].sort(
    (a, b) => Number(isSubmitted(a.id) && !isRetestPending(a.id)) - Number(isSubmitted(b.id) && !isRetestPending(b.id)),
  )
  if (!onlyPending.value) return sorted
  return sorted.filter((q) => !isSubmitted(q.id) || isRetestPending(q.id))
})
const listEmptyText = computed(() => {
  if (onlyPending.value && questionnaires.value.length > 0) return '你已完成全部可用问卷'
  return '暂无可用问卷'
})
const listEmptyDesc = computed(() => {
  if (onlyPending.value && questionnaires.value.length > 0) return '可以前往分析报告查看结果详情。'
  return ''
})
const listEmptyIcon = computed(() => {
  if (onlyPending.value && questionnaires.value.length > 0) return 'check-circle-2'
  return 'clipboard-list'
})
const isListEmpty = computed(() => {
  return questionnaireList.value.length === 0 && !loading.value
})
const progressText = computed(() => {
  const total = questionnaires.value.length
  if (!total) return '已提交 0 / 0'
  return `已提交 ${submittedCount.value} / ${total}`
})
const listHeaderNote = computed(() => {
  if (!questionnaires.value.length) return '当前暂无发布中的问卷'
  if (submittedCount.value === questionnaires.value.length) return '全部问卷已完成'
  return '按提交状态排序：未提交在前'
})
const isLastQuestion = computed(() => currentQIndex.value >= Math.max(questions.value.length - 1, 0))
const answeredCount = computed(() => Object.keys(answers.value).length)
const canSubmit = computed(() => {
  const total = questions.value.length
  if (!total) return false
  return answeredCount.value >= total
})
const percent = computed(() => {
  const total = questions.value.length || 1
  return Math.round(((currentQIndex.value + 1) / total) * 100)
})

const choices = [
  { label: '没有', value: 1 },
  { label: '很轻', value: 2 },
  { label: '中度', value: 3 },
  { label: '偏重', value: 4 },
  { label: '严重', value: 5 },
]

function toIdList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  const out: string[] = []
  for (const item of value) {
    const text = String(item ?? '').trim()
    if (!text) continue
    for (const part of text.split(',')) {
      const id = part.trim()
      if (id) out.push(id)
    }
  }
  return out
}

function formatIdList(ids: string[], limit = 8) {
  if (!ids.length) return ''
  if (ids.length <= limit) return ids.join('、')
  return `${ids.slice(0, limit).join('、')} 等${ids.length}题`
}

function formatSubmitError(err: any) {
  const data = err?.response?.data
  if (!data || typeof data !== 'object') return err?.response?.data?.detail || '提交失败'
  if (typeof data.detail === 'string' && data.detail) return data.detail

  const lines: string[] = []

  const missingIds = toIdList((data as any).missing_question_ids)
  if (missingIds.length) lines.push(`以下题目未作答：${formatIdList(missingIds)}。`)

  const extraIds = toIdList((data as any).extra_question_ids)
  if (extraIds.length) lines.push(`存在无效题号：${formatIdList(extraIds)}。`)

  const rangeErrors = Object.entries(data as Record<string, unknown>)
    .filter(([key]) => /^\d+$/.test(key))
    .map(([key, value]) => {
      const msg = Array.isArray(value) ? String(value[0] ?? '') : String(value ?? '')
      return `第${key}题${msg}`
    })

  if (rangeErrors.length) {
    const preview = rangeErrors.slice(0, 3).join('；')
    const suffix = rangeErrors.length > 3 ? `（共${rangeErrors.length}题）` : ''
    lines.push(`答案范围错误：${preview}${suffix}`)
  }

  if (lines.length) return lines.join(' ')
  return '提交失败，请检查作答后重试'
}

async function load() {
  loading.value = true
  try {
    const [{ data }, assessments, retestTasks] = await Promise.all([
      api.get('/api/surveys/questionnaires/'),
      fetchAll<AssessmentLite>('/api/assessments/results/', 20),
      fetchAll<RetestTaskLite>('/api/surveys/retest-tasks/', 20),
    ])
    questionnaires.value = data.results ?? data ?? []
    const ids = new Set<number>()
    for (const item of assessments) {
      const id = Number(item?.questionnaire?.id)
      if (Number.isFinite(id) && id > 0) ids.add(id)
    }
    submittedQuestionnaireIds.value = ids
    const pendingIds = new Set<number>()
    for (const task of retestTasks) {
      if (String(task?.status || '') !== 'pending') continue
      const qid = Number(task?.questionnaire?.id)
      if (Number.isFinite(qid) && qid > 0) pendingIds.add(qid)
    }
    pendingRetestQuestionnaireIds.value = pendingIds
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function isSubmitted(id: number) {
  return submittedQuestionnaireIds.value.has(id)
}

function isRetestPending(id: number) {
  return pendingRetestQuestionnaireIds.value.has(id)
}

function canStart(id: number) {
  return !isSubmitted(id) || isRetestPending(id)
}

function start(q: Questionnaire) {
  if (isSubmitted(q.id) && !isRetestPending(q.id)) {
    ElMessage.info('该问卷已提交，无需重复作答')
    return
  }
  currentQuestionnaire.value = q
  isAnswering.value = true
  currentQIndex.value = 0
  answers.value = {}
}

function answer(value: number) {
  const q = currentQuestion.value
  if (!q) return

  answers.value[String(q.id)] = value
  if (!isLastQuestion.value) {
    currentQIndex.value += 1
  }
}

function goPrev() {
  if (currentQIndex.value <= 0) return
  currentQIndex.value -= 1
}

async function submitSurvey() {
  const survey = currentQuestionnaire.value
  if (!survey || submitting.value) return

  const missingIds = questions.value
    .map((q) => String(q.id))
    .filter((id) => answers.value[id] === undefined || answers.value[id] === null)
  if (missingIds.length) {
    const firstMissing = missingIds[0]
    const targetIndex = questions.value.findIndex((q) => String(q.id) === firstMissing)
    if (targetIndex >= 0) currentQIndex.value = targetIndex
    ElMessage.warning(`还有 ${missingIds.length} 题未作答，请先完成后再提交`)
    return
  }

  submitting.value = true
  try {
    const { data } = await api.post(`/api/surveys/questionnaires/${survey.id}/submit/`, {
      answers: answers.value,
    })
    ElMessage.success(`测评提交成功，评估ID：${data.assessment_id}`)
    isAnswering.value = false
    currentQuestionnaire.value = null
    await load()
    props.onNavigate?.('report')
  } catch (err: any) {
    ElMessage.error(formatSubmitError(err))
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div v-if="role !== 'student'" class="bg-white rounded-xl border shadow-sm p-12 text-center text-slate-400">
      仅学生账号可进行在线测评。
    </div>

    <template v-else>
      <div v-if="isAnswering" class="bg-white p-8 rounded-2xl shadow-lg border-t-4 border-indigo-600 max-w-2xl mx-auto">
        <div class="flex justify-between items-center mb-8">
          <ElTag type="info">{{ currentQuestionnaire?.template?.name || '问卷' }}</ElTag>
          <span class="text-xs font-bold text-slate-400">
            题目 {{ currentQIndex + 1 }} / {{ questions.length || 0 }}
          </span>
        </div>
        <h3 class="text-xl font-bold text-slate-800 text-center mb-10">{{ currentQuestion?.text }}</h3>
        <div class="grid grid-cols-1 gap-3">
          <button
            v-for="c in choices"
            :key="c.value"
            class="p-4 border rounded-xl text-sm font-medium transition-all text-slate-600"
            :class="answers[String(currentQuestion?.id)] === c.value ? 'border-indigo-300 bg-indigo-50 text-indigo-700' : 'border-slate-100 hover:bg-indigo-50 hover:border-indigo-200'"
            @click="answer(c.value)"
          >
            {{ c.label }}
          </button>
        </div>
        <div class="mt-6 flex items-center justify-between gap-2">
          <ElButton :disabled="currentQIndex === 0 || submitting" @click="goPrev">上一题</ElButton>
          <div class="text-xs text-slate-400">已作答 {{ answeredCount }} / {{ questions.length || 0 }}</div>
          <ElButton
            type="primary"
            :disabled="!isLastQuestion || !canSubmit"
            :loading="submitting"
            @click="submitSurvey"
          >
            提交问卷
          </ElButton>
        </div>
        <div class="mt-3 text-xs text-slate-400 text-center" v-if="isLastQuestion">
          最后一题已作答后，请点击“提交问卷”完成本次测评。
        </div>
        <ElProgress :percentage="percent" class="mt-10" color="#4f46e5" />
      </div>

      <div v-else class="space-y-3">
        <div class="bg-white rounded-xl border border-slate-100 shadow-sm px-4 py-3 flex items-center justify-between gap-3">
          <div>
            <div class="text-xs text-slate-500 font-semibold">{{ progressText }}</div>
            <div class="text-[11px] text-slate-400 mt-0.5">{{ listHeaderNote }}</div>
          </div>
          <div class="flex items-center gap-2 text-xs text-slate-500">
            <span>仅看未提交</span>
            <ElSwitch v-model="onlyPending" size="small" />
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ElCard v-for="s in questionnaireList" :key="s.id" shadow="never">
            <div class="flex justify-between items-center">
              <div class="flex items-center gap-3">
                <div class="p-3 bg-indigo-50 text-indigo-500 rounded-lg">
                  <LucideIcon name="clipboard-list" class="w-4 h-4" />
                </div>
                <div>
                  <h4 class="font-bold text-sm">{{ s.title }}</h4>
                  <p class="text-[10px] text-slate-400 mt-0.5">{{ s.description }}</p>
                  <div v-if="isSubmitted(s.id)" class="mt-1">
                    <ElTag size="small" type="success" effect="light">已提交</ElTag>
                  </div>
                  <div v-if="isRetestPending(s.id)" class="mt-1">
                    <ElTag size="small" type="warning" effect="light">待复测</ElTag>
                  </div>
                </div>
              </div>
              <ElButton
                :type="canStart(s.id) ? 'primary' : 'info'"
                round
                size="small"
                :loading="loading"
                :disabled="!canStart(s.id)"
                @click="start(s)"
              >
                {{ isRetestPending(s.id) ? '开始复测' : isSubmitted(s.id) ? '已提交' : '开始' }}
              </ElButton>
            </div>
          </ElCard>
        </div>

        <div v-if="isListEmpty" class="bg-white rounded-xl border shadow-sm p-20 text-center text-slate-300">
          <LucideIcon :name="listEmptyIcon" class="w-12 h-12 mx-auto mb-4 opacity-10" />
          <div class="text-sm font-bold text-slate-400">{{ listEmptyText }}</div>
          <div v-if="listEmptyDesc" class="text-xs text-slate-300 mt-2">{{ listEmptyDesc }}</div>
        </div>
      </div>
    </template>
  </div>
</template>
