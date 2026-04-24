<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElDrawer, ElMessage } from 'element-plus'

import { api } from '../api/client'
import type { InterventionPlan, PageResp } from '../api/types'
import { fmtDateTime } from '../app/format'
import { interventionSeenStorageKey } from '../app/intervention'
import type { MenuId } from '../app/menu'
import EmptyState from '../components/EmptyState.vue'
import { useAuthStore } from '../stores/auth'

const props = defineProps<{ onNavigate?: (id: MenuId) => void }>()
const auth = useAuthStore()

const loading = ref(false)
const plans = ref<InterventionPlan[]>([])
const drawerOpen = ref(false)
const selected = ref<InterventionPlan | null>(null)

const seenAt = computed(() => localStorage.getItem(interventionSeenStorageKey(auth.me?.id)) || '')

function markSeen() {
  const values = plans.value
    .map((plan) => String(plan.updated_at || plan.created_at || ''))
    .filter(Boolean)
    .sort()
  const latest = values[values.length - 1]
  if (latest) localStorage.setItem(interventionSeenStorageKey(auth.me?.id), latest)
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<PageResp<InterventionPlan>>('/api/interventions/plans/')
    plans.value = data.results ?? []
    markSeen()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function openDetail(plan: InterventionPlan) {
  selected.value = plan
  drawerOpen.value = true
}

function nav(id: MenuId) {
  props.onNavigate?.(id)
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-900 tracking-tight">干预建议与跟进</div>
          <div class="text-xs text-slate-400 mt-1">查看咨询教师给出的建议内容、跟进说明和关联知识卡片</div>
        </div>
        <div class="flex items-center gap-2">
          <ElButton :loading="loading" @click="load">刷新</ElButton>
          <ElButton type="primary" @click="nav('consult')">人工咨询</ElButton>
        </div>
      </div>
    </div>

    <div v-if="plans.length" class="space-y-3">
      <button
        v-for="plan in plans"
        :key="plan.id"
        class="w-full text-left bg-white rounded-2xl border border-slate-100 shadow-sm p-6 hover:shadow-md hover:border-indigo-200 transition"
        @click="openDetail(plan)"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <div class="font-bold text-slate-900 truncate">{{ plan.title }}</div>
              <span
                v-if="String(plan.updated_at || plan.created_at || '') > seenAt"
                class="inline-flex w-2.5 h-2.5 rounded-full bg-rose-500 flex-shrink-0"
              />
            </div>
            <div class="text-xs text-slate-400 mt-1">
              更新：{{ fmtDateTime(plan.updated_at) || fmtDateTime(plan.created_at) }}
            </div>
          </div>
          <div class="text-xs text-slate-400 text-right">
            咨询教师：{{ plan.counselor?.real_name || plan.counselor?.username || '—' }}
          </div>
        </div>

        <div class="mt-3 text-sm text-slate-600 whitespace-pre-wrap leading-relaxed">
          {{ plan.content }}
        </div>

        <div v-if="plan.knowledge_article?.title" class="mt-3 text-xs text-indigo-600 font-semibold">
          已关联知识卡片：{{ plan.knowledge_article.title }}
        </div>
      </button>
    </div>

    <EmptyState
      v-else
      title="暂无干预建议"
      desc="当咨询教师为你创建干预建议后，这里会展示完整内容与跟进信息。"
      icon="shield-check"
    />

    <ElDrawer v-model="drawerOpen" size="560px" :with-header="false">
      <div v-if="selected" class="p-6 space-y-4">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="text-sm font-black text-slate-900 truncate">{{ selected.title }}</div>
            <div class="text-xs text-slate-400 mt-1">
              更新时间：{{ fmtDateTime(selected.updated_at) || fmtDateTime(selected.created_at) }}
            </div>
          </div>
          <div class="text-xs text-slate-500 text-right">
            咨询教师：{{ selected.counselor?.real_name || selected.counselor?.username || '—' }}
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <div class="font-bold text-slate-800">干预内容</div>
          <div class="mt-3 text-sm text-slate-600 whitespace-pre-wrap leading-relaxed">
            {{ selected.content }}
          </div>
        </div>

        <div v-if="selected.knowledge_article" class="bg-white rounded-2xl border border-indigo-100 shadow-sm p-5">
          <div class="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <div class="font-bold text-slate-800">关联知识卡片</div>
              <div class="text-xs text-slate-400 mt-1">
                {{ selected.knowledge_article.category?.name || '知识卡片' }}
              </div>
            </div>
            <a
              v-if="selected.knowledge_article.document_url || selected.knowledge_article.document"
              class="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-indigo-200 bg-indigo-50 hover:bg-white transition text-xs font-semibold text-indigo-700"
              :href="selected.knowledge_article.document_url || selected.knowledge_article.document || '#'"
              target="_blank"
              rel="noreferrer"
            >
              查看附件
            </a>
          </div>

          <div class="mt-3 font-semibold text-slate-800">
            {{ selected.knowledge_article.title }}
          </div>
          <div v-if="selected.knowledge_article.summary" class="mt-2 text-sm text-slate-500">
            {{ selected.knowledge_article.summary }}
          </div>
          <div class="mt-3 text-sm text-slate-600 whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto">
            {{ selected.knowledge_article.content }}
          </div>
        </div>

        <div class="flex gap-2">
          <ElButton class="flex-1" @click="drawerOpen = false">关闭</ElButton>
          <ElButton class="flex-1" type="primary" @click="nav('consult')">去人工咨询</ElButton>
        </div>
      </div>
    </ElDrawer>
  </div>
</template>
