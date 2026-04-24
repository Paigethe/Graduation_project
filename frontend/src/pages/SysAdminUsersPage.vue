<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
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
import { fetchAll } from '../api/pagination'
import type { ClassGroupLite, College, MajorLite, PageResp, Role, UserLite } from '../api/types'
import { fmtDateTime } from '../app/format'
import EmptyState from '../components/EmptyState.vue'
import LucideIcon from '../components/LucideIcon.vue'

type AdminUser = UserLite & { student_no?: string; phone?: string }

type DirectAssignment = {
  id: number
  counselor: UserLite
  student: UserLite
  created_at: string
}

type ClassAssignment = {
  id: number
  counselor: UserLite
  class_group: ClassGroupLite
  created_at: string
}

const tab = ref<'users' | 'class_assignments' | 'direct_assignments'>('users')
const loading = ref(false)

const users = ref<AdminUser[]>([])
const colleges = ref<College[]>([])
const majors = ref<MajorLite[]>([])
const classes = ref<ClassGroupLite[]>([])
const directAssignments = ref<DirectAssignment[]>([])
const classAssignments = ref<ClassAssignment[]>([])

const q = ref('')
const roleFilter = ref<'all' | Role>('all')
const collegeFilter = ref<number | null>(null)
const majorFilter = ref<number | null>(null)
const classFilter = ref<number | null>(null)

const majorOptions = computed(() => {
  if (!collegeFilter.value) return majors.value
  return majors.value.filter((m) => m.college?.id === collegeFilter.value)
})
const classOptions = computed(() => {
  if (majorFilter.value) return classes.value.filter((c) => c.major?.id === majorFilter.value)
  if (collegeFilter.value) return classes.value.filter((c) => c.major?.college?.id === collegeFilter.value)
  return classes.value
})

const filteredUsers = computed(() => {
  const s = q.value.trim()
  return users.value.filter((u) => {
    if (roleFilter.value !== 'all' && u.role !== roleFilter.value) return false
    if (collegeFilter.value && u.college?.id !== collegeFilter.value) return false
    if (majorFilter.value && u.major?.id !== majorFilter.value) return false
    if (classFilter.value && u.class_group?.id !== classFilter.value) return false
    if (!s) return true
    return (
      (u.username + (u.real_name || '') + (u.college?.name || '') + (u.major?.name || '') + (u.class_group?.name || '')).includes(s)
    )
  })
})

watch(collegeFilter, () => {
  if (majorFilter.value && !majorOptions.value.some((m) => m.id === majorFilter.value)) {
    majorFilter.value = null
  }
  if (classFilter.value && !classOptions.value.some((c) => c.id === classFilter.value)) {
    classFilter.value = null
  }
})

watch(majorFilter, () => {
  if (classFilter.value && !classOptions.value.some((c) => c.id === classFilter.value)) {
    classFilter.value = null
  }
})

const userDialog = ref(false)
const userSaving = ref(false)
const userForm = reactive({
  username: '',
  real_name: '',
  role: 'student' as Role,
  college_id: null as number | null,
  major_id: null as number | null,
  class_group_id: null as number | null,
  student_no: '',
  phone: '',
  password: '',
})

const userMajorOptions = computed(() => {
  if (!userForm.college_id) return majors.value
  return majors.value.filter((m) => m.college?.id === userForm.college_id)
})
const userClassOptions = computed(() => {
  if (userForm.major_id) return classes.value.filter((c) => c.major?.id === userForm.major_id)
  if (userForm.college_id) return classes.value.filter((c) => c.major?.college?.id === userForm.college_id)
  return classes.value
})

watch(
  () => userForm.college_id,
  () => {
    if (userForm.major_id && !userMajorOptions.value.some((m) => m.id === userForm.major_id)) {
      userForm.major_id = null
    }
    if (userForm.class_group_id && !userClassOptions.value.some((c) => c.id === userForm.class_group_id)) {
      userForm.class_group_id = null
    }
  },
)
watch(
  () => userForm.major_id,
  () => {
    if (userForm.class_group_id && !userClassOptions.value.some((c) => c.id === userForm.class_group_id)) {
      userForm.class_group_id = null
    }
  },
)

watch(
  () => userForm.class_group_id,
  (id) => {
    if (!id) return
    const cls = classes.value.find((c) => c.id === id)
    if (!cls) return
    userForm.major_id = cls.major?.id ?? null
    userForm.college_id = cls.major?.college?.id ?? null
  },
)

watch(
  () => userForm.major_id,
  (id) => {
    if (!id) return
    const m = majors.value.find((item) => item.id === id)
    if (!m) return
    userForm.college_id = m.college?.id ?? null
  },
)

function openCreateUser() {
  userForm.username = ''
  userForm.real_name = ''
  userForm.role = 'student'
  userForm.college_id = colleges.value[0]?.id ?? null
  userForm.major_id = null
  userForm.class_group_id = null
  userForm.student_no = ''
  userForm.phone = ''
  userForm.password = ''
  userDialog.value = true
}

async function createUser() {
  if (!userForm.username.trim()) return ElMessage.warning('请填写用户名/账号')
  if (!userForm.password) return ElMessage.warning('请填写密码')
  if (userForm.role !== 'sys_admin' && !userForm.college_id) return ElMessage.warning('该角色必须绑定学院')

  userSaving.value = true
  try {
    const { data } = await api.post<AdminUser>('/api/admin/users/', {
      username: userForm.username.trim(),
      real_name: userForm.real_name.trim(),
      role: userForm.role,
      college_id: userForm.college_id,
      major_id: userForm.major_id,
      class_group_id: userForm.class_group_id,
      student_no: userForm.student_no.trim(),
      phone: userForm.phone.trim(),
      password: userForm.password,
    })
    users.value = [data, ...users.value]
    ElMessage.success('用户已创建')
    userDialog.value = false
  } catch (err: any) {
    const msg =
      err?.response?.data?.username?.[0] ||
      err?.response?.data?.college_id?.[0] ||
      err?.response?.data?.major_id?.[0] ||
      err?.response?.data?.class_group_id?.[0] ||
      err?.response?.data?.detail ||
      '创建失败'
    ElMessage.error(msg)
  } finally {
    userSaving.value = false
  }
}

const majorDialog = ref(false)
const majorSaving = ref(false)
const majorForm = reactive({
  college_id: null as number | null,
  name: '',
})

function openCreateMajor() {
  majorForm.college_id = colleges.value[0]?.id ?? null
  majorForm.name = ''
  majorDialog.value = true
}

async function createMajor() {
  if (!majorForm.college_id) return ElMessage.warning('请选择学院')
  if (!majorForm.name.trim()) return ElMessage.warning('请填写专业名称')
  majorSaving.value = true
  try {
    const { data } = await api.post<MajorLite>('/api/majors/', {
      college_id: majorForm.college_id,
      name: majorForm.name.trim(),
    })
    majors.value = [...majors.value, data]
    ElMessage.success('专业已创建')
    majorDialog.value = false
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    majorSaving.value = false
  }
}

const classDialog = ref(false)
const classSaving = ref(false)
const classForm = reactive({
  major_id: null as number | null,
  name: '',
})

function openCreateClass() {
  classForm.major_id = majorOptions.value[0]?.id ?? majors.value[0]?.id ?? null
  classForm.name = ''
  classDialog.value = true
}

async function createClassGroup() {
  if (!classForm.major_id) return ElMessage.warning('请选择专业')
  if (!classForm.name.trim()) return ElMessage.warning('请填写班级名称')
  classSaving.value = true
  try {
    const { data } = await api.post<ClassGroupLite>('/api/classes/', {
      major_id: classForm.major_id,
      name: classForm.name.trim(),
    })
    classes.value = [...classes.value, data]
    ElMessage.success('班级已创建')
    classDialog.value = false
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    classSaving.value = false
  }
}

const classAssignDialog = ref(false)
const classAssignSaving = ref(false)
const classAssignForm = reactive({
  counselor_id: null as number | null,
  college_id: null as number | null,
  major_id: null as number | null,
  class_group_id: null as number | null,
})

const counselors = computed(() => users.value.filter((u) => u.role === 'counselor'))

const assignMajorOptions = computed(() => {
  if (!classAssignForm.college_id) return majors.value
  return majors.value.filter((m) => m.college?.id === classAssignForm.college_id)
})

const assignClassOptions = computed(() => {
  if (classAssignForm.major_id) return classes.value.filter((c) => c.major?.id === classAssignForm.major_id)
  if (classAssignForm.college_id) return classes.value.filter((c) => c.major?.college?.id === classAssignForm.college_id)
  return classes.value
})

const assignCounselorOptions = computed(() => {
  if (!classAssignForm.college_id) return counselors.value
  return counselors.value.filter((c) => c.college?.id === classAssignForm.college_id)
})

const availableAssignClasses = computed(() => {
  const occupiedByOthers = new Set(
    classAssignments.value
      .filter((a) => a.counselor?.id !== classAssignForm.counselor_id)
      .map((a) => a.class_group?.id),
  )
  return assignClassOptions.value.filter((cls) => !occupiedByOthers.has(cls.id))
})

watch(
  () => classAssignForm.college_id,
  () => {
    if (classAssignForm.major_id && !assignMajorOptions.value.some((m) => m.id === classAssignForm.major_id)) {
      classAssignForm.major_id = null
    }
    if (classAssignForm.class_group_id && !availableAssignClasses.value.some((c) => c.id === classAssignForm.class_group_id)) {
      classAssignForm.class_group_id = null
    }
    if (classAssignForm.counselor_id && !assignCounselorOptions.value.some((c) => c.id === classAssignForm.counselor_id)) {
      classAssignForm.counselor_id = null
    }
  },
)

watch(
  () => classAssignForm.major_id,
  () => {
    if (classAssignForm.class_group_id && !availableAssignClasses.value.some((c) => c.id === classAssignForm.class_group_id)) {
      classAssignForm.class_group_id = null
    }
  },
)

watch(
  () => classAssignForm.class_group_id,
  (id) => {
    if (!id) return
    const cls = classes.value.find((c) => c.id === id)
    if (!cls) return
    classAssignForm.major_id = cls.major?.id ?? null
    classAssignForm.college_id = cls.major?.college?.id ?? null
  },
)

watch(
  () => classAssignForm.major_id,
  (id) => {
    if (!id) return
    const m = majors.value.find((item) => item.id === id)
    if (!m) return
    classAssignForm.college_id = m.college?.id ?? null
  },
)

function openClassAssign() {
  classAssignForm.college_id = colleges.value[0]?.id ?? null
  classAssignForm.major_id = null
  classAssignForm.class_group_id = null
  classAssignForm.counselor_id = null
  classAssignDialog.value = true
}

async function createClassAssignment() {
  if (!classAssignForm.counselor_id) return ElMessage.warning('请选择咨询教师')
  if (!classAssignForm.class_group_id) return ElMessage.warning('请选择班级')

  classAssignSaving.value = true
  try {
    const { data } = await api.post<ClassAssignment>('/api/admin/class-assignments/', {
      counselor_id: classAssignForm.counselor_id,
      class_group_id: classAssignForm.class_group_id,
    })
    classAssignments.value = [data, ...classAssignments.value]
    ElMessage.success('班级分配已创建')
    classAssignDialog.value = false
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    classAssignSaving.value = false
  }
}

const directAssignDialog = ref(false)
const directAssignSaving = ref(false)
const directAssignForm = reactive({
  counselor_id: null as number | null,
  student_id: null as number | null,
})

const students = computed(() => users.value.filter((u) => u.role === 'student'))

function openDirectAssign() {
  directAssignForm.counselor_id = counselors.value[0]?.id ?? null
  directAssignForm.student_id = students.value[0]?.id ?? null
  directAssignDialog.value = true
}

async function createDirectAssignment() {
  if (!directAssignForm.counselor_id) return ElMessage.warning('请选择咨询教师')
  if (!directAssignForm.student_id) return ElMessage.warning('请选择学生')
  directAssignSaving.value = true
  try {
    const { data } = await api.post<DirectAssignment>('/api/admin/assignments/', {
      counselor_id: directAssignForm.counselor_id,
      student_id: directAssignForm.student_id,
    })
    directAssignments.value = [data, ...directAssignments.value]
    ElMessage.success('学生直分配已创建')
    directAssignDialog.value = false
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '创建失败')
  } finally {
    directAssignSaving.value = false
  }
}

async function loadAll() {
  loading.value = true
  try {
    const [uResp, cResp, majorRows, classRows, classAssignResp, directAssignResp] = await Promise.all([
      api.get<PageResp<AdminUser>>('/api/admin/users/'),
      api.get<PageResp<College>>('/api/colleges/'),
      fetchAll<MajorLite>('/api/majors/', 50),
      fetchAll<ClassGroupLite>('/api/classes/', 50),
      api.get<PageResp<ClassAssignment>>('/api/admin/class-assignments/'),
      api.get<PageResp<DirectAssignment>>('/api/admin/assignments/'),
    ])

    users.value = uResp.data.results ?? []
    colleges.value = cResp.data.results ?? []
    majors.value = majorRows
    classes.value = classRows
    classAssignments.value = classAssignResp.data.results ?? []
    directAssignments.value = directAssignResp.data.results ?? []
  } catch (err: any) {
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
          <div class="text-sm font-black text-slate-900 tracking-tight">用户与权限</div>
          <div class="text-xs text-slate-400 mt-1">支持学院 → 专业 → 班级分配与筛选，咨询教师按班级分配</div>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <ElButton :loading="loading" @click="loadAll">刷新</ElButton>
          <ElButton @click="openCreateMajor">新建专业</ElButton>
          <ElButton @click="openCreateClass">新建班级</ElButton>
          <ElButton type="primary" @click="openCreateUser">
            <LucideIcon name="plus" class="w-4 h-4" />
            新建用户
          </ElButton>
        </div>
      </div>
    </div>

    <ElTabs v-model="tab">
      <ElTabPane label="用户列表" name="users">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-3">
          <div class="flex items-center gap-2 flex-wrap">
            <ElInput v-model="q" placeholder="搜索账号/姓名/学院/专业/班级…" clearable class="w-[300px]" />
            <ElSelect v-model="roleFilter" class="w-36">
              <el-option label="全部角色" value="all" />
              <el-option label="学生" value="student" />
              <el-option label="心理辅导员" value="counselor" />
              <el-option label="二级学院管理员" value="college_admin" />
              <el-option label="系统管理员" value="sys_admin" />
            </ElSelect>
            <ElSelect v-model="collegeFilter" clearable filterable class="w-44" placeholder="学院">
              <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
            </ElSelect>
            <ElSelect v-model="majorFilter" clearable filterable class="w-44" placeholder="专业">
              <el-option v-for="m in majorOptions" :key="m.id" :label="m.name" :value="m.id" />
            </ElSelect>
            <ElSelect v-model="classFilter" clearable filterable class="w-44" placeholder="班级">
              <el-option v-for="c in classOptions" :key="c.id" :label="c.name" :value="c.id" />
            </ElSelect>
          </div>
          <ElTag type="info" effect="light">筛选结果 {{ filteredUsers.length }} / {{ users.length }}</ElTag>
        </div>

        <div v-if="filteredUsers.length" class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            v-for="u in filteredUsers"
            :key="u.id"
            class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="font-bold text-slate-900 truncate">{{ u.real_name || u.username }}</div>
                <div class="text-xs text-slate-400 mt-1 truncate">
                  {{ u.username }} · {{ u.college?.name || '未绑定学院' }}
                </div>
                <div class="mt-2 text-xs text-slate-500 space-y-1">
                  <div>角色：<span class="font-semibold">{{ u.role }}</span></div>
                  <div>专业：<span class="font-semibold">{{ u.major?.name || '—' }}</span></div>
                  <div>班级：<span class="font-semibold">{{ u.class_group?.name || '—' }}</span></div>
                </div>
              </div>
              <ElTag size="small" effect="light" type="info">#{{ u.id }}</ElTag>
            </div>
          </div>
        </div>

        <EmptyState v-else title="暂无用户" desc="请先创建用户，或调整筛选条件。" icon="users" />
      </ElTabPane>

      <ElTabPane label="班级分配" name="class_assignments">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div class="font-bold text-slate-800">咨询教师 ↔ 班级分配</div>
              <div class="text-xs text-slate-400 mt-1">同一个班级只允许分配给一个咨询教师</div>
            </div>
            <ElButton type="primary" @click="openClassAssign">
              <LucideIcon name="plus" class="w-4 h-4" />
              新建班级分配
            </ElButton>
          </div>
        </div>

        <div v-if="classAssignments.length" class="mt-4 space-y-3">
          <div
            v-for="a in classAssignments"
            :key="a.id"
            class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6"
          >
            <div class="flex items-start justify-between gap-4">
              <div>
                <div class="font-bold text-slate-900">
                  {{ a.counselor?.real_name || a.counselor?.username }}
                  <span class="mx-2 text-slate-300">→</span>
                  {{ a.class_group?.major?.college?.name || '—' }} / {{ a.class_group?.major?.name || '—' }} / {{ a.class_group?.name || '—' }}
                </div>
                <div class="text-xs text-slate-400 mt-1">
                  创建时间：<span class="font-mono">{{ fmtDateTime(a.created_at) }}</span>
                </div>
              </div>
              <ElTag size="small" effect="light" type="info">#{{ a.id }}</ElTag>
            </div>
          </div>
        </div>

        <EmptyState v-else title="暂无班级分配" desc="创建后，辅导员会自动获得该班级学生可见权限。" icon="users" />
      </ElTabPane>

      <ElTabPane label="学生直分配(兼容)" name="direct_assignments">
        <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div class="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div class="font-bold text-slate-800">咨询教师 ↔ 学生直分配</div>
              <div class="text-xs text-slate-400 mt-1">历史兼容方式，建议优先使用班级分配</div>
            </div>
            <ElButton type="primary" @click="openDirectAssign">
              <LucideIcon name="plus" class="w-4 h-4" />
              新建直分配
            </ElButton>
          </div>
        </div>

        <div v-if="directAssignments.length" class="mt-4 space-y-3">
          <div
            v-for="a in directAssignments"
            :key="a.id"
            class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6"
          >
            <div class="flex items-start justify-between gap-4">
              <div>
                <div class="font-bold text-slate-900">
                  {{ a.counselor?.real_name || a.counselor?.username }}
                  <span class="mx-2 text-slate-300">→</span>
                  {{ a.student?.real_name || a.student?.username }}
                </div>
                <div class="text-xs text-slate-400 mt-1">创建时间：{{ fmtDateTime(a.created_at) }}</div>
              </div>
              <ElTag size="small" effect="light" type="info">#{{ a.id }}</ElTag>
            </div>
          </div>
        </div>

        <EmptyState v-else title="暂无直分配" desc="可选兼容能力，不影响班级分配流程。" icon="users" />
      </ElTabPane>
    </ElTabs>

    <ElDialog v-model="majorDialog" title="新建专业" width="520px">
      <ElForm label-position="top">
        <ElFormItem label="学院">
          <ElSelect v-model="majorForm.college_id" filterable class="w-full">
            <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="专业名称">
          <ElInput v-model="majorForm.name" placeholder="例如：计算机科学与技术" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="majorDialog = false">取消</ElButton>
          <ElButton type="primary" :loading="majorSaving" @click="createMajor">创建</ElButton>
        </div>
      </template>
    </ElDialog>

    <ElDialog v-model="classDialog" title="新建班级" width="520px">
      <ElForm label-position="top">
        <ElFormItem label="专业">
          <ElSelect v-model="classForm.major_id" filterable class="w-full">
            <el-option
              v-for="m in majors"
              :key="m.id"
              :label="`${m.college?.name || '—'} / ${m.name}`"
              :value="m.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="班级名称">
          <ElInput v-model="classForm.name" placeholder="例如：计科 2022 级 3 班" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="classDialog = false">取消</ElButton>
          <ElButton type="primary" :loading="classSaving" @click="createClassGroup">创建</ElButton>
        </div>
      </template>
    </ElDialog>

    <ElDialog v-model="userDialog" title="新建用户" width="760px">
      <ElForm label-position="top">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <ElFormItem label="账号/用户名">
            <ElInput v-model="userForm.username" placeholder="例如：student3" />
          </ElFormItem>
          <ElFormItem label="真实姓名">
            <ElInput v-model="userForm.real_name" placeholder="可选" />
          </ElFormItem>
          <ElFormItem label="角色">
            <ElSelect v-model="userForm.role" class="w-full">
              <el-option label="学生" value="student" />
              <el-option label="心理辅导员" value="counselor" />
              <el-option label="二级学院管理员" value="college_admin" />
              <el-option label="系统管理员" value="sys_admin" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem :label="userForm.role === 'sys_admin' ? '学院（可选）' : '学院（必选）'">
            <ElSelect v-model="userForm.college_id" filterable clearable class="w-full" placeholder="不绑定则为全局账号">
              <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="专业（可选）">
            <ElSelect v-model="userForm.major_id" filterable clearable class="w-full" placeholder="选择专业">
              <el-option v-for="m in userMajorOptions" :key="m.id" :label="m.name" :value="m.id" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="班级（可选）">
            <ElSelect v-model="userForm.class_group_id" filterable clearable class="w-full" placeholder="选择班级">
              <el-option v-for="c in userClassOptions" :key="c.id" :label="c.name" :value="c.id" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem v-if="userForm.role === 'student'" label="学号（可选）">
            <ElInput v-model="userForm.student_no" placeholder="例如：2021010101" />
          </ElFormItem>
          <ElFormItem label="手机号（可选）">
            <ElInput v-model="userForm.phone" placeholder="例如：13800000000" />
          </ElFormItem>
        </div>
        <ElFormItem label="初始密码">
          <ElInput v-model="userForm.password" type="password" show-password placeholder="至少 6 位" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="userDialog = false">取消</ElButton>
          <ElButton type="primary" :loading="userSaving" @click="createUser">创建</ElButton>
        </div>
      </template>
    </ElDialog>

    <ElDialog v-model="classAssignDialog" title="新建班级分配" width="620px">
      <ElForm label-position="top">
        <ElFormItem label="学院">
          <ElSelect v-model="classAssignForm.college_id" filterable clearable class="w-full" placeholder="选择学院">
            <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="咨询教师">
          <ElSelect v-model="classAssignForm.counselor_id" filterable class="w-full" placeholder="选择咨询教师">
            <el-option
              v-for="c in assignCounselorOptions"
              :key="c.id"
              :label="`${c.real_name || c.username}（${c.username}）`"
              :value="c.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="专业">
          <ElSelect v-model="classAssignForm.major_id" filterable clearable class="w-full" placeholder="选择专业">
            <el-option v-for="m in assignMajorOptions" :key="m.id" :label="m.name" :value="m.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="班级">
          <ElSelect v-model="classAssignForm.class_group_id" filterable class="w-full" placeholder="选择班级">
            <el-option v-for="c in availableAssignClasses" :key="c.id" :label="c.name" :value="c.id" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="classAssignDialog = false">取消</ElButton>
          <ElButton type="primary" :loading="classAssignSaving" @click="createClassAssignment">创建</ElButton>
        </div>
      </template>
    </ElDialog>

    <ElDialog v-model="directAssignDialog" title="新建学生直分配" width="560px">
      <ElForm label-position="top">
        <ElFormItem label="咨询教师">
          <ElSelect v-model="directAssignForm.counselor_id" filterable class="w-full">
            <el-option v-for="c in counselors" :key="c.id" :label="`${c.real_name || c.username}（${c.username}）`" :value="c.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="学生">
          <ElSelect v-model="directAssignForm.student_id" filterable class="w-full">
            <el-option v-for="s in students" :key="s.id" :label="`${s.real_name || s.username}（${s.username}）`" :value="s.id" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="directAssignDialog = false">取消</ElButton>
          <ElButton type="primary" :loading="directAssignSaving" @click="createDirectAssignment">创建</ElButton>
        </div>
      </template>
    </ElDialog>
  </div>
</template>
