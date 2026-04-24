<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElDatePicker, ElDialog, ElDrawer, ElForm, ElFormItem, ElInput, ElMessage, ElSelect, ElTag } from 'element-plus'

import { api } from '../api/client'
import { fetchAll } from '../api/pagination'
import type { AssessmentResult, InterventionPlan, PageResp, Questionnaire, QuestionnaireRetestTask, RiskAlert, UserLite } from '../api/types'
import type { MenuId } from '../app/menu'
import { clampText, fmtDateTime } from '../app/format'
import { interventionStatusLabel } from '../app/intervention'
import { riskLabel, riskPillClass } from '../app/risk'
import EmptyState from '../components/EmptyState.vue'
import LucideIcon from '../components/LucideIcon.vue'
import StatCard from '../components/StatCard.vue'

type StudentProfileResp = {
  student: UserLite
  assigned_counselors: UserLite[]
  latest_assessment: AssessmentResult | null
  recent_assessments: AssessmentResult[]
  latest_alerts: RiskAlert[]
  intervention_plans: InterventionPlan[]
  retest_tasks: QuestionnaireRetestTask[]
}

const props = defineProps<{ onNavigate?: (id: MenuId) => void }>()

const loading = ref(false)
const students = ref<UserLite[]>([])
const q = ref('')

const drawerOpen = ref(false)
const profileLoading = ref(false)
const profile = ref<StudentProfileResp | null>(null)
const questionnaires = ref<Questionnaire[]>([])

const retestDialog = ref(false)
const retestSaving = ref(false)
const retestForm = ref({
  student_id: null as number | null,
  questionnaire_id: null as number | null,
  reason: '',
  due_date: '' as string | '',
})

const filtered = computed(() => {
  const s = q.value.trim()
  if (!s) return students.value
  return students.value.filter((u) => (u.real_name + u.username).includes(s))
})

async function fetchAllStudents() {
  const all: UserLite[] = []
  let page = 1
  while (true) {
    const { data } = await api.get<PageResp<UserLite>>('/api/counselor/students/', {
      params: { page },
    })
    const rows = data.results ?? []
    all.push(...rows)
    if (!data.next || rows.length === 0) break
    page += 1
    if (page > 200) break
  }
  return all
}

async function load() {
  loading.value = true
  try {
    const [stuRows, qRows] = await Promise.all([
      fetchAllStudents(),
      fetchAll<Questionnaire>('/api/surveys/questionnaires/', 20),
    ])
    students.value = stuRows
    questionnaires.value = qRows
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function openProfile(u: UserLite) {
  drawerOpen.value = true
  profile.value = null
  profileLoading.value = true
  try {
    const { data } = await api.get<StudentProfileResp>(`/api/students/${u.id}/profile/`)
    profile.value = data
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载档案失败')
  } finally {
    profileLoading.value = false
  }
}

async function startConsult(u: UserLite) {
  try {
    const { data } = await api.post('/api/chat/conversations/human/start/', { student_id: u.id })
    localStorage.setItem('bs001_consult_conv_id', String(data.id))
    props.onNavigate?.('consult')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建会话失败')
  }
}

function goIntervention(u: UserLite) {
  localStorage.setItem('bs001_intervention_student_id', String(u.id))
  props.onNavigate?.('intervention')
}

function openRetest(u: UserLite) {
  retestForm.value = {
    student_id: u.id,
    questionnaire_id: questionnaires.value[0]?.id ?? null,
    reason: '',
    due_date: '',
  }
  retestDialog.value = true
}

async function createRetest() {
  if (!retestForm.value.student_id) return ElMessage.warning('学生信息缺失')
  if (!retestForm.value.questionnaire_id) return ElMessage.warning('请选择问卷')
  retestSaving.value = true
  try {
    const payload: any = {
      student_id: retestForm.value.student_id,
      questionnaire_id: retestForm.value.questionnaire_id,
      reason: retestForm.value.reason.trim(),
    }
    if (retestForm.value.due_date) payload.due_date = retestForm.value.due_date
    const { data } = await api.post<QuestionnaireRetestTask>('/api/surveys/retest-tasks/', payload)
    if (profile.value && profile.value.student.id === retestForm.value.student_id) {
      profile.value.retest_tasks = [data, ...(profile.value.retest_tasks || [])]
    }
    ElMessage.success('已发起复测任务')
    retestDialog.value = false
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '发起失败')
  } finally {
    retestSaving.value = false
  }
}

function fmtConfidence(value: unknown) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  const clamped = Math.min(1, Math.max(0, n))
  return `${(clamped * 100).toFixed(1)}%`
}

function modelHint(assessment: AssessmentResult | null, latestAlerts: RiskAlert[]) {
  if (assessment) {
    return `预测：${riskLabel(assessment.predicted_risk_level)} · 置信度：${fmtConfidence(assessment.model_meta?.confidence)}`
  }
  return latestAlerts?.length ? '基于最新预警（如有）' : '暂无评估记录'
}

function retestStatusLabel(status: string) {
  if (status === 'pending') return '待完成'
  if (status === 'completed') return '已完成'
  if (status === 'canceled') return '已取消'
  return status || '未知'
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-900 tracking-tight">学生档案管理</div>
          <div class="text-xs text-slate-400 mt-1">查看分配学生的评估、预警、干预与咨询情况</div>
        </div>
        <div class="flex items-center gap-2 flex-wrap justify-end">
          <ElInput v-model="q" placeholder="搜索姓名/账号…" clearable class="w-[280px]" />
          <ElButton :loading="loading" @click="load">刷新</ElButton>
        </div>
      </div>
    </div>

    <div v-if="filtered.length" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div
        v-for="u in filtered"
        :key="u.id"
        class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 hover:shadow-md transition"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="font-bold text-slate-900 truncate">{{ u.real_name || u.username }}</div>
            <div class="text-xs text-slate-400 mt-1 truncate">
              {{ u.username }} · {{ u.college?.name || '未绑定学院' }}
            </div>
            <div class="text-xs text-slate-400 mt-1 truncate">
              {{ u.major?.name || '未绑定专业' }} · {{ u.class_group?.name || '未绑定班级' }}
            </div>
          </div>
          <div class="flex-shrink-0">
            <div class="p-2 rounded-xl bg-slate-50 border border-slate-100 text-slate-500">
              <LucideIcon name="user-round" class="w-5 h-5" />
            </div>
          </div>
        </div>

        <div class="mt-4 flex gap-2">
          <ElButton size="small" @click="openProfile(u)">查看档案</ElButton>
          <ElButton size="small" type="primary" @click="startConsult(u)">发起咨询</ElButton>
          <ElButton size="small" type="warning" plain @click="goIntervention(u)">创建干预</ElButton>
          <ElButton size="small" type="success" plain @click="openRetest(u)">发起复测</ElButton>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      title="暂无分配学生"
      desc="系统管理员可在「用户与权限」中配置咨询教师与学生的分配关系。"
      icon="users"
    />

    <ElDrawer v-model="drawerOpen" size="560px" :with-header="false">
      <div class="p-6 space-y-4">
        <div v-if="profileLoading" class="text-sm text-slate-400">加载中…</div>

        <template v-else-if="profile">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="text-sm font-black text-slate-900 truncate">{{ profile.student.real_name || profile.student.username }}</div>
              <div class="text-xs text-slate-400 mt-1 truncate">
                {{ profile.student.username }} · {{ profile.student.college?.name || '未绑定学院' }}
              </div>
              <div class="text-xs text-slate-400 mt-1 truncate">
                {{ profile.student.major?.name || '未绑定专业' }} · {{ profile.student.class_group?.name || '未绑定班级' }}
              </div>
            </div>
            <ElButton size="small" type="primary" @click="startConsult(profile.student)">进入会话</ElButton>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <StatCard
              icon="file-text"
              label="最近评估"
              :value="profile.latest_assessment ? fmtDateTime(profile.latest_assessment.created_at).slice(0, 10) : '—'"
              :hint="profile.latest_assessment ? profile.latest_assessment.questionnaire?.title : '暂无评估记录'"
              tone="slate"
            />
            <StatCard
              icon="shield-check"
              label="当前风险"
              :value="riskLabel(profile.latest_assessment?.risk_level || profile.latest_alerts?.[0]?.level || 'low')"
              :hint="modelHint(profile.latest_assessment, profile.latest_alerts || [])"
              :tone="(profile.latest_assessment?.risk_level || profile.latest_alerts?.[0]?.level) === 'high' ? 'rose' : (profile.latest_assessment?.risk_level || profile.latest_alerts?.[0]?.level) === 'medium' ? 'amber' : 'emerald'"
            />
          </div>

          <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
            <div class="font-bold text-slate-800">风险动态趋势（最近 8 次）</div>
            <div v-if="profile.recent_assessments?.length" class="mt-4 space-y-2">
              <div
                v-for="a in profile.recent_assessments"
                :key="a.id"
                class="p-3 rounded-xl border border-slate-100 bg-slate-50/60"
              >
                <div class="flex items-center justify-between gap-3 text-xs text-slate-500">
                  <span class="truncate">{{ a.questionnaire?.title || '问卷' }}</span>
                  <span class="font-mono">{{ fmtDateTime(a.created_at) }}</span>
                </div>
                <div class="mt-2 flex items-center justify-between gap-3">
                  <div class="text-xs">
                    风险：<span class="font-semibold">{{ riskLabel(a.risk_level) }}</span>
                    <span class="mx-2 text-slate-300">·</span>
                    预测：<span class="font-semibold">{{ riskLabel(a.predicted_risk_level) }}</span>
                  </div>
                  <div class="text-xs font-mono text-slate-500">均分 {{ Number(a.avg_score || 0).toFixed(2) }}</div>
                </div>
              </div>
            </div>
            <div v-else class="mt-4 text-xs text-slate-400">暂无趋势数据</div>
          </div>

          <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
            <div class="font-bold text-slate-800">最新预警</div>
            <div v-if="profile.latest_alerts?.length" class="mt-4 space-y-3">
              <div
                v-for="a in profile.latest_alerts.slice(0, 6)"
                :key="a.id"
                class="p-4 rounded-xl border border-slate-100 bg-slate-50/50"
              >
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-xs font-bold px-2 py-1 rounded-lg border" :class="riskPillClass(a.level)">
                    {{ riskLabel(a.level) }}
                  </span>
                  <span class="text-[10px] font-mono text-slate-400">{{ fmtDateTime(a.created_at) }}</span>
                  <ElTag v-if="a.is_acknowledged" size="small" type="success" effect="light">已确认</ElTag>
                </div>
                <div class="mt-2 text-xs text-slate-600 leading-relaxed">{{ a.message }}</div>
              </div>
            </div>
            <div v-else class="mt-4 text-xs text-slate-400">暂无预警记录</div>
          </div>

          <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
            <div class="flex items-center justify-between gap-3 flex-wrap">
              <div class="font-bold text-slate-800">干预建议</div>
              <ElButton size="small" type="warning" plain @click="goIntervention(profile.student)">创建</ElButton>
            </div>

            <div v-if="profile.intervention_plans?.length" class="mt-4 space-y-3">
              <div
                v-for="p in profile.intervention_plans.slice(0, 6)"
                :key="p.id"
                class="p-4 rounded-xl border border-slate-100 hover:border-indigo-200 hover:bg-indigo-50/30 transition"
              >
                <div class="flex items-center justify-between gap-3">
                  <div class="font-bold text-slate-800 truncate">{{ p.title }}</div>
                  <div class="text-[10px] font-mono text-slate-400">{{ fmtDateTime(p.updated_at) }}</div>
                </div>
                <div class="mt-2 text-xs text-slate-500">
                  状态：<span class="font-semibold">{{ interventionStatusLabel(p.status) }}</span>
                  <span class="mx-2 text-slate-300">·</span>
                  关联评估：<span class="font-mono">{{ p.assessment || '—' }}</span>
                </div>
                <div class="mt-2 text-sm text-slate-600 whitespace-pre-wrap">{{ clampText(p.content, 300) }}</div>
              </div>
            </div>
            <div v-else class="mt-4 text-xs text-slate-400">暂无干预记录</div>
          </div>

          <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
            <div class="flex items-center justify-between gap-3 flex-wrap">
              <div class="font-bold text-slate-800">复测任务</div>
              <ElButton size="small" type="success" plain @click="openRetest(profile.student)">发起复测</ElButton>
            </div>
            <div v-if="profile.retest_tasks?.length" class="mt-4 space-y-3">
              <div
                v-for="t in profile.retest_tasks.slice(0, 8)"
                :key="t.id"
                class="p-4 rounded-xl border border-slate-100 bg-slate-50/50"
              >
                <div class="flex items-center justify-between gap-3">
                  <div class="font-bold text-slate-800 truncate">{{ t.questionnaire?.title || '问卷复测' }}</div>
                  <ElTag size="small" effect="light" :type="t.status === 'completed' ? 'success' : t.status === 'pending' ? 'warning' : 'info'">
                    {{ retestStatusLabel(t.status) }}
                  </ElTag>
                </div>
                <div class="mt-2 text-xs text-slate-500">
                  截止：{{ t.due_date || '未设置' }}
                  <span class="mx-2 text-slate-300">·</span>
                  创建：{{ fmtDateTime(t.created_at) }}
                </div>
                <div v-if="t.reason" class="mt-2 text-sm text-slate-600 whitespace-pre-wrap">{{ t.reason }}</div>
              </div>
            </div>
            <div v-else class="mt-4 text-xs text-slate-400">暂无复测任务</div>
          </div>
        </template>

        <EmptyState v-else title="未加载档案" desc="请选择学生查看详情。" icon="users" />
      </div>
    </ElDrawer>

    <ElDialog v-model="retestDialog" title="发起问卷复测" width="620px">
      <ElForm label-position="top">
        <ElFormItem label="问卷">
          <ElSelect v-model="retestForm.questionnaire_id" filterable class="w-full" placeholder="选择问卷">
            <el-option v-for="q in questionnaires" :key="q.id" :label="q.title" :value="q.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="截止日期（可选）">
          <ElDatePicker v-model="retestForm.due_date" type="date" value-format="YYYY-MM-DD" class="w-full" />
        </ElFormItem>
        <ElFormItem label="复测原因（可选）">
          <ElInput v-model="retestForm.reason" type="textarea" :rows="4" placeholder="例如：近期风险波动明显，建议一周后复测" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="retestDialog = false">取消</ElButton>
          <ElButton type="primary" :loading="retestSaving" @click="createRetest">确认发起</ElButton>
        </div>
      </template>
    </ElDialog>
  </div>
</template>
