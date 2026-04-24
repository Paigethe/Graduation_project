<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { ElAvatar, ElButton } from 'element-plus'

import { MENU_CONFIG, ROLE_LABEL, menuName, type MenuId } from '../app/menu'
import { useAuthStore } from '../stores/auth'
import LucideIcon from './LucideIcon.vue'
import PlaceholderPanel from './PlaceholderPanel.vue'

const AdminMonitorDashboard = defineAsyncComponent(() => import('../pages/AdminMonitorDashboard.vue'))
const BackupPage = defineAsyncComponent(() => import('../pages/BackupPage.vue'))
const ChatPage = defineAsyncComponent(() => import('../pages/ChatPage.vue'))
const CollegeDashboardPage = defineAsyncComponent(() => import('../pages/CollegeDashboardPage.vue'))
const CollegeAnalysisPage = defineAsyncComponent(() => import('../pages/CollegeAnalysisPage.vue'))
const CollegeProgressPage = defineAsyncComponent(() => import('../pages/CollegeProgressPage.vue'))
const CollegeReportsPage = defineAsyncComponent(() => import('../pages/CollegeReportsPage.vue'))
const CounselorDashboardPage = defineAsyncComponent(() => import('../pages/CounselorDashboardPage.vue'))
const CounselorInterventionsPage = defineAsyncComponent(() => import('../pages/CounselorInterventionsPage.vue'))
const CounselorStudentsPage = defineAsyncComponent(() => import('../pages/CounselorStudentsPage.vue'))
const KnowledgePage = defineAsyncComponent(() => import('../pages/KnowledgePage.vue'))
const StudentDashboardPage = defineAsyncComponent(() => import('../pages/StudentDashboardPage.vue'))
const StudentInterventionsPage = defineAsyncComponent(() => import('../pages/StudentInterventionsPage.vue'))
const StudentReportPage = defineAsyncComponent(() => import('../pages/StudentReportPage.vue'))
const SurveyPage = defineAsyncComponent(() => import('../pages/SurveyPage.vue'))
const SysAdminCollegeRiskPage = defineAsyncComponent(() => import('../pages/SysAdminCollegeRiskPage.vue'))
const SysAdminDatabasePage = defineAsyncComponent(() => import('../pages/SysAdminDatabasePage.vue'))
const SysAdminSecurityPage = defineAsyncComponent(() => import('../pages/SysAdminSecurityPage.vue'))
const SysAdminUsersPage = defineAsyncComponent(() => import('../pages/SysAdminUsersPage.vue'))

const auth = useAuthStore()

const role = computed(() => auth.me?.role ?? 'student')
const roleLabel = computed(() => ROLE_LABEL[role.value])
const menu = computed(() => MENU_CONFIG[role.value])

const activeTab = ref<MenuId>('dashboard')

const nowText = ref(dayjs().format('YYYY-MM-DD HH:mm'))
let timer: number | undefined

function syncActiveTab() {
  const first = menu.value[0]?.id ?? 'dashboard'
  if (!menu.value.some((m) => m.id === activeTab.value)) activeTab.value = first
}

function logout() {
  auth.logout()
}

watch(menu, syncActiveTab, { immediate: true })

onMounted(() => {
  timer = window.setInterval(() => {
    nowText.value = dayjs().format('YYYY-MM-DD HH:mm')
  }, 30_000)
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="flex min-h-screen">
    <aside class="w-64 bg-slate-900 text-slate-300 flex flex-col flex-shrink-0">
      <div class="p-6 border-b border-slate-800 flex items-center gap-3">
        <div class="p-2 bg-indigo-600 rounded text-white shadow-lg">
          <LucideIcon name="brain-circuit" class="w-5 h-5" />
        </div>
        <span class="font-black text-white tracking-tighter">MH-SYSTEM</span>
      </div>

      <nav class="flex-1 p-4 space-y-1 overflow-y-auto">
        <div
          v-for="item in menu"
          :key="item.id"
          role="button"
          tabindex="0"
          @click="activeTab = item.id"
          @keyup.enter="activeTab = item.id"
          :class="['sidebar-item', activeTab === item.id ? 'active' : '']"
        >
          <LucideIcon :name="item.icon" class="w-4 h-4" />
          <span class="font-medium">{{ item.name }}</span>
        </div>
      </nav>

      <div class="p-4 border-t border-slate-800 space-y-3">
        <div class="bg-slate-800/40 border border-slate-800 rounded-lg p-3">
          <div class="text-xs text-slate-300 font-bold truncate">
            {{ auth.me?.real_name || auth.me?.username }}
          </div>
          <div class="text-[10px] text-slate-400 mt-1 truncate">
            {{ auth.me?.college?.name || '未绑定学院' }} · {{ roleLabel }}
          </div>
        </div>
        <ElButton plain type="danger" size="small" class="w-full" @click="logout">退出系统</ElButton>
      </div>
    </aside>

    <main class="flex-1 flex flex-col h-screen overflow-hidden">
      <header class="h-16 bg-white border-b flex items-center justify-between px-8 flex-shrink-0 shadow-sm z-10">
        <div class="flex items-center gap-2">
          <span class="text-slate-300 font-mono text-[10px] tracking-widest uppercase">/ {{ roleLabel }} /</span>
          <h2 class="text-sm font-bold text-slate-600 uppercase">{{ menuName(role, activeTab) }}</h2>
        </div>
        <div class="flex items-center gap-4">
          <div class="text-right hidden sm:block">
            <p class="text-xs font-bold text-slate-700">{{ auth.me?.real_name || auth.me?.username }}</p>
            <p class="text-[10px] text-slate-400">{{ nowText }}</p>
          </div>
          <ElAvatar :size="32" class="!bg-indigo-600 !text-white !font-black">
            {{ (auth.me?.real_name || auth.me?.username || 'U').slice(0, 1) }}
          </ElAvatar>
        </div>
      </header>

      <div class="flex-1 overflow-y-auto p-8 bg-slate-50/50">
        <div class="max-w-6xl mx-auto">
          <!-- Sys admin -->
          <AdminMonitorDashboard v-if="role === 'sys_admin' && activeTab === 'dashboard'" />
          <SysAdminCollegeRiskPage v-else-if="role === 'sys_admin' && activeTab === 'college_risk'" />
          <SysAdminUsersPage v-else-if="role === 'sys_admin' && activeTab === 'users'" />
          <SysAdminSecurityPage v-else-if="role === 'sys_admin' && activeTab === 'security'" />
          <SysAdminDatabasePage v-else-if="role === 'sys_admin' && activeTab === 'database'" />

          <!-- College admin -->
          <CollegeDashboardPage v-else-if="role === 'college_admin' && activeTab === 'dashboard'" :on-navigate="(id) => (activeTab = id)" />
          <CollegeAnalysisPage v-else-if="role === 'college_admin' && activeTab === 'analysis'" />
          <CollegeProgressPage v-else-if="role === 'college_admin' && activeTab === 'progress'" />
          <CollegeReportsPage v-else-if="role === 'college_admin' && activeTab === 'reports'" />
          <BackupPage v-else-if="role === 'college_admin' && activeTab === 'backup'" />
          <BackupPage v-else-if="role === 'sys_admin' && activeTab === 'backup'" />

          <!-- Counselor -->
          <CounselorDashboardPage v-else-if="role === 'counselor' && activeTab === 'dashboard'" :on-navigate="(id) => (activeTab = id)" />
          <CounselorStudentsPage v-else-if="role === 'counselor' && activeTab === 'students'" :on-navigate="(id) => (activeTab = id)" />
          <CounselorInterventionsPage v-else-if="role === 'counselor' && activeTab === 'intervention'" />

          <!-- Student -->
          <StudentDashboardPage v-else-if="role === 'student' && activeTab === 'dashboard'" :on-navigate="(id) => (activeTab = id)" />
          <SurveyPage v-else-if="role === 'student' && activeTab === 'survey'" :on-navigate="(id) => (activeTab = id)" />
          <KnowledgePage v-else-if="role === 'student' && activeTab === 'knowledge'" />
          <StudentReportPage v-else-if="role === 'student' && activeTab === 'report'" />
          <StudentInterventionsPage v-else-if="role === 'student' && activeTab === 'intervention'" :on-navigate="(id) => (activeTab = id)" />

          <!-- Chat -->
          <ChatPage v-else-if="activeTab === 'ai_chat'" mode="ai_chat" :on-navigate="(id) => (activeTab = id)" />
          <ChatPage v-else-if="activeTab === 'consult'" mode="consult" :on-navigate="(id) => (activeTab = id)" />

          <PlaceholderPanel v-else :title="menuName(role, activeTab)">
            <template #icon>
              <LucideIcon name="activity" class="w-12 h-12 mx-auto" />
            </template>
          </PlaceholderPanel>
        </div>
      </div>
    </main>
  </div>
</template>
