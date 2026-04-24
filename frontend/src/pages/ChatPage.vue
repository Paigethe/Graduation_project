<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElButton, ElInput, ElMessage, ElTag } from 'element-plus'

import { api } from '../api/client'
import type { ChatMessage, Conversation, PageResp } from '../api/types'
import type { MenuId } from '../app/menu'
import { fmtDateTime } from '../app/format'
import { riskLabel, riskPillClass } from '../app/risk'
import { useAuthStore } from '../stores/auth'
import EmptyState from '../components/EmptyState.vue'
import LucideIcon from '../components/LucideIcon.vue'

type AiChatResp = {
  conversation: Conversation
  user_message: ChatMessage
  ai_message: ChatMessage
  risk_level: 'low' | 'medium' | 'high'
  ai_meta?: { model_version?: string; source?: string }
  recommendations?: { id: number; title: string; summary: string }[]
  handoff_required?: boolean
  handoff_conversation?: Conversation | null
  handoff_error?: string | null
}

const props = defineProps<{
  mode: 'ai_chat' | 'consult'
  onNavigate?: (id: MenuId) => void
}>()

const auth = useAuthStore()
const role = computed(() => auth.me?.role)

const inputMsg = ref('')
const sending = ref(false)

// Shared
const messages = ref<ChatMessage[]>([])
const activeConvId = ref<number | null>(null)

// Consult (list for counselor/admin)
const convLoading = ref(false)
const conversations = ref<Conversation[]>([])

// AI
const riskLevel = ref<'low' | 'medium' | 'high'>('low')
const showRiskPrompt = ref(false)
const recommendations = ref<{ id: number; title: string; summary: string }[]>([])
let pollTimer: number | undefined

function isMine(msg: ChatMessage) {
  const myId = auth.me?.id
  if (!myId) return msg.sender_kind === 'user'
  if (msg.sender && msg.sender.id) return msg.sender.id === myId
  return msg.sender_kind === 'user'
}

async function scrollBottom() {
  await nextTick()
  const el = document.getElementById('chat-box')
  if (el) el.scrollTop = el.scrollHeight
}

async function loadMessages(convId: number) {
  const { data } = await api.get<ChatMessage[]>(`/api/chat/conversations/${convId}/messages/`)
  messages.value = data ?? []
  if (props.mode === 'consult') {
    try {
      await api.post(`/api/chat/conversations/${convId}/read/`, {})
    } catch {
      // ignore read errors
    }
  }
  await scrollBottom()
}

function startPolling() {
  stopPolling()
  if (props.mode !== 'consult') return
  pollTimer = window.setInterval(async () => {
    const convId = activeConvId.value
    if (!convId) return
    try {
      await loadMessages(convId)
    } catch {
      // ignore polling errors
    }
  }, 1000)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = undefined
  }
}

async function initAi() {
  messages.value = []
  activeConvId.value = null
  showRiskPrompt.value = false
  riskLevel.value = 'low'
  recommendations.value = []

  if (role.value !== 'student') {
    messages.value = [
      {
        id: -1,
        sender_kind: 'ai',
        sender: null,
        content: 'AI 自助仅对学生开放。你可以切换到人工咨询模块查看会话。',
        created_at: new Date().toISOString(),
        read_at: null,
      },
    ]
    return
  }

  // Load existing AI conversation (if any)
  try {
    const { data } = await api.get<PageResp<Conversation>>('/api/chat/conversations/')
    const aiConv = (data.results ?? []).find((c) => c.kind === 'ai')
    if (aiConv) {
      activeConvId.value = aiConv.id
      await loadMessages(aiConv.id)
      if (!messages.value.length) {
        messages.value = [
          {
            id: -1,
            sender_kind: 'ai',
            sender: null,
            content: '您好，我是心理小助手。我可以为您提供 24 小时的咨询支持。你可以告诉我任何困扰。',
            created_at: new Date().toISOString(),
            read_at: null,
          },
        ]
      }
      return
    }
  } catch {
    // ignore; fall back to initial welcome message
  }

  messages.value = [
    {
      id: -1,
      sender_kind: 'ai',
      sender: null,
      content: '您好，我是心理小助手。我可以为您提供 24 小时的咨询支持。你可以告诉我任何困扰。',
      created_at: new Date().toISOString(),
      read_at: null,
    },
  ]
}

async function initConsult() {
  messages.value = []
  activeConvId.value = null
  conversations.value = []

  // Student: single conversation with assigned counselor
  if (role.value === 'student') {
    try {
      const cached = Number(localStorage.getItem('bs001_consult_conv_id') || '')
      if (cached) {
        activeConvId.value = cached
        await loadMessages(cached)
        return
      }
      const { data } = await api.post<Conversation>('/api/chat/conversations/human/start/', {})
      activeConvId.value = data.id
      localStorage.setItem('bs001_consult_conv_id', String(data.id))
      await loadMessages(data.id)
      startPolling()
      return
    } catch (err: any) {
      ElMessage.error(err?.response?.data?.detail || '创建/加载人工会话失败')
      return
    }
  }

  // Counselor / admin: list conversations
  convLoading.value = true
  try {
    const { data } = await api.get<PageResp<Conversation>>('/api/chat/conversations/')
    conversations.value = (data.results ?? []).filter((c) => c.kind === 'human')

    const cached = Number(localStorage.getItem('bs001_consult_conv_id') || '')
    const first = conversations.value.find((c) => c.id === cached) ?? conversations.value[0]
    if (first) {
      activeConvId.value = first.id
      localStorage.setItem('bs001_consult_conv_id', String(first.id))
      await loadMessages(first.id)
      startPolling()
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '加载会话列表失败')
  } finally {
    convLoading.value = false
  }
}

async function sendAiMsg() {
  const text = inputMsg.value.trim()
  if (!text) return
  inputMsg.value = ''

  messages.value.push({
    id: Date.now(),
    sender_kind: 'user',
    sender: auth.me,
    content: text,
    created_at: new Date().toISOString(),
    read_at: null,
  })
  await scrollBottom()

  sending.value = true
  try {
    const placeholderId = Date.now() + 1
    messages.value.push({
      id: placeholderId,
      sender_kind: 'ai',
      sender: null,
      content: '',
      created_at: new Date().toISOString(),
      read_at: null,
    })
    const aiIndex = messages.value.length - 1
    await scrollBottom()

    const data = await streamAiReply(
      text,
      (delta) => {
        const current = messages.value[aiIndex]
        if (!current) return
        current.content = `${current.content || ''}${delta}`
      },
      async () => {
        await scrollBottom()
      },
    )

    activeConvId.value = data.conversation.id
    riskLevel.value = data.risk_level
    showRiskPrompt.value = Boolean(data.handoff_required || data.risk_level === 'high')
    recommendations.value = data.recommendations ?? []

    messages.value[aiIndex] = {
      id: data.ai_message.id,
      sender_kind: 'ai',
      sender: null,
      content: data.ai_message.content,
      created_at: data.ai_message.created_at,
      read_at: data.ai_message.read_at,
    }

    if (data.handoff_conversation?.id) {
      localStorage.setItem('bs001_consult_conv_id', String(data.handoff_conversation.id))
    }
    if (data.handoff_error) {
      ElMessage.warning(data.handoff_error)
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || err?.message || 'AI 调用失败')
    messages.value.push({
      id: Date.now() + 1,
      sender_kind: 'ai',
      sender: null,
      content: '抱歉，我暂时无法响应。请稍后再试。',
      created_at: new Date().toISOString(),
      read_at: null,
    })
  } finally {
    sending.value = false
    await scrollBottom()
  }
}

function parseSseEvent(block: string): { event: string; data: string } | null {
  const lines = block.split('\n')
  let event = 'message'
  const dataLines: string[] = []
  for (const line of lines) {
    const normalized = line.trimEnd()
    if (!normalized || normalized.startsWith(':')) continue
    if (normalized.startsWith('event:')) {
      event = normalized.slice(6).trim()
    } else if (normalized.startsWith('data:')) {
      dataLines.push(normalized.slice(5).trim())
    }
  }
  if (!dataLines.length) return null
  return { event, data: dataLines.join('\n') }
}

async function streamAiReply(
  text: string,
  onDelta: (delta: string) => void,
  onProgress?: () => Promise<void>,
): Promise<AiChatResp> {
  const token = localStorage.getItem('bs001_access_token')
  const resp = await fetch('/api/chat/conversations/ai/stream/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ content: text }),
  })

  if (!resp.ok || !resp.body) {
    let detail = 'AI 调用失败'
    try {
      const payload = await resp.json()
      detail = payload?.detail || detail
    } catch {
      // ignore json parse error
    }
    throw new Error(detail)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let donePayload: AiChatResp | null = null
  let streamError: string | null = null
  let chunkCounter = 0

  const consumeBlock = async (rawBlock: string) => {
    const evt = parseSseEvent(rawBlock)
    if (!evt) return
    let payload: any = {}
    try {
      payload = JSON.parse(evt.data)
    } catch {
      payload = {}
    }

    if (evt.event === 'delta') {
      const delta = String(payload?.content || '')
      if (delta) {
        onDelta(delta)
        chunkCounter += 1
        if (onProgress && (chunkCounter % 3 === 0)) {
          await onProgress()
        }
      }
      return
    }
    if (evt.event === 'done') {
      donePayload = payload as AiChatResp
      return
    }
    if (evt.event === 'error') {
      streamError = String(payload?.detail || '流式响应失败')
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // Normalize line endings so both LF and CRLF SSE streams can be parsed.
    buffer = buffer.replace(/\r\n/g, '\n')
    while (true) {
      const splitAt = buffer.indexOf('\n\n')
      if (splitAt < 0) break
      const block = buffer.slice(0, splitAt)
      buffer = buffer.slice(splitAt + 2)
      await consumeBlock(block)
    }
  }
  buffer += decoder.decode()
  buffer = buffer.replace(/\r\n/g, '\n')
  if (buffer.trim()) {
    await consumeBlock(buffer.trim())
  }

  if (streamError) {
    throw new Error(streamError)
  }
  if (!donePayload) {
    throw new Error('流式响应未完成')
  }
  return donePayload
}

async function sendHumanMsg() {
  const convId = activeConvId.value
  const text = inputMsg.value.trim()
  if (!convId || !text) return

  inputMsg.value = ''
  messages.value.push({
    id: Date.now(),
    sender_kind: 'user',
    sender: auth.me,
    content: text,
    created_at: new Date().toISOString(),
    read_at: null,
  })
  await scrollBottom()

  sending.value = true
  try {
    const { data } = await api.post<ChatMessage>(`/api/chat/conversations/${convId}/messages/`, { content: text })
    // Replace optimistic message (best-effort)
    messages.value[messages.value.length - 1] = data
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '发送失败')
  } finally {
    sending.value = false
    await scrollBottom()
  }
}

async function switchConversation(c: Conversation) {
  activeConvId.value = c.id
  localStorage.setItem('bs001_consult_conv_id', String(c.id))
  await loadMessages(c.id)
  startPolling()
}

async function transferToManual() {
  if (role.value !== 'student') return
  try {
    const { data } = await api.post<Conversation>('/api/chat/conversations/human/start/', {})
    localStorage.setItem('bs001_consult_conv_id', String(data.id))
    props.onNavigate?.('consult')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '转接失败')
  }
}

watch(
  () => props.mode,
  async () => {
    if (props.mode === 'ai_chat') {
      stopPolling()
      await initAi()
    } else {
      await initConsult()
    }
  },
  { immediate: true },
)

onMounted(() => {
  const cached = localStorage.getItem('bs001_consult_conv_id')
  if (!cached) localStorage.removeItem('bs001_consult_conv_id')
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<template>
  <div class="h-[calc(100vh-12rem)] flex bg-white rounded-2xl shadow-sm border overflow-hidden">
    <aside
      v-if="mode === 'consult' && role !== 'student'"
      class="w-80 border-r bg-slate-50/60 hidden md:flex flex-col"
    >
      <div class="p-4 border-b bg-white">
        <div class="font-bold text-slate-800">会话列表</div>
        <div class="text-xs text-slate-400 mt-1">点击进入对应学生的咨询会话</div>
      </div>

      <div v-if="convLoading" class="p-4 text-sm text-slate-400">加载中…</div>

      <div v-else class="flex-1 overflow-y-auto p-3 space-y-2">
        <button
          v-for="c in conversations"
          :key="c.id"
          class="w-full text-left p-3 rounded-xl border transition"
          :class="c.id === activeConvId ? 'border-indigo-200 bg-indigo-50/60' : 'border-slate-100 bg-white hover:bg-slate-50'"
          @click="switchConversation(c)"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <div class="text-sm font-bold text-slate-800 truncate">
                {{ c.student?.real_name || c.student?.username }}
              </div>
              <div class="text-[10px] text-slate-400 mt-1 truncate">
                {{ c.last_message?.content || '暂无消息' }}
              </div>
            </div>
            <div class="text-[10px] font-mono text-slate-400 flex-shrink-0">
              {{ fmtDateTime(c.updated_at).slice(5, 16) }}
            </div>
          </div>
        </button>

        <EmptyState v-if="!conversations.length" title="暂无会话" desc="学生发起咨询或你主动创建会话后将出现在这里。" icon="message-circle" />
      </div>
    </aside>

    <div class="flex-1 flex flex-col">
      <div class="p-4 bg-white border-b flex justify-between items-center">
        <div class="font-bold text-slate-800 flex items-center gap-2">
          <LucideIcon :name="mode === 'ai_chat' ? 'brain-circuit' : 'message-circle'" class="w-4 h-4 text-indigo-600" />
          {{ mode === 'ai_chat' ? 'AI 智能助理' : '人工咨询' }}
        </div>

        <div class="flex items-center gap-2">
          <ElTag
            v-if="mode === 'ai_chat' && role === 'student'"
            size="small"
            effect="light"
            :class="['border', riskPillClass(riskLevel)]"
          >
            {{ riskLabel(riskLevel) }}
          </ElTag>

          <ElButton v-if="mode === 'ai_chat' && role === 'student'" size="small" plain @click="transferToManual">
            转人工
          </ElButton>
        </div>
      </div>

      <div id="chat-box" class="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50">
        <div
          v-for="(msg, i) in messages"
          :key="msg.id || i"
          :class="['flex', isMine(msg) ? 'justify-end' : 'justify-start']"
        >
          <div
            :class="[
              'max-w-[80%] px-4 py-3 rounded-2xl text-sm shadow-sm',
              isMine(msg)
                ? 'bg-indigo-600 text-white rounded-br-none'
                : 'bg-white text-slate-700 rounded-bl-none border border-slate-200',
            ]"
          >
            <div class="whitespace-pre-wrap leading-relaxed">{{ msg.content }}</div>
            <div class="mt-2 text-[10px] opacity-60 flex justify-end gap-2">
              {{ fmtDateTime(msg.created_at).slice(11, 16) }}
              <span v-if="mode === 'consult' && isMine(msg)">
                {{ msg.read_at ? '已读' : '未读' }}
              </span>
            </div>
          </div>
        </div>

        <div
          v-if="mode === 'ai_chat' && showRiskPrompt && role === 'student'"
          class="p-4 rounded-2xl border border-rose-100 bg-rose-50 text-rose-700"
        >
          <div class="text-xs font-bold uppercase tracking-widest">高风险提示</div>
          <div class="mt-2 text-sm leading-relaxed">
            系统检测到高风险表述。建议立即转接人工咨询教师，并同步生成预警记录。
          </div>
          <div class="mt-3 flex gap-2">
            <ElButton type="danger" size="small" @click="transferToManual">立即转接</ElButton>
            <ElButton size="small" @click="showRiskPrompt = false">暂不需要</ElButton>
          </div>
        </div>

        <div
          v-if="mode === 'ai_chat' && recommendations.length && role === 'student'"
          class="p-4 rounded-2xl border border-slate-100 bg-white"
        >
          <div class="text-xs font-bold uppercase tracking-widest text-slate-400">推荐阅读</div>
          <div class="mt-3 space-y-2">
            <div
              v-for="r in recommendations"
              :key="r.id"
              class="p-3 rounded-xl border border-slate-100 bg-slate-50/60"
            >
              <div class="text-sm font-bold text-slate-800">{{ r.title }}</div>
              <div class="text-xs text-slate-500 mt-1">{{ r.summary }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="p-4 bg-white border-t flex gap-2">
        <ElInput
          v-model="inputMsg"
          :disabled="sending"
          :placeholder="mode === 'ai_chat' ? '描述你的情绪与困扰…' : '输入并发送给对方…'"
          @keyup.enter="mode === 'ai_chat' ? sendAiMsg() : sendHumanMsg()"
        />
        <ElButton type="primary" :loading="sending" @click="mode === 'ai_chat' ? sendAiMsg() : sendHumanMsg()">
          <LucideIcon name="send" class="w-4 h-4" />
        </ElButton>
      </div>
    </div>
  </div>
</template>
