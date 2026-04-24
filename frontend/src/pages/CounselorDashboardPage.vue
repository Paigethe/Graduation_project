<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElMessage, ElTag } from 'element-plus'

import { api } from '../api/client'
import type { InterventionPlan, PageResp, RiskAlert, Conversation, UserLite } from '../api/types'
import { fmtDateTime } from '../app/format'
import { interventionStatusLabel } from '../app/intervention'
import { riskLabel, riskPillClass } from '../app/risk'
import EmptyState from '../components/EmptyState.vue'
import StatCard from '../components/StatCard.vue'
import type { MenuId } from '../app/menu'

const props = defineProps<{ onNavigate?: (id: MenuId) => void }>()

const loading = ref(false)
const students = ref<UserLite[]>([])
const alerts = ref<RiskAlert[]>([])
const plans = ref<InterventionPlan[]>([])
const conversations = ref<Conversation[]>([])

const unAckCount = computed(() => alerts.value.filter((a) => !a.is_acknowledged).length)
const inProgressPlans = computed(() => plans.value.filter((p) => p.status !== 'done').length)

async function load() {
  loading.value = true
  try {
    const [stuResp, alertResp, planResp, convResp] = await Promise.all([
      api.get<PageResp<UserLite>>('/api/counselor/students/'),
      api.get<PageResp<RiskAlert>>('/api/assessments/alerts/'),
      api.get<PageResp<InterventionPlan>>('/api/interventions/plans/'),
      api.get<PageResp<Conversation>>('/api/chat/conversations/'),
    ])
    students.value = stuResp.data.results ?? []
    alerts.value = alertResp.data.results ?? []
    plans.value = planResp.data.results ?? []
    conversations.value = (convResp.data.results ?? []).filter((c) => c.kind === 'human')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function ack(alert: RiskAlert) {
  try {
    await api.post(`/api/assessments/alerts/${alert.id}/acknowledge/`, {})
    alert.is_acknowledged = true
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '确认失败')
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
          <div class="text-sm font-black text-slate-900 tracking-tight">辅导员工作台</div>
          <div class="text-xs text-slate-400 mt-1">预警跟进、干预建议、人工咨询一站式处理</div>
        </div>
        <div class="flex items-center gap-2">
          <ElButton :loading="loading" @click="load">刷新</ElButton>
          <ElButton type="primary" @click="nav('intervention')">创建干预</ElButton>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <StatCard icon="users" label="分配学生" :value="students.length" hint="当前账号名下已分配学生数量" />
      <StatCard icon="alert-triangle" label="待确认预警" :value="unAckCount" hint="需要你确认并跟进的预警" tone="rose" />
      <StatCard icon="shield-check" label="进行中干预" :value="inProgressPlans" hint="未完成的干预建议与跟踪任务" tone="amber" />
      <StatCard icon="message-circle" label="人工会话" :value="conversations.length" hint="与学生的人工咨询会话数" tone="slate" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 space-y-4">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div class="font-bold text-slate-800">风险预警（最新）</div>
            <ElButton size="small" @click="nav('students')">学生档案</ElButton>
          </div>

          <div v-if="alerts.length" class="mt-4 space-y-3">
            <div
              v-for="a in alerts.slice(0, 8)"
              :key="a.id"
              class="p-4 rounded-xl border border-slate-100 bg-slate-50/50 flex items-start justify-between gap-4"
            >
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-xs font-bold px-2 py-1 rounded-lg border" :class="riskPillClass(a.level)">
                    {{ riskLabel(a.level) }}
                  </span>
                  <span class="text-xs font-bold text-slate-700">
                    {{ a.student?.real_name || a.student?.username }}
                  </span>
                  <span class="text-[10px] font-mono text-slate-400">{{ fmtDateTime(a.created_at) }}</span>
                  <ElTag v-if="a.is_acknowledged" size="small" type="success" effect="light">已确认</ElTag>
                  <ElTag v-else size="small" type="warning" effect="light">待确认</ElTag>
                </div>
                <div class="mt-2 text-sm text-slate-600 leading-relaxed">{{ a.message }}</div>
              </div>

              <div class="flex-shrink-0">
                <ElButton v-if="!a.is_acknowledged" size="small" type="warning" @click="ack(a)">确认</ElButton>
              </div>
            </div>
          </div>
          <div v-else class="mt-4">
            <EmptyState title="暂无预警" desc="系统未检测到需要跟进的风险事件。" icon="shield-check" />
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div class="font-bold text-slate-800">干预建议（最新）</div>
            <ElButton size="small" @click="nav('intervention')">进入</ElButton>
          </div>

          <div v-if="plans.length" class="mt-4 space-y-3">
            <div
              v-for="p in plans.slice(0, 6)"
              :key="p.id"
              class="p-4 rounded-xl border border-slate-100 hover:bg-white transition bg-slate-50/50"
            >
              <div class="flex items-center justify-between gap-3 flex-wrap">
                <div class="font-bold text-slate-800 truncate">
                  {{ p.title }}
                </div>
                <div class="text-[10px] font-mono text-slate-400">更新：{{ fmtDateTime(p.updated_at) }}</div>
              </div>
              <div class="mt-2 text-sm text-slate-600">
                学生：<span class="font-semibold">{{ p.student?.real_name || p.student?.username }}</span>
                <span class="mx-2 text-slate-300">·</span>
                状态：<span class="font-semibold">{{ interventionStatusLabel(p.status) }}</span>
              </div>
              <div class="mt-2 text-xs text-slate-500 whitespace-pre-wrap leading-relaxed">{{ p.content }}</div>
            </div>
          </div>
          <div v-else class="mt-4">
            <EmptyState title="暂无干预记录" desc="你可以从学生档案或预警列表创建干预建议。" icon="sparkles" />
          </div>
        </div>
      </div>

      <div class="space-y-4">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="font-bold text-slate-800">快捷操作</div>
          <div class="mt-4 grid grid-cols-1 gap-3">
            <button
              class="w-full flex items-center justify-between gap-3 p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white transition"
              @click="nav('students')"
            >
              <div class="text-left">
                <div class="font-bold text-sm text-slate-800">学生档案</div>
                <div class="text-xs text-slate-400 mt-0.5">查看分配学生的评估/预警/干预</div>
              </div>
              <span class="text-xs text-slate-400">进入</span>
            </button>

            <button
              class="w-full flex items-center justify-between gap-3 p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white transition"
              @click="nav('consult')"
            >
              <div class="text-left">
                <div class="font-bold text-sm text-slate-800">人工咨询</div>
                <div class="text-xs text-slate-400 mt-0.5">与学生进行安全合规的对话</div>
              </div>
              <span class="text-xs text-slate-400">进入</span>
            </button>
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="font-bold text-slate-800">工作提醒</div>
          <div class="mt-3 text-xs text-slate-500 leading-relaxed">
            对高风险学生建议优先完成「确认预警 → 人工咨询 → 干预建议 → 跟踪」闭环，并在系统内留痕记录。
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
