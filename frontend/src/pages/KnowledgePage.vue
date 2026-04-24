<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElInput, ElMessage, ElSwitch, ElTag } from 'element-plus'

import { api } from '../api/client'
import LucideIcon from '../components/LucideIcon.vue'

type Article = {
  id: number
  title: string
  summary: string
  content: string
  document?: string | null
  document_url?: string | null
  is_favorited: boolean
  created_at: string
}

const loading = ref(false)
const items = ref<Article[]>([])
const q = ref('')
const onlyFav = ref(false)

const filtered = computed(() => {
  const base = onlyFav.value ? items.value.filter((a) => a.is_favorited) : items.value
  const s = q.value.trim()
  if (!s) return base
  return base.filter((a) => (a.title + a.summary + a.content).includes(s))
})

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/api/knowledge/articles/')
    items.value = data.results ?? data ?? []
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function toggleFav(a: Article) {
  try {
    await api.post(`/api/knowledge/articles/${a.id}/${a.is_favorited ? 'unfavorite' : 'favorite'}/`)
    a.is_favorited = !a.is_favorited
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '操作失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="bg-white rounded-xl border shadow-sm p-6">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div class="text-sm font-black text-slate-800 tracking-tight">心理知识库</div>
          <div class="text-xs text-slate-400 mt-1">舒适、简短、可收藏的日常练习</div>
        </div>
        <div class="flex items-center gap-3 flex-wrap justify-end">
          <div class="flex items-center gap-2 px-3 py-2 rounded-lg border bg-slate-50">
            <span class="text-xs font-bold text-slate-500">只看收藏</span>
            <ElSwitch v-model="onlyFav" />
          </div>
          <ElInput v-model="q" placeholder="搜索标题 / 内容…" clearable class="w-[320px]" />
          <ElButton :loading="loading" @click="load">刷新</ElButton>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div v-for="a in filtered" :key="a.id" class="bg-white rounded-xl border shadow-sm p-6">
        <div class="flex justify-between gap-4 items-start">
          <div class="min-w-0">
            <div class="font-bold text-slate-800 truncate">{{ a.title }}</div>
            <div class="text-xs text-slate-400 mt-1">{{ a.summary }}</div>
          </div>
          <button class="p-2 rounded-lg border bg-slate-50 hover:bg-white transition" @click="toggleFav(a)">
            <LucideIcon :name="a.is_favorited ? 'shield-check' : 'book-open'" class="w-4 h-4 text-indigo-600" />
          </button>
        </div>
        <div class="mt-4 text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">{{ a.content }}</div>
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
        <div class="mt-4 flex items-center justify-between">
          <ElTag type="info" effect="light">#{{ a.id }}</ElTag>
          <span class="text-[10px] font-mono text-slate-400">{{ a.created_at?.slice(0, 19).replace('T', ' ') }}</span>
        </div>
      </div>

      <div v-if="!filtered.length && !loading" class="bg-white rounded-xl border shadow-sm p-20 text-center text-slate-300">
        <LucideIcon name="book-open" class="w-12 h-12 mx-auto mb-4 opacity-10" />
        <div class="text-sm font-bold text-slate-400">暂无内容</div>
      </div>
    </div>
  </div>
</template>
