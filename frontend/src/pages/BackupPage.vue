<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElCard, ElForm, ElFormItem, ElMessage, ElSelect, ElTag } from 'element-plus'

import { api, downloadWithAuth } from '../api/client'
import type { College } from '../api/types'
import { useAuthStore } from '../stores/auth'
import LucideIcon from '../components/LucideIcon.vue'

const auth = useAuthStore()
const role = computed(() => auth.me?.role)

const colleges = ref<College[]>([])
const selectedCollegeId = ref<number | null>(null)
const exporting = ref(false)
const lastExport = ref<{ file: string; meta: any } | null>(null)

function fileName(path: string) {
  const parts = path.split('/')
  return parts[parts.length - 1] ?? ''
}

async function loadColleges() {
  if (role.value !== 'sys_admin') return
  try {
    const { data } = await api.get('/api/colleges/')
    colleges.value = data.results ?? data ?? []
    if (selectedCollegeId.value === null) selectedCollegeId.value = 0
  } catch {
    colleges.value = []
  }
}

async function exportBackup() {
  exporting.value = true
  try {
    const payload: any = {}
    if (role.value === 'sys_admin') {
      if (selectedCollegeId.value && selectedCollegeId.value !== 0) {
        payload.college_id = selectedCollegeId.value
      }
    }
    const { data } = await api.post('/api/backups/export/', payload)
    lastExport.value = { file: data.file, meta: data.meta }
    ElMessage.success('备份导出成功')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '备份失败')
  } finally {
    exporting.value = false
  }
}

async function downloadBackup(name: string) {
  try {
    await downloadWithAuth(`/api/backups/download/?name=${encodeURIComponent(name)}`, name)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '下载失败')
  }
}

onMounted(loadColleges)
</script>

<template>
  <div class="space-y-8">
    <div class="bg-white p-10 rounded-xl border border-dashed border-slate-300 text-center">
      <LucideIcon name="database" class="w-16 h-16 mx-auto mb-4 text-slate-200" />
      <h3 class="font-bold text-slate-700">
        {{ role === 'college_admin' ? '学院专属数据备份控制台' : '系统全局全量备份' }}
      </h3>
      <p class="text-xs text-slate-400 mt-2 max-w-sm mx-auto">
        {{
          role === 'college_admin'
            ? '仅备份属于本学院的学生问卷、评估报告及咨询记录。'
            : '系统管理员可按学院或全校导出数据备份。'
        }}
      </p>

      <div class="mt-6 flex flex-col md:flex-row gap-3 justify-center items-center">
        <ElForm v-if="role === 'sys_admin'" class="w-full md:w-auto">
          <ElFormItem label="学院" class="!mb-0">
            <ElSelect v-model="selectedCollegeId" class="w-64" filterable>
              <el-option label="全部学院" :value="0" />
              <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
            </ElSelect>
          </ElFormItem>
        </ElForm>

        <ElButton type="primary" size="large" :loading="exporting" @click="exportBackup">立即启动备份</ElButton>
      </div>
    </div>

    <ElCard v-if="lastExport" shadow="never">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-bold">最近一次导出</span>
          <ElTag type="info" effect="light">{{ fileName(lastExport.file) }}</ElTag>
        </div>
      </template>

      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="text-xs text-slate-500">
          <div>范围：{{ lastExport.meta?.scope === 'all' ? '全部学院' : `学院 ${lastExport.meta?.college_id}` }}</div>
          <div>导出时间：{{ lastExport.meta?.exported_at }}</div>
        </div>
        <button
          class="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 bg-slate-50 hover:bg-white transition"
          @click="downloadBackup(fileName(lastExport.file))"
        >
          <LucideIcon name="download" class="w-4 h-4 text-slate-600" />
          <span class="text-sm font-semibold text-slate-700">下载备份文件</span>
        </button>
      </div>
    </ElCard>
  </div>
</template>
