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
  ElTag,
} from 'element-plus'

import { api } from '../api/client'
import { fetchAll } from '../api/pagination'
import type { InterventionPlan, KnowledgeArticle, PageResp, UserLite } from '../api/types'
import { fmtDateTime } from '../app/format'
import { interventionStatusLabel, interventionStatusType } from '../app/intervention'
import EmptyState from '../components/EmptyState.vue'
import LucideIcon from '../components/LucideIcon.vue'

const loading = ref(false)
const plans = ref<InterventionPlan[]>([])
const students = ref<UserLite[]>([])
const articles = ref<KnowledgeArticle[]>([])

const statusFilter = ref<string>('all')
const q = ref('')

const dialogOpen = ref(false)
const saving = ref(false)
const editing = ref<InterventionPlan | null>(null)
const articlePreviewOpen = ref(false)
const previewArticle = ref<KnowledgeArticle | null>(null)

const form = reactive({
  student_id: undefined as number | undefined,
  assessment: null as number | null,
  title: '干预建议',
  content: '',
  status: 'in_progress' as string,
  knowledge_article_id: null as number | null,
})

const filtered = computed(() => {
  const s = q.value.trim()
  return plans.value.filter((p) => {
    if (statusFilter.value !== 'all' && p.status !== statusFilter.value) return false
    if (!s) return true
    return (
      (p.title + p.content).includes(s) ||
      (p.student?.real_name || p.student?.username || '').includes(s) ||
      (p.student?.username || '').includes(s)
    )
  })
})

function resetForm() {
  editing.value = null
  form.student_id = undefined
  form.assessment = null
  form.title = '干预建议'
  form.content = ''
  form.status = 'in_progress'
  form.knowledge_article_id = null
}

function openCreate() {
  resetForm()
  const cached = Number(localStorage.getItem('bs001_intervention_student_id') || '')
  if (cached) form.student_id = cached
  dialogOpen.value = true
}

function openEdit(p: InterventionPlan) {
  editing.value = p
  form.student_id = p.student?.id
  form.assessment = p.assessment
  form.title = p.title
  form.content = p.content
  form.status = p.status === 'done' ? 'done' : 'in_progress'
  form.knowledge_article_id = p.knowledge_article?.id ?? null
  dialogOpen.value = true
}

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
    const [planResp, allStudents, allArticles] = await Promise.all([
      api.get<PageResp<InterventionPlan>>('/api/interventions/plans/'),
      fetchAllStudents(),
      fetchAll<KnowledgeArticle>('/api/knowledge/articles/', 20),
    ])
    plans.value = planResp.data.results ?? []
    students.value = allStudents
    articles.value = allArticles
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function openArticle(article: KnowledgeArticle | null | undefined) {
  if (!article) return
  previewArticle.value = article
  articlePreviewOpen.value = true
}

async function save() {
  if (!form.student_id) return ElMessage.warning('请选择学生')
  if (!form.content.trim()) return ElMessage.warning('请填写干预建议内容')

  saving.value = true
  try {
    if (editing.value) {
      const { data } = await api.patch<InterventionPlan>(`/api/interventions/plans/${editing.value.id}/`, {
        title: form.title,
        content: form.content,
        status: form.status,
        assessment: form.assessment,
        knowledge_article_id: form.knowledge_article_id,
      })
      const idx = plans.value.findIndex((p) => p.id === editing.value?.id)
      if (idx >= 0) plans.value[idx] = data
      ElMessage.success('已更新')
    } else {
      const { data } = await api.post<InterventionPlan>('/api/interventions/plans/', {
        student_id: form.student_id,
        assessment: form.assessment,
        title: form.title,
        content: form.content,
        knowledge_article_id: form.knowledge_article_id,
      })
      plans.value = [data, ...plans.value]
      ElMessage.success('已创建并推送')
    }
    localStorage.removeItem('bs001_intervention_student_id')
    dialogOpen.value = false
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-900 tracking-tight">干预建议推送</div>
          <div class="text-xs text-slate-400 mt-1">面向分配学生的干预建议创建、推送与进度跟踪</div>
        </div>

        <div class="flex items-center gap-2 flex-wrap justify-end">
          <div class="flex items-center gap-2 px-3 py-2 rounded-xl border bg-slate-50">
            <LucideIcon name="filter" class="w-4 h-4 text-slate-500" />
            <ElSelect v-model="statusFilter" size="small" class="w-32">
              <el-option label="全部状态" value="all" />
              <el-option label="草稿" value="draft" />
              <el-option label="已推送" value="sent" />
              <el-option label="进行中" value="in_progress" />
              <el-option label="已完成" value="done" />
            </ElSelect>
          </div>
          <ElInput v-model="q" placeholder="搜索标题/内容/学生…" clearable class="w-[260px]" />
          <ElButton :loading="loading" @click="load">刷新</ElButton>
          <ElButton type="primary" @click="openCreate">创建干预</ElButton>
        </div>
      </div>
    </div>

    <div v-if="filtered.length" class="space-y-3">
      <div
        v-for="p in filtered"
        :key="p.id"
        class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 hover:shadow-md transition"
      >
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div class="min-w-0">
            <div class="font-bold text-slate-900 truncate">{{ p.title }}</div>
            <div class="text-xs text-slate-400 mt-1">
              学生：{{ p.student?.real_name || p.student?.username }}
              <span class="mx-2 text-slate-300">·</span>
              更新：{{ fmtDateTime(p.updated_at) || fmtDateTime(p.created_at) }}
            </div>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <ElTag size="small" effect="light" :type="interventionStatusType(p.status)">
              {{ interventionStatusLabel(p.status) }}
            </ElTag>
            <ElButton size="small" @click="openEdit(p)">编辑</ElButton>
          </div>
        </div>

        <div class="mt-3 text-sm text-slate-600 whitespace-pre-wrap leading-relaxed">{{ p.content }}</div>
        <div class="mt-3 flex items-center justify-between gap-3 flex-wrap">
          <div class="text-xs text-slate-500">
            学生：<span class="font-semibold text-slate-700">{{ p.student?.real_name || p.student?.username }}</span>
          </div>
          <button
            v-if="p.knowledge_article"
            class="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
            @click="openArticle(p.knowledge_article)"
          >
            查看关联知识卡片：{{ p.knowledge_article.title }}
          </button>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      title="暂无干预建议"
      desc="从学生档案或风险预警进入，创建并推送干预建议。"
      icon="sparkles"
    />

    <ElDialog v-model="dialogOpen" width="620px" :title="editing ? '编辑干预建议' : '创建干预建议'">
      <ElForm label-position="top">
        <ElFormItem label="选择学生">
          <ElSelect v-model="form.student_id" filterable placeholder="选择已分配学生" class="w-full" :disabled="Boolean(editing)">
            <el-option v-for="s in students" :key="s.id" :label="`${s.real_name || s.username}（${s.username}）`" :value="s.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="标题">
          <ElInput v-model="form.title" placeholder="例如：睡眠调整与压力管理干预建议" />
        </ElFormItem>
        <ElFormItem label="干预内容">
          <ElInput v-model="form.content" type="textarea" :rows="7" placeholder="给学生的具体建议与跟进方式…" />
        </ElFormItem>
        <ElFormItem label="关联知识卡片（可选）">
          <ElSelect v-model="form.knowledge_article_id" clearable filterable class="w-full" placeholder="选择知识卡片">
            <el-option
              v-for="article in articles"
              :key="article.id"
              :label="`${article.title}${article.category?.name ? `（${article.category.name}）` : ''}`"
              :value="article.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="editing" label="状态">
          <ElSelect v-model="form.status" class="w-full">
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="done" />
          </ElSelect>
        </ElFormItem>
      </ElForm>

      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="dialogOpen = false">取消</ElButton>
          <ElButton type="primary" :loading="saving" @click="save">{{ editing ? '保存修改' : '创建并推送' }}</ElButton>
        </div>
      </template>
    </ElDialog>

    <ElDialog v-model="articlePreviewOpen" width="720px" title="知识卡片预览">
      <div v-if="previewArticle" class="space-y-3">
        <div class="text-lg font-bold text-slate-900">{{ previewArticle.title }}</div>
        <div class="text-xs text-slate-400">
          {{ previewArticle.category?.name || '知识卡片' }}
        </div>
        <div v-if="previewArticle.summary" class="text-sm text-slate-500">
          {{ previewArticle.summary }}
        </div>
        <div class="max-h-[420px] overflow-y-auto whitespace-pre-wrap text-sm text-slate-700 leading-relaxed border rounded-xl p-4 bg-slate-50">
          {{ previewArticle.content }}
        </div>
        <div v-if="previewArticle.document_url || previewArticle.document" class="flex justify-end">
          <a
            class="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-indigo-200 bg-indigo-50 hover:bg-white transition text-sm font-semibold text-indigo-700"
            :href="previewArticle.document_url || previewArticle.document || '#'"
            target="_blank"
            rel="noreferrer"
          >
            查看附件
          </a>
        </div>
      </div>
    </ElDialog>
  </div>
</template>
