<template>
  <n-modal
    v-model:show="showModal"
    preset="card"
    :style="{ width: isMobile ? '95%' : '600px', maxHeight: '80vh' }"
    :segmented="{ content: true }"
    @close="handleClose"
  >
    <template #header>
      <n-space justify="space-between" align="center" style="width: 100%">
        <span>{{ title }}</span>
        <n-button
          v-if="messages.length > 0"
          quaternary
          size="small"
          @click="handleReset"
        >
          🔄 新对话
        </n-button>
      </n-space>
    </template>
    <n-scrollbar ref="scrollbarRef" :style="{ maxHeight: isMobile ? '60vh' : '500px' }">
      <n-space vertical size="large">
        <!-- 对话历史 -->
        <n-space vertical size="medium">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['chat-message', msg.role]"
            :style="msg.role === 'user' ? userBubbleStyle : {}"
          >
            <div class="message-header">
              <n-text :depth="3" :style="msg.role === 'user' ? { fontSize: '12px', color: isDark ? 'rgba(255,255,255,0.75)' : undefined } : { fontSize: '12px' }">
                {{ msg.role === 'user' ? '我' : aiName }}
              </n-text>
            </div>
            <div class="message-content">
              <n-text :style="msg.role === 'user' && isDark ? { color: '#ffffff' } : {}">
                {{ msg.content }}
              </n-text>
            </div>
          </div>
        </n-space>

        <!-- 建议问题（仅当有建议且对话为空时显示） -->
        <n-space v-if="suggestions.length > 0 && messages.length === 0" vertical size="small">
          <n-text :depth="3" style="font-size: 13px">💡 你可以问我：</n-text>
          <n-space size="small" wrap>
            <n-tag
              v-for="(suggestion, index) in suggestions"
              :key="index"
              :bordered="false"
              type="info"
              size="small"
              style="cursor: pointer"
              @click="sendMessage(suggestion)"
            >
              {{ suggestion }}
            </n-tag>
          </n-space>
        </n-space>

        <!-- 加载状态 -->
        <n-space v-if="loading" justify="center">
          <n-spin size="small" />
          <n-text :depth="3">{{ aiName }}正在思考...</n-text>
        </n-space>
      </n-space>
    </n-scrollbar>

    <!-- 输入框 -->
    <template #footer>
      <n-space vertical size="small">
        <n-input
          v-model:value="inputMessage"
          type="textarea"
          :placeholder="`与${aiName}对话...`"
          :autosize="{ minRows: 2, maxRows: 4 }"
          :disabled="loading"
          @keydown.enter.prevent="handleEnterKey"
        />
        <n-space justify="space-between">
          <n-text v-if="!isMobile" :depth="3" style="font-size: 12px">
            提示：按 Ctrl+Enter 发送
          </n-text>
          <div v-else></div>
          <n-button
            type="primary"
            :loading="loading"
            :disabled="!inputMessage.trim()"
            @click="handleSend"
          >
            发送
          </n-button>
        </n-space>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import { useThemeStore } from '@/stores/theme'
import { useUserStore } from '@/stores/user'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface Props {
  show: boolean
  title?: string
  aiName?: string
  contextType?: string
  suggestions?: string[]
  onChat: (message: string, history: Message[]) => Promise<{ reply: string; suggestions?: string[] }>
}

const props = withDefaults(defineProps<Props>(), {
  title: 'AI 助手',
  aiName: 'AI 助手',
  contextType: 'general',
  suggestions: () => []
})

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
}>()

const message = useMessage()
const showModal = computed({
  get: () => props.show,
  set: (val) => emit('update:show', val)
})

const themeStore = useThemeStore()
const userStore = useUserStore()
const isDark = computed(() => themeStore.currentTheme === 'dark')
const userBubbleStyle = computed(() => {
  if (isDark.value) {
    return { backgroundColor: '#0d9668', color: '#ffffff' }
  }
  return {}
})

const isMobile = ref(window.innerWidth < 768)
const scrollbarRef = ref<any>(null)
const messages = ref<Message[]>([])
const inputMessage = ref('')
const loading = ref(false)
const currentSuggestions = ref<string[]>([...props.suggestions])

// localStorage 持久化 key
const storageKey = computed(() => {
  const userId = userStore.user?.id || 'anonymous'
  return `ai_chat_${userId}_${props.contextType}`
})

// 从 localStorage 加载历史消息
function loadMessages() {
  try {
    const saved = localStorage.getItem(storageKey.value)
    if (saved) {
      messages.value = JSON.parse(saved)
    }
  } catch {
    messages.value = []
  }
}

// 保存消息到 localStorage
function saveMessages() {
  try {
    // 最多保存最近 50 条消息
    const toSave = messages.value.slice(-50)
    localStorage.setItem(storageKey.value, JSON.stringify(toSave))
  } catch {
    // localStorage 满了则忽略
  }
}

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    scrollbarRef.value?.scrollTo({ top: 99999, behavior: 'smooth' })
  })
}

// 响应式监听窗口大小
window.addEventListener('resize', () => {
  isMobile.value = window.innerWidth < 768
})

// 监听对话框打开时加载历史
watch(() => props.show, (val) => {
  if (val) {
    loadMessages()
    scrollToBottom()
  }
})

// 监听建议变化
watch(() => props.suggestions, (newSuggestions) => {
  currentSuggestions.value = [...newSuggestions]
}, { immediate: true })

const suggestions = computed(() => currentSuggestions.value)

async function sendMessage(msg: string) {
  if (!msg.trim() || loading.value) return

  const userMessage = msg.trim()
  inputMessage.value = ''

  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: userMessage
  })
  saveMessages()
  scrollToBottom()

  loading.value = true

  try {
    // 传递历史消息（最多最近 10 轮对话作为上下文）
    const historyForAI = messages.value.slice(0, -1).slice(-20)
    const response = await props.onChat(userMessage, historyForAI)
    
    // 添加 AI 回复
    messages.value.push({
      role: 'assistant',
      content: response.reply
    })
    saveMessages()
    scrollToBottom()

    // 更新建议
    if (response.suggestions && response.suggestions.length > 0) {
      currentSuggestions.value = response.suggestions
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || 'AI 服务暂时不可用')
    // 移除用户消息（因为发送失败）
    messages.value.pop()
    saveMessages()
  } finally {
    loading.value = false
  }
}

function handleSend() {
  if (inputMessage.value.trim()) {
    sendMessage(inputMessage.value)
  }
}

function handleEnterKey(e: KeyboardEvent) {
  if (e.ctrlKey || e.metaKey) {
    handleSend()
  }
}

function handleReset() {
  messages.value = []
  inputMessage.value = ''
  currentSuggestions.value = [...props.suggestions]
  saveMessages()
}

function handleClose() {
  // 关闭时不清空，保留对话历史
  inputMessage.value = ''
}
</script>

<style scoped>
.chat-message {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
}

.chat-message.user {
  background-color: var(--n-color-target);
  margin-left: 40px;
}

.chat-message.assistant {
  background-color: var(--n-color-embedded);
  margin-right: 40px;
}

.message-header {
  margin-bottom: 6px;
}

.message-content {
  word-wrap: break-word;
  white-space: pre-wrap;
  line-height: 1.6;
}


</style>
