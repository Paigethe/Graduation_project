<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
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
} from 'element-plus'

import { api } from '../api/client'
import type { College, PageResp, Questionnaire, QuestionnaireTemplate } from '../api/types'
import { fmtDateTime } from '../app/format'
import EmptyState from '../components/EmptyState.vue'
import LucideIcon from '../components/LucideIcon.vue'
import StatCard from '../components/StatCard.vue'

const tab = ref<'overview' | 'templates' | 'questionnaires'>('overview')
const loading = ref(false)

const healthOk = ref<boolean | null>(null)

const colleges = ref<College[]>([])
const templates = ref<QuestionnaireTemplate[]>([])
const questionnaires = ref<Questionnaire[]>([])

// Template create
const tplDialog = ref(false)
const tplSaving = ref(false)
const tplForm = reactive({
  name: '',
  scale_type: 'SCL-90',
  description: '',
  questionsJson: '',
})

function openTplCreate() {
  tplForm.name = ''
  tplForm.scale_type = 'SCL-90'
  tplForm.description = ''
  tplForm.questionsJson = JSON.stringify(
    [
      { id: 1, text: '示例题目 1', dimension: 'overall', weight: 1 },
      { id: 2, text: '示例题目 2', dimension: 'anxiety', weight: 1 },
    ],
    null,
    2,
  )
  tplDialog.value = true
}

async function createTemplate() {
  if (!tplForm.name.trim()) return ElMessage.warning('请填写模板名称')
  let questions: any[] = []
  try {
    questions = JSON.parse(tplForm.questionsJson || '[]')
  } catch {
    return ElMessage.warning('题目结构文本格式不正确')
  }
  if (!Array.isArray(questions) || !questions.length) return ElMessage.warning('题目列表不能为空')

  tplSaving.value = true
  try {
    const { data } = await api.post<QuestionnaireTemplate>('/api/surveys/templates/', {
      name: tplForm.name.trim(),
      scale_type: tplForm.scale_type.trim(),
      description: tplForm.description.trim(),
      questions,
    })
    templates.value = [data, ...templates.value]
    ElMessage.success('模板已创建')
    tplDialog.value = false
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    tplSaving.value = false
  }
}

// Questionnaire create
const qDialog = ref(false)
const qSaving = ref(false)
const qForm = reactive({
  title: '',
  description: '',
  template_id: null as number | null,
  target_college_id: null as number | null,
  is_active: true,
})

function openQuestionnaireCreate() {
  qForm.title = ''
  qForm.description = ''
  qForm.template_id = templates.value[0]?.id ?? null
  qForm.target_college_id = colleges.value[0]?.id ?? null
  qForm.is_active = true
  qDialog.value = true
}

async function createQuestionnaire() {
  if (!qForm.title.trim()) return ElMessage.warning('请填写问卷标题')
  if (!qForm.template_id) return ElMessage.warning('请选择模板')
  qSaving.value = true
  try {
    const { data } = await api.post<Questionnaire>('/api/surveys/questionnaires/', {
      title: qForm.title.trim(),
      description: qForm.description.trim(),
      template_id: qForm.template_id,
      target_college_id: qForm.target_college_id,
      is_active: qForm.is_active,
    })
    questionnaires.value = [data, ...questionnaires.value]
    ElMessage.success('问卷已发布')
    qDialog.value = false
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '发布失败')
  } finally {
    qSaving.value = false
  }
}

const stats = computed(() => ({
  colleges: colleges.value.length,
  templates: templates.value.length,
  questionnaires: questionnaires.value.length,
}))

async function loadAll() {
  loading.value = true
  try {
    const [healthResp, colResp, tplResp, qResp] = await Promise.all([
      api.get('/api/health/'),
      api.get<PageResp<College>>('/api/colleges/'),
      api.get<PageResp<QuestionnaireTemplate>>('/api/surveys/templates/'),
      api.get<PageResp<Questionnaire>>('/api/surveys/questionnaires/'),
    ])
    healthOk.value = Boolean(healthResp.data?.ok)
    colleges.value = colResp.data.results ?? colResp.data ?? []
    templates.value = tplResp.data.results ?? []
    questionnaires.value = qResp.data.results ?? []
  } catch (err: any) {
    healthOk.value = null
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <div class="space-y-4">
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-900 tracking-tight">数据库管理</div>
          <div class="text-xs text-slate-400 mt-1">问卷模板/问卷发布与基础数据查看（系统管理员）</div>
        </div>
        <div class="flex items-center gap-2">
          <ElButton :loading="loading" @click="loadAll">刷新</ElButton>
          <ElButton type="primary" @click="openQuestionnaireCreate">
            <LucideIcon name="plus" class="w-4 h-4" />
            发布问卷
          </ElButton>
        </div>
      </div>
    </div>

    <ElTabs v-model="tab">
      <ElTabPane label="概览" name="overview">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard icon="activity" label="接口健康" :value="healthOk === null ? '—' : healthOk ? '正常' : '异常'" hint="/api/health/" :tone="healthOk ? 'emerald' : 'rose'" />
          <StatCard icon="users" label="学院" :value="stats.colleges" hint="学院基础数据" tone="slate" />
          <StatCard icon="clipboard-list" label="问卷模板" :value="stats.templates" hint="量表/题目结构" tone="indigo" />
          <StatCard icon="file-text" label="问卷发布" :value="stats.questionnaires" hint="学院/全局问卷实例" tone="amber" />
        </div>

        <div class="mt-4 bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="font-bold text-slate-800">提示</div>
          <div class="mt-3 text-xs text-slate-500 leading-relaxed space-y-2">
            <p>1) 模板用于定义题目、维度与权重；问卷用于发布到学院/全校。</p>
            <p>2) 系统会在学生提交问卷后即时生成评估结果，并在中高风险时生成预警。</p>
          </div>
        </div>
      </ElTabPane>

      <ElTabPane label="问卷模板" name="templates">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div class="font-bold text-slate-800">模板列表</div>
              <div class="text-xs text-slate-400 mt-1">创建与维护问卷模板（题目/维度/权重）</div>
            </div>
            <ElButton type="primary" @click="openTplCreate">
              <LucideIcon name="plus" class="w-4 h-4" />
              新建模板
            </ElButton>
          </div>
        </div>

        <div v-if="templates.length" class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="t in templates"
            :key="t.id"
            class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 hover:shadow-md transition"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="font-bold text-slate-900 truncate">{{ t.name }}</div>
                <div class="text-xs text-slate-400 mt-1 truncate">{{ t.description }}</div>
              </div>
              <ElTag size="small" effect="light" type="info">{{ t.scale_type }}</ElTag>
            </div>
            <div class="mt-3 text-xs text-slate-500">
              题目数：<span class="font-mono">{{ t.questions?.length ?? 0 }}</span>
              <span class="mx-2 text-slate-300">·</span>
              创建：<span class="font-mono">{{ fmtDateTime(t.created_at) }}</span>
            </div>
          </div>
        </div>

        <EmptyState v-else title="暂无模板" desc="先创建模板后才能发布问卷。" icon="clipboard-list" />
      </ElTabPane>

      <ElTabPane label="问卷发布" name="questionnaires">
        <div v-if="questionnaires.length" class="grid grid-cols-1 md:grid-cols-2 gap-4">
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
              范围：<span class="font-semibold">{{ q.target_college?.name || '全校' }}</span>
            </div>
            <div class="mt-2 text-[10px] font-mono text-slate-400">
              创建：{{ fmtDateTime(q.created_at) }}
            </div>
          </div>
        </div>

        <EmptyState v-else title="暂无问卷" desc="发布问卷后，学生端可在线填写并生成评估报告。" icon="file-text" />
      </ElTabPane>
    </ElTabs>

    <ElDialog v-model="tplDialog" title="新建问卷模板" width="760px">
      <ElForm label-position="top">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <ElFormItem label="模板名称">
            <ElInput v-model="tplForm.name" placeholder="例如：SAS 焦虑自评量表（示例）" />
          </ElFormItem>
          <ElFormItem label="量表类型">
            <ElInput v-model="tplForm.scale_type" placeholder="例如：SAS / SDS / SCL-90" />
          </ElFormItem>
        </div>
        <ElFormItem label="描述">
          <ElInput v-model="tplForm.description" placeholder="用于说明模板用途…" />
        </ElFormItem>
        <ElFormItem label="题目结构文本（数组）">
          <ElInput v-model="tplForm.questionsJson" type="textarea" :rows="10" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="tplDialog = false">取消</ElButton>
          <ElButton type="primary" :loading="tplSaving" @click="createTemplate">创建</ElButton>
        </div>
      </template>
    </ElDialog>

    <ElDialog v-model="qDialog" title="发布问卷" width="680px">
      <ElForm label-position="top">
        <ElFormItem label="问卷标题">
          <ElInput v-model="qForm.title" placeholder="例如：2026 春季心理健康筛查" />
        </ElFormItem>
        <ElFormItem label="描述">
          <ElInput v-model="qForm.description" placeholder="面向学生的提示…" />
        </ElFormItem>
        <ElFormItem label="模板">
          <ElSelect v-model="qForm.template_id" filterable class="w-full">
            <el-option v-for="t in templates" :key="t.id" :label="`${t.name}（${t.scale_type}）`" :value="t.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="投放学院（可选）">
          <ElSelect v-model="qForm.target_college_id" filterable clearable class="w-full" placeholder="不选择则为全校">
            <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="qDialog = false">取消</ElButton>
          <ElButton type="primary" :loading="qSaving" @click="createQuestionnaire">发布</ElButton>
        </div>
      </template>
    </ElDialog>
  </div>
</template>
