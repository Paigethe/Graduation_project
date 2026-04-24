<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAuthStore } from './stores/auth'
import AuthPage from './pages/AuthPage.vue'
import AppShell from './components/AppShell.vue'

const auth = useAuthStore()
const ready = ref(false)

const isLoggedIn = computed(() => Boolean(auth.accessToken && auth.me))

onMounted(async () => {
  if (auth.accessToken && !auth.me) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
    }
  }
  ready.value = true
})
</script>

<template>
  <div v-if="!ready" class="min-h-screen grid place-items-center text-slate-400 text-sm">加载中…</div>
  <AuthPage v-else-if="!isLoggedIn" />
  <AppShell v-else />
</template>
