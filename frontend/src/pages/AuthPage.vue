<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { ElButton, ElForm, ElFormItem, ElInput, ElMessage, ElSelect, ElTabPane, ElTabs } from 'element-plus'

import { api } from '../api/client'
import type { College, MajorLite, ClassGroupLite } from '../api/types'
import { useAuthStore } from '../stores/auth'
import LucideIcon from '../components/LucideIcon.vue'

const auth = useAuthStore()

const authTab = ref<'login' | 'register'>('login')
const loading = ref(false)

const colleges = ref<College[]>([])
const majors = ref<MajorLite[]>([])
const classGroups = ref<ClassGroupLite[]>([])

const loginForm = reactive({
  username: 'student1',
  password: '123456',
})

const registerForm = reactive({
  username: '',
  real_name: '',
  college_id: undefined as number | undefined,
  major_id: undefined as number | undefined,
  class_group_id: undefined as number | undefined,
  password: '',
  password2: '',
})

async function loadColleges() {
  try {
    const { data } = await api.get('/api/colleges/')
    colleges.value = data.results ?? data ?? []
  } catch {
    colleges.value = []
  }
}

async function loadMajors(collegeId?: number) {
  if (!collegeId) {
    majors.value = []
    return
  }
  try {
    const { data } = await api.get('/api/majors/', { params: { college_id: collegeId } })
    majors.value = data.results ?? data ?? []
  } catch {
    majors.value = []
  }
}

async function loadClassGroups(majorId?: number) {
  if (!majorId) {
    classGroups.value = []
    return
  }
  try {
    const { data } = await api.get('/api/classes/', { params: { major_id: majorId } })
    classGroups.value = data.results ?? data ?? []
  } catch {
    classGroups.value = []
  }
}

async function handleLogin() {
  loading.value = true
  try {
    await auth.login(loginForm.username.trim(), loginForm.password)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '登录失败，请检查账号密码')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!registerForm.username.trim()) return ElMessage.warning('请填写账号/学号')
  if (!registerForm.real_name.trim()) return ElMessage.warning('请填写真实姓名')
  if (!registerForm.college_id) return ElMessage.warning('请选择二级学院')
  if (!registerForm.major_id) return ElMessage.warning('请选择专业')
  if (!registerForm.class_group_id) return ElMessage.warning('请选择班级')
  if (!registerForm.password) return ElMessage.warning('请设置密码')
  if (registerForm.password !== registerForm.password2) return ElMessage.warning('两次密码不一致')

  loading.value = true
  try {
    await api.post('/api/auth/register/', {
      username: registerForm.username.trim(),
      real_name: registerForm.real_name.trim(),
      college_id: registerForm.college_id,
      major_id: registerForm.major_id,
      class_group_id: registerForm.class_group_id,
      password: registerForm.password,
    })
    ElMessage.success('注册成功，请登录')
    authTab.value = 'login'
    loginForm.username = registerForm.username.trim()
    loginForm.password = registerForm.password
    registerForm.username = ''
    registerForm.real_name = ''
    registerForm.college_id = undefined
    registerForm.major_id = undefined
    registerForm.class_group_id = undefined
    registerForm.password = ''
    registerForm.password2 = ''
  } catch (err: any) {
    const msg =
      err?.response?.data?.username?.[0] ||
      err?.response?.data?.detail ||
      '注册失败，请检查输入'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

onMounted(loadColleges)

watch(() => registerForm.college_id, (newCollegeId) => {
  registerForm.major_id = undefined
  registerForm.class_group_id = undefined
  loadMajors(newCollegeId)
})

watch(() => registerForm.major_id, (newMajorId) => {
  registerForm.class_group_id = undefined
  loadClassGroups(newMajorId)
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4 bg-slate-100 relative overflow-hidden">
    <div class="absolute top-[-10%] left-[-10%] w-96 h-96 bg-indigo-200 rounded-full blur-[100px] opacity-20"></div>
    <div class="max-w-md w-full bg-white rounded-2xl shadow-2xl overflow-hidden border relative z-10">
      <div class="bg-indigo-700 p-8 text-white text-center">
        <LucideIcon name="brain-circuit" class="w-10 h-10 mx-auto mb-3" />
        <h2 class="text-xl font-bold tracking-tight">学生心理健康分析系统</h2>
        <p class="text-indigo-200 text-xs mt-1 uppercase tracking-widest">Graduation Project Implementation</p>
      </div>

      <div class="p-8">
        <ElTabs v-model="authTab">
          <ElTabPane label="账号登录" name="login">
            <ElForm label-position="top" class="mt-4" @submit.prevent>
              <ElFormItem label="账号/学号">
                <ElInput v-model="loginForm.username" placeholder="请输入您的账号" />
              </ElFormItem>
              <ElFormItem label="密码">
                <ElInput v-model="loginForm.password" type="password" placeholder="请输入密码" show-password />
              </ElFormItem>
              <ElButton type="primary" class="w-full h-11 mt-2 font-bold" :loading="loading || auth.loading" @click="handleLogin">
                登 录
              </ElButton>
            </ElForm>
          </ElTabPane>

          <ElTabPane label="学生注册" name="register">
            <ElForm label-position="top" class="mt-4" @submit.prevent>
              <ElFormItem label="账号/学号">
                <ElInput v-model="registerForm.username" placeholder="请输入账号或学号" />
              </ElFormItem>
              <ElFormItem label="真实姓名">
                <ElInput v-model="registerForm.real_name" placeholder="请输入姓名" />
              </ElFormItem>
              <ElFormItem label="所属二级学院">
                <ElSelect v-model="registerForm.college_id" placeholder="请选择学院" class="w-full" filterable>
                  <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
                </ElSelect>
              </ElFormItem>
              <ElFormItem label="专业">
                <ElSelect v-model="registerForm.major_id" placeholder="请选择专业" class="w-full" filterable>
                  <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
                </ElSelect>
              </ElFormItem>
              <ElFormItem label="班级">
                <ElSelect v-model="registerForm.class_group_id" placeholder="请选择班级" class="w-full" filterable>
                  <el-option v-for="c in classGroups" :key="c.id" :label="c.name" :value="c.id" />
                </ElSelect>
              </ElFormItem>
              <ElFormItem label="设置密码">
                <ElInput v-model="registerForm.password" type="password" placeholder="至少 6 位" show-password />
              </ElFormItem>
              <ElFormItem label="确认密码">
                <ElInput v-model="registerForm.password2" type="password" placeholder="再次输入密码" show-password />
              </ElFormItem>
              <ElButton type="success" class="w-full h-11 mt-2 font-bold" :loading="loading" @click="handleRegister">
                立即注册
              </ElButton>
            </ElForm>
          </ElTabPane>
        </ElTabs>
      </div>
    </div>
  </div>
</template>

