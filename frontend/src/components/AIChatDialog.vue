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
        <div style="position: relative">
          <n-input
            v-model:value="inputMessage"
            type="textarea"
            :placeholder="voiceRecording ? '正在录音...' : `与${aiName}对话...`"
            :autosize="{ minRows: 2, maxRows: 4 }"
            :disabled="loading || voiceRecording"
            @keydown.enter.prevent="handleEnterKey"
          />
          <!-- 语音转写状态 -->
          <div v-if="voiceTranscribing" class="voice-transcribing-hint">
            <n-spin size="small" />
            <span style="margin-left: 6px; font-size: 12px">语音识别中...</span>
          </div>
        </div>
        <n-space justify="space-between" align="center">
          <n-space align="center" :size="4">
            <n-text v-if="!isMobile && !voiceRecording" :depth="3" style="font-size: 12px">
              Ctrl+Enter 发送 · 长按🎤语音输入
            </n-text>
            <!-- 录音计时 -->
            <n-text v-if="voiceRecording" type="error" style="font-size: 12px; font-weight: 600">
              🔴 {{ voiceTimerText }}
            </n-text>
          </n-space>
          <n-space :size="8">
            <!-- 语音按钮：长按录音，松开发送 -->
            <button
              class="voice-hold-btn"
              :class="{ recording: voiceRecording }"
              :disabled="loading || voiceTranscribing"
              @mousedown.prevent="onVoiceBtnDown"
              @mouseup="onVoiceBtnUp"
              @mouseleave="onVoiceBtnUp"
              @touchstart.prevent="onVoiceBtnDown"
              @touchend.prevent="onVoiceBtnUp"
              @touchcancel="onVoiceBtnUp"
              @contextmenu.prevent
              :title="voiceRecording ? '松开结束录音' : '长按说话'"
            >
              {{ voiceRecording ? '⏹' : '🎤' }}
            </button>
            <n-button
              type="primary"
              :loading="loading"
              :disabled="!inputMessage.trim() || voiceRecording"
              @click="handleSend"
            >
              发送
            </n-button>
          </n-space>
        </n-space>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useThemeStore } from '@/stores/theme'
import { useUserStore } from '@/stores/user'
import { aiChatApi } from '@/api'

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

// 语音输入状态
const voiceRecording = ref(false)
const voiceTranscribing = ref(false)
const voiceTimer = ref(0)
const voiceTimerText = computed(() => {
  const m = Math.floor(voiceTimer.value / 60)
  const s = voiceTimer.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let voiceTimerInterval: ReturnType<typeof setInterval> | null = null

// localStorage 持久化 key
const storageKey = computed(() => {
  const userId = userStore.user?.id || 'anonymous'
  return `ai_chat_${userId}_${props.contextType}`
})

// 从 localStorage 加载历史消息
function loadMessages() {
  try {
    const saved = localStorage.getItem(storageKey.value)
    messages.value = saved ? JSON.parse(saved) : []
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

// 角色切换时重新加载对应角色的对话历史
watch(() => props.contextType, () => {
  loadMessages()
  scrollToBottom()
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
  // 停止录音（如果正在录音）
  if (voiceRecording.value) {
    stopVoiceRecording()
  }
}

// ========== 语音输入（长按录音，松开发送） ==========

function onVoiceBtnDown() {
  if (loading.value || voiceTranscribing.value) return
  startVoiceRecording()
}

function onVoiceBtnUp() {
  if (voiceRecording.value) {
    stopVoiceRecording()
  }
}

async function startVoiceRecording() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    message.error('当前浏览器不支持录音，请使用HTTPS访问或更换浏览器')
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : MediaRecorder.isTypeSupported('audio/mp4')
          ? 'audio/mp4'
          : ''

    mediaRecorder = mimeType
      ? new MediaRecorder(stream, { mimeType })
      : new MediaRecorder(stream)

    audioChunks = []
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data)
    }
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      if (audioChunks.length === 0) return
      const blob = new Blob(audioChunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
      await sendVoiceForTranscription(blob)
    }

    mediaRecorder.start(1000)
    voiceRecording.value = true
    voiceTimer.value = 0
    voiceTimerInterval = setInterval(() => { voiceTimer.value++ }, 1000)
  } catch (err: any) {
    console.error('Microphone access error:', err)
    if (err.name === 'NotAllowedError') {
      message.error('请允许使用麦克风权限')
    } else if (err.name === 'NotFoundError') {
      message.error('未检测到麦克风设备')
    } else {
      message.error('无法启动录音: ' + (err.message || '未知错误'))
    }
  }
}

function stopVoiceRecording() {
  if (voiceTimerInterval) {
    clearInterval(voiceTimerInterval)
    voiceTimerInterval = null
  }
  voiceRecording.value = false
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
}

async function sendVoiceForTranscription(blob: Blob) {
  voiceTranscribing.value = true
  try {
    const ext = blob.type.includes('mp4') ? 'mp4' : blob.type.includes('ogg') ? 'ogg' : 'webm'
    const formData = new FormData()
    formData.append('file', blob, `voice.${ext}`)

    const { data } = await aiChatApi.voiceToText(formData)

    if (data.text) {
      // 将转录文本追加到输入框
      inputMessage.value = inputMessage.value
        ? inputMessage.value + ' ' + data.text
        : data.text
      message.success('语音识别完成')
    } else {
      message.warning('未识别到语音内容，请重新录制')
    }
  } catch (err: any) {
    console.error('Voice-to-text error:', err)
    message.error(err.response?.data?.detail || '语音识别失败，请重试')
  } finally {
    voiceTranscribing.value = false
  }
}

onUnmounted(() => {
  if (voiceRecording.value) {
    stopVoiceRecording()
  }
})
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

.voice-transcribing-hint {
  position: absolute;
  bottom: 8px;
  left: 12px;
  display: flex;
  align-items: center;
  color: var(--n-text-color-3);
  pointer-events: none;
}

.voice-hold-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 2px solid var(--n-border-color);
  background: var(--n-color);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.2s;
  outline: none;
  -webkit-tap-highlight-color: transparent;
  -webkit-user-select: none;
  user-select: none;
  -webkit-touch-callout: none;
  touch-action: none;
}

.voice-hold-btn:active:not(:disabled) {
  transform: scale(0.9);
}

.voice-hold-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.voice-hold-btn.recording {
  border-color: #e74c3c;
  background: rgba(231, 76, 60, 0.1);
  animation: voice-btn-pulse 1.2s ease-in-out infinite;
}

@keyframes voice-btn-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.3); }
  50% { box-shadow: 0 0 0 8px rgba(231, 76, 60, 0); }
}
</style>
