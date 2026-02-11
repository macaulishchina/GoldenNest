<template>
  <n-modal
    v-model:show="showModal"
    preset="card"
    :title="title"
    :style="{ width: isMobile ? '95%' : '600px', maxHeight: '80vh' }"
    :segmented="{ content: true }"
    @close="handleClose"
  >
    <n-scrollbar :style="{ maxHeight: isMobile ? '60vh' : '500px' }">
      <n-space vertical size="large">
        <!-- 对话历史 -->
        <n-space vertical size="medium">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            :class="['chat-message', msg.role]"
          >
            <div class="message-header">
              <n-text :depth="3" style="font-size: 12px">
                {{ msg.role === 'user' ? '我' : aiName }}
              </n-text>
            </div>
            <div class="message-content">
              <n-text>{{ msg.content }}</n-text>
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
          <n-text :depth="3" style="font-size: 12px">
            提示：按 Ctrl+Enter 发送
          </n-text>
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
import { ref, computed, watch } from 'vue'
import { useMessage } from 'naive-ui'

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
  onChat: (message: string) => Promise<{ reply: string; suggestions?: string[] }>
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

const isMobile = ref(window.innerWidth < 768)
const messages = ref<Message[]>([])
const inputMessage = ref('')
const loading = ref(false)
const currentSuggestions = ref<string[]>([...props.suggestions])

// 响应式监听窗口大小
window.addEventListener('resize', () => {
  isMobile.value = window.innerWidth < 768
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

  loading.value = true

  try {
    const response = await props.onChat(userMessage)
    
    // 添加 AI 回复
    messages.value.push({
      role: 'assistant',
      content: response.reply
    })

    // 更新建议
    if (response.suggestions && response.suggestions.length > 0) {
      currentSuggestions.value = response.suggestions
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || 'AI 服务暂时不可用')
    // 移除用户消息（因为发送失败）
    messages.value.pop()
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

function handleClose() {
  // 清空对话历史
  messages.value = []
  inputMessage.value = ''
  currentSuggestions.value = [...props.suggestions]
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

/* 深色模式适配 */
html.dark .chat-message.user {
  background-color: rgba(99, 226, 183, 0.15);
}

html.dark .chat-message.assistant {
  background-color: rgba(255, 255, 255, 0.08);
}
</style>
