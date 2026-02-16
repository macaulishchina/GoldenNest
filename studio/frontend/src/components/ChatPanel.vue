<template>
  <div style="display: flex; flex-direction: column; height: 100%; min-height: 400px">
    <!-- 消息列表 -->
    <div ref="messageListRef" style="flex: 1; overflow-y: auto; padding: 4px 0">
      <div v-for="msg in messages" :key="msg.id" style="margin-bottom: 6px">
        <!-- 系统消息 (上下文总结) -->
        <div v-if="msg.role === 'system'" style="display: flex; justify-content: center">
          <n-card size="small" style="max-width: 90%; background: #1a2a3e; border: 1px dashed #f0a020; border-radius: 6px; --n-padding-top: 4px; --n-padding-bottom: 4px">
            <n-collapse>
              <n-collapse-item name="summary">
                <template #header>
                  <n-space align="center" :size="4">
                    <span style="font-size: 14px">📝</span>
                    <n-text style="color: #f0a020; font-size: 11px; font-weight: 500">
                      上下文自动总结
                    </n-text>
                    <n-text depth="3" style="font-size: 10px">{{ formatTime(msg.created_at) }}</n-text>
                  </n-space>
                </template>
                <div class="thinking-block" v-html="renderMarkdown(msg.content)" />
              </n-collapse-item>
            </n-collapse>
          </n-card>
        </div>

        <!-- 用户/AI 消息 -->
        <div
          v-else
          :style="{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }"
          @mouseenter="hoveredMessageId = msg.id"
          @mouseleave="hoveredMessageId = null"
        >
          <div style="max-width: 85%; position: relative">
            <n-card
              size="small"
              :style="{
                background: msg.role === 'user' ? '#1a3a5c' : '#1a2a3e',
                borderLeft: msg.role === 'assistant' ? '2px solid #e94560' : 'none',
                borderRight: msg.role === 'user' ? '2px solid #0ea5e9' : 'none',
                '--n-padding-top': '6px',
                '--n-padding-bottom': '6px',
                '--n-padding-left': '10px',
                '--n-padding-right': '10px',
              }"
            >
            <template #header>
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 4px">
                <n-space align="center" :size="6" style="flex: 1; min-width: 0">
                  <n-text :style="{ color: msg.role === 'assistant' ? '#e94560' : getUserColor(msg.sender_name), fontSize: '12px' }">
                    {{ msg.sender_name || msg.role }}
                  </n-text>
                  <n-tag v-if="msg.model_used" size="tiny" :bordered="false" round>
                    {{ msg.model_used }}
                  </n-tag>
                  <n-text depth="3" style="font-size: 10px">
                    {{ formatTime(msg.created_at) }}
                  </n-text>
                </n-space>
                <!-- 操作按钮 (常驻显示在 header 右侧) -->
                <n-button-group size="tiny" class="msg-actions" :class="{ 'msg-actions-visible': hoveredMessageId === msg.id }">
                  <n-button quaternary @click.stop="copyMessage(msg)" title="复制">
                    <template #icon><span style="font-size: 11px">📋</span></template>
                  </n-button>
                  <n-button quaternary @click.stop="msg.role === 'user' ? retryMessage(msg) : regenerateMessage(msg)" :title="msg.role === 'user' ? '重新发送' : '重新生成'">
                    <template #icon><span style="font-size: 11px">🔄</span></template>
                  </n-button>
                </n-button-group>
              </div>
            </template>

            <!-- 图片附件 -->
            <n-space v-if="msg.attachments?.length" style="margin-bottom: 6px">
              <n-image
                v-for="(att, i) in msg.attachments.filter((a: any) => a.type === 'image')"
                :key="i"
                :src="att.url"
                width="180"
                style="border-radius: 6px"
              />
            </n-space>

            <!-- 思考过程 (已保存的消息) -->
            <n-collapse v-if="msg.thinking_content" style="margin-bottom: 6px">
              <n-collapse-item title="💭 思考过程" name="thinking">
                <div class="thinking-block" v-html="renderMarkdown(msg.thinking_content)" />
              </n-collapse-item>
            </n-collapse>

            <!-- 工具调用记录 (已保存的消息) -->
            <n-collapse v-if="msg.tool_calls?.length" style="margin-bottom: 6px">
              <n-collapse-item name="tools">
                <template #header>
                  <n-space align="center" :size="4">
                    <span>🔧</span>
                    <n-text style="font-size: 11px; color: #18a058">
                      工具调用 ×{{ msg.tool_calls.length }}
                    </n-text>
                  </n-space>
                </template>
                <div v-for="tc in msg.tool_calls" :key="tc.id" class="tool-call-item">
                  <div class="tool-call-header">
                    <span :class="tc.result?.startsWith('ERROR:') ? 'tool-icon-error' : 'tool-icon-ok'">
                      {{ tc.result?.startsWith('ERROR:') ? '❌' : '✅' }}
                    </span>
                    <n-text strong style="font-size: 12px; color: #e0e0e0">{{ toolDisplayName(tc.name) }}</n-text>
                    <n-text depth="3" style="font-size: 11px">({{ tc.duration_ms || 0 }}ms)</n-text>
                  </div>
                  <div v-if="tc.arguments" class="tool-call-args">
                    <code>{{ formatToolArgs(tc.name, tc.arguments) }}</code>
                  </div>
                  <n-collapse>
                    <n-collapse-item title="查看结果" name="result">
                      <div class="tool-result-content" v-html="renderMarkdown(tc.result || '(无结果)')" />
                    </n-collapse-item>
                  </n-collapse>
                </div>
              </n-collapse-item>
            </n-collapse>

            <!-- 消息内容 (Markdown) -->
            <div class="markdown-body" v-html="renderMarkdown(msg.content)" />

            <!-- 工具调用统计 -->
            <div v-if="msg.token_usage?.tool_rounds" style="margin-top: 4px; padding-top: 3px; border-top: 1px solid #333">
              <n-text depth="3" style="font-size: 10px; color: #63e2b7">
                🛠️ {{ msg.token_usage.tool_rounds }} 轮工具调用
              </n-text>
            </div>
          </n-card>
          </div>
        </div>
      </div>

      <!-- 上下文总结通知 -->
      <div v-if="summaryNotice" style="display: flex; justify-content: center; margin-bottom: 6px">
        <n-card size="small" style="max-width: 90%; background: #1a2a3e; border: 1px dashed #f0a020; border-radius: 6px">
          <n-collapse>
            <n-collapse-item name="summary">
              <template #header>
                <n-space align="center" :size="6">
                  <span style="font-size: 16px">📝</span>
                  <n-text style="color: #f0a020; font-size: 12px; font-weight: 500">
                    上下文已接近上限，自动总结了早期对话
                  </n-text>
                </n-space>
              </template>
              <div class="thinking-block" v-html="renderMarkdown(summaryNotice)" />
            </n-collapse-item>
          </n-collapse>
        </n-card>
      </div>

      <!-- AI 正在回复 -->
      <div v-if="streaming" style="display: flex; justify-content: flex-start; margin-bottom: 6px">
        <n-card size="small" style="max-width: 85%; background: #1a2a3e; border-left: 2px solid #e94560; --n-padding-top: 6px; --n-padding-bottom: 6px">
          <template #header>
            <n-space align="center" :size="6">
              <n-text style="color: #e94560; font-size: 12px">{{ selectedModel }}</n-text>
              <n-spin size="small" />
              <n-button size="tiny" type="error" ghost @click="stopStreaming" style="margin-left: 8px">
                ⏹ 停止
              </n-button>
            </n-space>
          </template>

          <!-- 思考过程 (折叠) -->
          <n-collapse v-if="streamThinking" :default-expanded-names="['thinking']" style="margin-bottom: 8px">
            <n-collapse-item title="💭 思考过程" name="thinking">
              <div class="thinking-block" v-html="renderMarkdown(streamThinking)" />
            </n-collapse-item>
          </n-collapse>

          <!-- 工具调用 (实时) -->
          <div v-if="streamToolCalls.length" style="margin-bottom: 8px">
            <n-collapse :default-expanded-names="['tools']">
              <n-collapse-item name="tools">
                <template #header>
                  <n-space align="center" :size="6">
                    <span>🔧</span>
                    <n-text style="font-size: 12px; color: #18a058">
                      工具调用 ×{{ streamToolCalls.length }}
                    </n-text>
                    <n-spin v-if="streamToolCalls.some(tc => tc.status === 'calling')" :size="12" />
                  </n-space>
                </template>
                <div v-for="tc in streamToolCalls" :key="tc.id" class="tool-call-item">
                  <div class="tool-call-header">
                    <span v-if="tc.status === 'calling'" class="tool-icon-pending">⏳</span>
                    <span v-else-if="tc.status === 'error'" class="tool-icon-error">❌</span>
                    <span v-else class="tool-icon-ok">✅</span>
                    <n-text strong style="font-size: 12px; color: #e0e0e0">{{ toolDisplayName(tc.name) }}</n-text>
                    <n-text v-if="tc.duration_ms" depth="3" style="font-size: 11px">({{ tc.duration_ms }}ms)</n-text>
                    <n-spin v-if="tc.status === 'calling'" :size="12" style="margin-left: 4px" />
                  </div>
                  <div v-if="tc.arguments" class="tool-call-args">
                    <code>{{ formatToolArgs(tc.name, tc.arguments) }}</code>
                  </div>
                  <n-collapse v-if="tc.result">
                    <n-collapse-item title="查看结果" name="result">
                      <div class="tool-result-content" v-html="renderMarkdown(tc.result)" />
                    </n-collapse-item>
                  </n-collapse>
                </div>
              </n-collapse-item>
            </n-collapse>
          </div>

          <div class="markdown-body" v-html="renderMarkdown(streamContent || '▍')" />

          <!-- Token 使用条 -->
          <div v-if="contextInfo" style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #333">
            <n-space align="center" :size="4">
              <n-text depth="3" style="font-size: 11px">
                上下文: {{ contextInfo.percentage }}%
                ({{ formatTokens(contextInfo.used) }}/{{ formatTokens(contextInfo.total) }})
              </n-text>
              <n-progress
                type="line"
                :percentage="contextInfo.percentage"
                :show-indicator="false"
                :height="4"
                style="width: 80px"
                :color="contextInfo.percentage > 80 ? '#e94560' : contextInfo.percentage > 50 ? '#f0a020' : '#18a058'"
              />
              <n-text v-if="contextInfo.messages?.dropped > 0" depth="3" style="font-size: 11px; color: #f0a020">
                ({{ contextInfo.messages.dropped }} 条旧消息已截断)
              </n-text>
            </n-space>
          </div>
        </n-card>
      </div>
    </div>

    <!-- 图片预览区 -->
    <div v-if="pendingImages.length" style="padding: 6px 8px; background: #16213e; border-radius: 6px; margin-bottom: 4px">
      <n-space :size="6">
        <div v-for="(img, i) in pendingImages" :key="i" style="position: relative">
          <n-image :src="img.preview" width="64" height="64" style="border-radius: 6px; object-fit: cover" />
          <n-button circle size="tiny" type="error" style="position: absolute; top: -4px; right: -4px" @click="pendingImages.splice(i, 1)">✕</n-button>
        </div>
      </n-space>
    </div>

    <!-- 隐藏的文件选择器 (绕过 n-upload 的 DOM 问题) -->
    <input ref="fileInputRef" type="file" accept="image/*" style="display: none" @change="onFileInputChange" />

    <!-- ========== 输入区 ========== -->
    <div class="input-area">
      <!-- 第 1 行: 工具栏 -->
      <div class="toolbar-row">
        <n-dropdown :options="sourceFilterOptions" @select="onSourceFilterChange" trigger="click" size="small">
          <n-button size="small" quaternary style="padding: 0 6px">
            {{ sourceFilterLabel }} <span style="font-size: 10px; margin-left: 2px; opacity: 0.6">▾</span>
          </n-button>
        </n-dropdown>
        <div class="model-select-group">
          <n-select
            v-model:value="selectedModel"
            :options="modelOptions"
            :render-label="renderModelLabel"
            size="small"
            style="width: 100%"
            filterable
            :consistent-menu-width="false"
            @update:value="handleModelChange"
          />
          <button class="model-refresh-btn" @click="refreshModels" :disabled="loadingModels" :title="loadingModels ? '刷新中...' : '刷新模型列表'">
            <span :class="{ 'spin-icon': loadingModels }">⟲</span>
          </button>
        </div>
        <n-button v-if="currentModelCaps.supports_vision" size="small" quaternary :disabled="streaming" @click="fileInputRef?.click()">📷 图片</n-button>
        <n-popover v-if="currentModelCaps.supports_tools" trigger="click" placement="bottom" style="max-width: 320px">
          <template #trigger>
            <n-button size="small" quaternary :type="toolPermissions.length ? 'info' : 'default'">🛠️ 工具</n-button>
          </template>
          <div style="padding: 4px 0">
            <n-text strong style="font-size: 13px">AI 工具权限</n-text>
            <n-text depth="3" style="font-size: 11px; display: block; margin: 4px 0 8px">
              开启后 AI 可查看项目源码（可在设置页配置工具轮次上限）
            </n-text>
            <n-checkbox-group v-model:value="toolPermissions" @update:value="saveToolPermissions">
              <n-space vertical :size="4">
                <n-checkbox value="read_source" label="📖 读取源码文件" />
                <n-checkbox value="read_config" label="📄 读取配置文件" />
                <n-checkbox value="search" label="🔍 搜索代码内容" />
                <n-checkbox value="tree" label="🌳 浏览目录结构" />
              </n-space>
            </n-checkbox-group>
          </div>
        </n-popover>
        <n-tag v-if="remoteStreaming" type="warning" size="small" :bordered="false" round>⏳ AI 回复中...</n-tag>
      </div>

      <!-- 第 2 行: 文本输入框 -->
      <n-input
        ref="inputRef"
        v-model:value="inputText"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 6 }"
        :placeholder="aiMuted ? '人工讨论模式 · 消息不触发 AI (Enter 发送)' : '描述你的需求... (Enter 发送, Shift+Enter 换行)'"
        :disabled="streaming"
        @keydown="handleKeydown"
        style="margin: 6px 0"
      />

      <!-- 第 3 行: 操作栏 -->
      <div class="action-bar">
        <div class="action-bar-item">
          <n-progress
            type="line"
            :percentage="displayContextInfo.percentage"
            :show-indicator="false"
            :height="3"
            style="width: 48px"
            :color="displayContextInfo.percentage > 80 ? '#e94560' : displayContextInfo.percentage > 50 ? '#f0a020' : '#18a058'"
          />
          <span class="action-bar-stat">
            {{ formatTokens(displayContextInfo.used) }}/{{ formatTokens(displayContextInfo.total) }} · {{ displayContextInfo.percentage }}%
          </span>
          <n-spin v-if="contextCompressing" :size="12" style="margin-left: 4px" />
        </div>
        <span class="action-bar-spring" />
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button size="small" :type="aiMuted ? 'error' : 'default'" quaternary :loading="muteLoading" @click="toggleAiMute">
              {{ aiMuted ? '🔇 AI已禁言' : '🔊 禁言AI' }}
            </n-button>
          </template>
          {{ aiMuted ? '解除禁言后，AI 会阅读所有新消息并回复' : '禁言后仅人工讨论，AI 不参与回复' }}
        </n-tooltip>
        <n-button size="small" type="warning" quaternary @click="handleFinalizePlan" :loading="finalizingPlan" :disabled="messages.length < 2 || streaming">
          📋 敲定
        </n-button>
        <n-button v-if="streaming" size="small" type="error" @click="stopStreaming">⏹ 停止</n-button>
        <n-button v-else size="small" type="primary" @click="sendMessage()" :disabled="!inputText.trim() && !pendingImages.length">发送</n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch, h } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { discussionApi, modelApi, projectApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useStudioConfigStore } from '@/stores/studioConfig'
import type { Project } from '@/stores/project'
import { marked } from 'marked'

const authStore = useAuthStore()
const studioConfig = useStudioConfigStore()

const props = defineProps<{ project: Project }>()
const emit = defineEmits(['plan-finalized'])
const message = useMessage()
const dialog = useDialog()

const messages = ref<any[]>([])
const inputText = ref('')
const streaming = ref(false)
const streamContent = ref('')
const streamThinking = ref('')
const streamToolCalls = ref<Array<{
  id: string
  name: string
  arguments: any
  status: 'calling' | 'done' | 'error'
  result?: string
  duration_ms?: number
}>>([])
const contextInfo = ref<any>(null)
const tokenUsage = ref<any>(null)
const summaryNotice = ref<string>('')
const finalizingPlan = ref(false)
const messageListRef = ref<HTMLElement>()
const inputRef = ref()
const fileInputRef = ref<HTMLInputElement>()
const models = ref<any[]>([])
const selectedModel = ref(props.project.discussion_model || 'gpt-4o')
const loadingModels = ref(false)
const modelSourceFilter = ref<'all' | 'models' | 'copilot' | 'custom'>('all')

// AbortController for canceling streams
const abortController = ref<AbortController | null>(null)

// Message hover state for action buttons
const hoveredMessageId = ref<number | null>(null)

// Last token usage for display
const lastTokenUsage = ref<any>(null)

// 上下文信息 (常驻显示, 不随 streaming 重置)
const persistentContextInfo = ref<any>(null)

// 当前选中模型的最大上下文 tokens
const selectedModelMaxTokens = computed(() => {
  const model = models.value.find((m: any) => m.id === selectedModel.value)
  if (!model) return 0
  return studioConfig.getEffectiveMaxInput(model.id, model.max_input_tokens || 0) || model.max_input_tokens || 0
})

// 始终显示的上下文信息: 分母跟随活跃模型
const displayContextInfo = computed(() => {
  const total = selectedModelMaxTokens.value
  if (persistentContextInfo.value) {
    // 有实际数据时, 使用实际 used 但 total 以当前模型为准
    const used = persistentContextInfo.value.used || 0
    const effectiveTotal = total || persistentContextInfo.value.total || 1
    const percentage = Math.min(100, Math.round(used * 100 / Math.max(effectiveTotal, 1)))
    return { used, total: effectiveTotal, percentage }
  }
  // 无数据时, 显示 0/模型上限
  return { used: 0, total: total || 0, percentage: 0 }
})

// AI 禁言状态
const aiMuted = ref(false)
const muteLoading = ref(false)

// 上下文压缩状态 (转圈圈特效)
const contextCompressing = ref(false)
let contextCheckVersion = 0  // 快速切换模型时取消旧请求

// 来源过滤 — 下拉菜单
const sourceFilterOptions = computed(() => {
  const base = [
    { label: '全部', key: 'all' },
    { label: 'GitHub (免费)', key: 'models' },
    { label: 'Copilot ☁️ (付费)', key: 'copilot' },
  ]
  if (studioConfig.customModelsEnabled) {
    base.push({ label: '补充模型', key: 'custom' })
  }
  return base
})
const sourceFilterLabel = computed(() => {
  if (modelSourceFilter.value === 'models') return 'GitHub'
  if (modelSourceFilter.value === 'copilot') return 'Copilot ☁️'
  if (modelSourceFilter.value === 'custom') return '补充模型'
  return '全部'
})
function onSourceFilterChange(key: string) {
  if (key === 'custom' && !studioConfig.customModelsEnabled) {
    modelSourceFilter.value = 'all'
    return
  }
  modelSourceFilter.value = key as any
}

// 当前选中模型的能力 (用于动态显示/隐藏按钮)
const currentModelCaps = computed(() => {
  const model = models.value.find((m: any) => m.id === selectedModel.value)
  if (!model) return { supports_vision: false, supports_tools: false }
  return { supports_vision: !!model.supports_vision, supports_tools: !!model.supports_tools }
})

// 工具权限 (默认关闭 — 每轮工具调用消耗额外 1 次 premium request)
const toolPermissions = ref<string[]>(
  props.project.tool_permissions || []
)

// 当前模型的工具轮次上限 (根据免费/付费配置)
const currentModelToolRounds = computed(() => {
  const model = models.value.find(m => m.id === selectedModel.value)
  if (!model) return studioConfig.freeToolRounds
  return studioConfig.getToolRounds(model)
})

async function saveToolPermissions(val: string[]) {
  try {
    await projectApi.update(props.project.id, { tool_permissions: val })
  } catch {
    message.error('保存工具权限失败')
  }
}

// 远程流式输出检测 (其他用户触发的 AI 流式)
const remoteStreaming = ref(false)
let streamingPollTimer: ReturnType<typeof setInterval> | null = null

// 待发送的图片
const pendingImages = ref<Array<{ file: File; preview: string; uploaded?: any }>>([])

// 用户颜色映射
const userColorMap: Record<string, string> = {}
const userColors = ['#0ea5e9', '#a855f7', '#22c55e', '#f59e0b', '#ec4899', '#06b6d4', '#84cc16']
let colorIndex = 0

function getUserColor(senderName: string): string {
  if (!senderName || senderName === 'assistant') return '#e94560'
  if (!userColorMap[senderName]) {
    userColorMap[senderName] = userColors[colorIndex % userColors.length]
    colorIndex++
  }
  return userColorMap[senderName]
}

// 模型选项，按 publisher 分组, Copilot API 模型排在后面, 应用配置过滤
const modelOptions = computed(() => {
  const byCategory = models.value.filter(m => m.category === 'discussion' || m.category === 'both')
  // 按来源过滤
  const sourceFiltered = modelSourceFilter.value === 'all'
    ? byCategory
    : modelSourceFilter.value === 'copilot'
      ? byCategory.filter(m => m.api_backend === 'copilot')
      : modelSourceFilter.value === 'custom'
        ? byCategory.filter(m => m.is_custom)
        : byCategory.filter(m => m.api_backend !== 'copilot')

  // 应用配置过滤 (免费模式 + 黑名单)
  const filtered = sourceFiltered.filter(m => studioConfig.isModelVisible(m))

  const modelsApi = filtered.filter(m => m.api_backend !== 'copilot')
  const copilotApi = filtered.filter(m => m.api_backend === 'copilot')

  const classifyFamily = (m: any): string => {
    const n = String(m.id || m.name || '').replace(/^copilot:/, '').toLowerCase()
    if (n.includes('claude') || n.includes('anthropic')) return 'Anthropic'
    if (n.includes('gpt') || n.startsWith('o1') || n.startsWith('o3') || n.startsWith('o4')) return 'OpenAI'
    if (n.includes('gemini') || n.includes('google')) return 'Google'
    if (n.includes('deepseek')) return 'DeepSeek'
    if (n.includes('mistral')) return 'Mistral AI'
    if (n.includes('meta')) return 'Meta'
    if (n.includes('microsoft')) return 'Microsoft'
    if (n.includes('cohere')) return 'Cohere'
    if (n.includes('xai')) return 'xAI'
    return m.publisher || '其他'
  }

  const buildGroups = (list: any[], suffix: string = '') => {
    const groups: Record<string, any[]> = {}
    for (const m of list) {
      const pub = classifyFamily(m) + suffix
      if (!groups[pub]) groups[pub] = []
      groups[pub].push(m)
    }
    return groups
  }

  const mapOpt = (m: any) => ({
    label: m.name, value: m.id,
    description: m.summary || m.description || '',
    supports_vision: m.supports_vision, supports_tools: m.supports_tools,
    is_reasoning: m.is_reasoning, api_backend: m.api_backend,
    pricing_tier: m.pricing_tier, premium_multiplier: m.premium_multiplier,
    is_deprecated: m.is_deprecated, pricing_note: m.pricing_note,
    max_input_tokens: studioConfig.getEffectiveMaxInput(m.id, m.max_input_tokens || 0),
    max_output_tokens: m.max_output_tokens || 0,
  })
  const options: any[] = []
  for (const [pub, items] of Object.entries(buildGroups(modelsApi))) {
    options.push({ type: 'group', label: pub, key: pub, children: items.map(mapOpt) })
  }
  if (copilotApi.length) {
    for (const [pub, items] of Object.entries(buildGroups(copilotApi, ' ☁️'))) {
      options.push({ type: 'group', label: pub, key: 'copilot-' + pub, children: items.map(mapOpt) })
    }
  }
  return options
})

// 自定义模型选项渲染 (能力图标 + 上下文窗口 + 定价标识)
function renderModelLabel(option: any, selected: boolean) {
  if (option.type === 'group') return option.label
  const caps: string[] = []
  if (option.is_reasoning) caps.push('🧠')
  if (option.supports_vision) caps.push('👁️')
  if (option.supports_tools) caps.push('🔧')
  const depStr = option.is_deprecated ? ' ⚠️' : ''
  const capStr = caps.length ? ` ${caps.join('')}` : ''
  const priceText = option.pricing_note || 'x0'
  const ctxText = option.max_input_tokens ? formatTokens(option.max_input_tokens) : ''
  const nameStyle = selected ? 'font-weight:600' : ''
  const priceStyle = selected
    ? 'color:#18a058;font-size:11px;flex-shrink:0;margin-left:8px;font-weight:600'
    : 'color:#888;font-size:11px;flex-shrink:0;margin-left:8px'
  return h('div', { style: 'display:flex;justify-content:space-between;align-items:center;width:100%' }, [
    h('span', { style: nameStyle }, [selected ? '● ' : '', option.label as string, capStr, depStr]),
    h('span', { style: priceStyle }, [
      ctxText ? h('span', { style: 'color:#666;margin-right:6px' }, ctxText) : null,
      priceText,
    ]),
  ])
}

async function refreshModels() {
  loadingModels.value = true
  try {
    await modelApi.refresh()
    const { data } = await modelApi.list({ category: 'discussion', custom_models: studioConfig.customModelsEnabled })
    models.value = data
    message.success(`已刷新，共 ${data.length} 个可用模型`)
  } catch (e: any) {
    message.error('刷新模型列表失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loadingModels.value = false
  }
}

function renderMarkdown(text: string) {
  if (!text) return ''
  try {
    return marked.parse(text, { async: false }) as string
  } catch {
    return text.replace(/\n/g, '<br>')
  }
}

function formatTime(d: string) {
  return new Date(d).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

function formatTokens(n: number): string {
  if (!n) return '0'
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(0)}K`
  return `${n}`
}

// ==================== 错误解析 ====================

function parseErrorMeta(errorText: string, backendMeta?: any): any {
  const meta: any = { ...(backendMeta || {}) }

  // 速率限制
  const rlMatch = errorText.match(/Rate limit.*?(\d+)\s*per\s*(\d+)s/i)
  if (rlMatch) {
    meta.error_type = meta.error_type || 'rate_limit'
    meta.rate_limit = `${rlMatch[1]} per ${rlMatch[2]}s`
    meta.rate_limit_count = parseInt(rlMatch[1])
    meta.rate_limit_seconds = parseInt(rlMatch[2])
  }
  const waitMatch = errorText.match(/wait\s+(\d+)\s*seconds?/i)
  if (waitMatch) {
    meta.wait_seconds = parseInt(waitMatch[1])
    meta.error_type = meta.error_type || 'rate_limit'
  }

  // 上下文超限
  const ctxMatch = errorText.match(/maximum context length.*?(\d{3,})/i)
  if (ctxMatch) {
    meta.error_type = meta.error_type || 'context_overflow'
    meta.max_context_tokens = parseInt(ctxMatch[1])
  }
  const maxSizeMatch = errorText.match(/Max size:\s*(\d+)\s*tokens/i)
  if (maxSizeMatch) {
    meta.error_type = meta.error_type || 'context_overflow'
    meta.max_context_tokens = parseInt(maxSizeMatch[1])
  }
  const requestedMatch = errorText.match(/requested\s+(\d+)\s*tokens/i)
  if (requestedMatch) {
    meta.requested_tokens = parseInt(requestedMatch[1])
  }

  // 生成摘要
  if (meta.error_type === 'rate_limit') {
    meta.summary = `🚦 速率限制 (${meta.rate_limit || ''}${meta.wait_seconds ? `, 等待 ${meta.wait_seconds}s` : ''})`
  } else if (meta.error_type === 'context_overflow') {
    meta.summary = `📏 上下文超限 (最大 ${formatTokens(meta.max_context_tokens || 0)})`
  } else if (meta.error_type === 'auth_error') {
    meta.summary = '🔒 认证错误，请检查授权状态'
  } else {
    meta.summary = '⚠️ AI 服务错误'
  }

  return meta
}

function formatErrorAsMessage(error: string, meta: any): string {
  const parts = ['**⚠️ AI 服务错误**\n']

  if (meta.error_type === 'rate_limit') {
    if (meta.rate_limit_count && meta.rate_limit_seconds) {
      parts.push(`> 🚦 **速率限制**: 每 ${meta.rate_limit_seconds}秒 最多 ${meta.rate_limit_count} 次请求`)
    }
    if (meta.wait_seconds) {
      parts.push(`> ⏱️ **等待**: ${meta.wait_seconds} 秒后可重试`)
    }
    parts.push('\n💡 *建议：稍后重新发送消息，或切换到其他模型*')
  } else if (meta.error_type === 'context_overflow') {
    const limit = meta.max_context_tokens
    if (limit) {
      parts.push(`> 📏 **上下文超限**: 模型最大 ${formatTokens(limit)} tokens`)
    }
    if (meta.requested_tokens) {
      parts.push(`> 📊 **实际请求**: ${formatTokens(meta.requested_tokens)} tokens`)
    }
    parts.push('\n💡 *建议：删除部分历史消息，或切换到上下文更大的模型*')
  } else if (meta.error_type === 'auth_error') {
    parts.push('> 🔒 **认证失败**: 请前往设置页面检查 Copilot 授权状态')
  } else {
    // 通用错误 — 显示前 300 字符
    const brief = error.length > 300 ? error.slice(0, 300) + '...' : error
    parts.push('```\n' + brief + '\n```')
  }

  return parts.join('\n')
}

// 工具显示名称映射
const toolNames: Record<string, string> = {
  read_file: '📖 读取文件',
  search_text: '🔍 搜索',
  list_directory: '📂 列目录',
  get_file_tree: '🌳 目录树',
}

function toolDisplayName(name: string): string {
  return toolNames[name] || name
}

function formatToolArgs(name: string, args: any): string {
  if (!args) return ''
  if (name === 'read_file') {
    let s = args.path || ''
    if (args.start_line) s += ` L${args.start_line}`
    if (args.end_line) s += `-${args.end_line}`
    return s
  }
  if (name === 'search_text') {
    let s = `"${args.query || ''}"`
    if (args.include_pattern) s += ` in ${args.include_pattern}`
    return s
  }
  if (name === 'list_directory' || name === 'get_file_tree') {
    return args.path || '.'
  }
  return JSON.stringify(args)
}

// 图片上传
// 图片上传 (通过隐藏 input[type=file] 触发)
async function onFileInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = '' // 重置以允许重复选择同一文件
  try {
    const preview = URL.createObjectURL(file)
    const { data } = await discussionApi.uploadImage(props.project.id, file)
    pendingImages.value.push({ file, preview, uploaded: data })
  } catch (e: any) {
    message.error(e.response?.data?.detail || '图片上传失败')
  }
}

async function handleImageUpload({ file }: any) {
  try {
    const preview = URL.createObjectURL(file.file)
    const { data } = await discussionApi.uploadImage(props.project.id, file.file)
    pendingImages.value.push({
      file: file.file,
      preview,
      uploaded: data,
    })
  } catch (e: any) {
    message.error(e.response?.data?.detail || '图片上传失败')
  }
}

// ==================== 停止生成 ====================

function stopStreaming() {
  abortController.value?.abort()
  // 保留已生成的部分内容
  if (streamContent.value) {
    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      sender_name: selectedModel.value,
      content: streamContent.value + '\n\n---\n*⏹ 已手动停止*',
      model_used: selectedModel.value,
      thinking_content: streamThinking.value || null,
      tool_calls: streamToolCalls.value.length ? [...streamToolCalls.value] : null,
      created_at: new Date().toISOString(),
    })
  }
  streaming.value = false
  streamContent.value = ''
  streamThinking.value = ''
  streamToolCalls.value = []
  abortController.value = null
  scrollToBottom()
}

// ==================== 消息操作 ====================

async function copyMessage(msg: any) {
  try {
    await navigator.clipboard.writeText(msg.content)
    message.success('已复制到剪贴板')
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = msg.content
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    message.success('已复制到剪贴板')
  }
}

function confirmDeleteMessage(msg: any) {
  dialog.warning({
    title: '确认删除',
    content: `删除这条${msg.role === 'user' ? '用户' : 'AI'}消息？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: () => doDeleteMessage(msg),
  })
}

async function doDeleteMessage(msg: any) {
  try {
    // 只对有真实 DB ID 的消息发起删除请求 (Date.now() 生成的 ID > 1e12)
    if (msg.id && msg.id < 1e12) {
      await discussionApi.deleteMessage(props.project.id, msg.id)
    }
    messages.value = messages.value.filter(m => m.id !== msg.id)
    message.success('已删除')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

async function retryMessage(msg: any) {
  const retryContent = msg.content
  const retryAttachments = msg.attachments || []
  try {
    // 只对有真实 DB ID 的消息发起删除请求 (Date.now() 生成的 ID > 1e12)
    if (msg.id && msg.id < 1e12) {
      await discussionApi.deleteMessageAndAfter(props.project.id, msg.id)
    }
    const idx = messages.value.findIndex(m => m.id === msg.id)
    if (idx >= 0) messages.value = messages.value.slice(0, idx)
    await sendMessage(retryContent, retryAttachments)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '重试失败')
  }
}

async function regenerateMessage(msg: any) {
  try {
    // 只对有真实 DB ID 的消息发起删除请求 (Date.now() 生成的 ID > 1e12)
    if (msg.id && msg.id < 1e12) {
      await discussionApi.deleteMessage(props.project.id, msg.id)
    }
    messages.value = messages.value.filter(m => m.id !== msg.id)

    streaming.value = true
    streamContent.value = ''
    streamThinking.value = ''
    streamToolCalls.value = []
    contextInfo.value = null
    tokenUsage.value = null
    summaryNotice.value = ''
    abortController.value = new AbortController()

    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }

    const response = await fetch(discussionApi.discussUrl(props.project.id), {
      method: 'POST',
      headers,
      body: JSON.stringify({ message: '', sender_name: 'user', regenerate: true, max_tool_rounds: currentModelToolRounds.value }),
      signal: abortController.value.signal,
    })

    await handleSSEResponse(response)
  } catch (e: any) {
    if (e.name !== 'AbortError') {
      message.error('重新生成失败: ' + (e.message || ''))
    }
  } finally {
    streaming.value = false
    streamContent.value = ''
    streamThinking.value = ''
    streamToolCalls.value = []
    abortController.value = null
    scrollToBottom()
  }
}

// ==================== SSE 响应处理 (共用) ====================

// 标记 handleSSEResponse 是否已将内容添加到 messages
let sseContentSaved = false

async function handleSSEResponse(response: Response) {
  const reader = response.body?.getReader()
  const decoder = new TextDecoder()
  if (!reader) throw new Error('No response body')

  let savedThinking = ''
  let savedToolCalls: any[] = []
  sseContentSaved = false
  streamToolCalls.value = []

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value, { stream: true })
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const data = JSON.parse(line.slice(6))
        if (data.type === 'content') {
          streamContent.value += data.content
          scrollToBottom()
        } else if (data.type === 'thinking') {
          streamThinking.value += data.content
          savedThinking += data.content
          scrollToBottom()
        } else if (data.type === 'context') {
          contextInfo.value = data.context
          persistentContextInfo.value = data.context  // 常驻保存
        } else if (data.type === 'summary') {
          summaryNotice.value = data.summary
          scrollToBottom()
        } else if (data.type === 'tool_call') {
          // backend sends: {type: 'tool_call', tool_call: {id, name, arguments}}
          const tc_data = data.tool_call || data
          streamToolCalls.value.push({
            id: tc_data.id || data.tool_call_id || '',
            name: tc_data.name || data.name || '',
            arguments: tc_data.arguments || data.arguments || '',
            status: 'calling' as const,
          })
          scrollToBottom()
        } else if (data.type === 'tool_result') {
          const tc = streamToolCalls.value.find(t => t.id === data.tool_call_id)
          if (tc) {
            tc.status = 'done'
            tc.result = data.result
            tc.duration_ms = data.duration_ms
          }
          savedToolCalls = [...streamToolCalls.value]
          scrollToBottom()
        } else if (data.type === 'tool_error') {
          const tc = streamToolCalls.value.find(t => t.id === data.tool_call_id)
          if (tc) {
            tc.status = 'error'
            tc.result = data.error
            tc.duration_ms = data.duration_ms
          }
          savedToolCalls = [...streamToolCalls.value]
          scrollToBottom()
        } else if (data.type === 'usage') {
          tokenUsage.value = data.usage
          lastTokenUsage.value = data.usage
        } else if (data.type === 'done') {
          if (streamContent.value) {
            messages.value.push({
              id: data.message_id || Date.now(),
              role: 'assistant',
              sender_name: selectedModel.value,
              content: streamContent.value,
              model_used: selectedModel.value,
              thinking_content: savedThinking || null,
              tool_calls: savedToolCalls.length ? savedToolCalls : null,
              token_usage: tokenUsage.value || null,
              created_at: new Date().toISOString(),
            })
            sseContentSaved = true
          }
        } else if (data.type === 'error') {
          const errorMeta = parseErrorMeta(data.error, data.error_meta)

          if (!streamContent.value && !sseContentSaved) {
            // 无内容生成 — 将错误作为聊天消息显示
            messages.value.push({
              id: Date.now(),
              role: 'assistant',
              sender_name: selectedModel.value,
              content: formatErrorAsMessage(data.error, errorMeta),
              model_used: selectedModel.value,
              thinking_content: savedThinking || null,
              tool_calls: savedToolCalls.length ? savedToolCalls : null,
              token_usage: tokenUsage.value || null,
              created_at: new Date().toISOString(),
            })
            sseContentSaved = true
            // 从错误中学习模型能力
            if (errorMeta.max_context_tokens || errorMeta.rate_limit) {
              studioConfig.updateModelCapability(selectedModel.value, errorMeta)
            }
          } else if (streamContent.value && !sseContentSaved) {
            // 有部分内容 — 保留已生成的部分并附加错误
            messages.value.push({
              id: Date.now(),
              role: 'assistant',
              sender_name: selectedModel.value,
              content: streamContent.value + '\n\n---\n' + formatErrorAsMessage(data.error, errorMeta),
              model_used: selectedModel.value,
              thinking_content: savedThinking || null,
              tool_calls: savedToolCalls.length ? savedToolCalls : null,
              token_usage: tokenUsage.value || null,
              created_at: new Date().toISOString(),
            })
            sseContentSaved = true
          }
          // 简短提示 (warning 不会自动消失)
          message.warning(errorMeta.summary || '⚠️ AI 服务错误', { duration: 10000 })
        }
      } catch {}
    }
  }

  // 流结束后, 如果有内容但未保存 (没收到 done 也没收到 error), 兜底保存
  if (streamContent.value && !sseContentSaved) {
    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      sender_name: selectedModel.value,
      content: streamContent.value,
      model_used: selectedModel.value,
      thinking_content: savedThinking || null,
      tool_calls: savedToolCalls.length ? savedToolCalls : null,
      token_usage: tokenUsage.value || null,
      created_at: new Date().toISOString(),
    })
    sseContentSaved = true
  }
}

// ==================== 发送消息 ====================

async function sendMessage(overrideContent?: string, overrideAttachments?: any[]) {
  const text = overrideContent ?? inputText.value.trim()
  const isOverride = overrideContent !== undefined

  if (!text && !pendingImages.value.length && !isOverride) return

  const attachments = isOverride
    ? (overrideAttachments || [])
    : pendingImages.value
        .filter(img => img.uploaded)
        .map(img => ({
          type: 'image',
          url: img.uploaded.url,
          base64: img.uploaded.base64,
          mime_type: img.uploaded.mime_type,
          name: img.file.name,
        }))

  // 使用认证用户的昵称作为发送者
  const senderName = authStore.user?.nickname || authStore.user?.username || 'user'

  if (!isOverride) {
    inputText.value = ''
    pendingImages.value = []
  }

  messages.value.push({
    id: Date.now(),
    role: 'user',
    sender_name: senderName,
    content: text,
    attachments,
    created_at: new Date().toISOString(),
  })
  scrollToBottom()

  streaming.value = true
  streamContent.value = ''
  streamThinking.value = ''
  streamToolCalls.value = []
  contextInfo.value = null
  tokenUsage.value = null
  summaryNotice.value = ''
  abortController.value = new AbortController()

  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }

    const response = await fetch(discussionApi.discussUrl(props.project.id), {
      method: 'POST',
      headers,
      body: JSON.stringify({ message: text, sender_name: senderName, attachments, max_tool_rounds: currentModelToolRounds.value }),
      signal: abortController.value.signal,
    })

    // 处理非流式响应 (AI 正在输出 / AI 禁言)
    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const result = await response.json()
      if (result.status === 'queued') {
        message.info('AI 正在输出中，你的消息已保存，稍后一并回复')
      } else if (result.status === 'muted') {
        message.info('AI 已禁言，消息已保存')
      }
      streaming.value = false
      streamContent.value = ''
      streamThinking.value = ''
      streamToolCalls.value = []
      abortController.value = null
      return
    }

    await handleSSEResponse(response)
  } catch (e: any) {
    if (e.name !== 'AbortError') {
      message.error('AI 通信异常: ' + (e.message || ''))
    }
  } finally {
    streaming.value = false
    streamContent.value = ''
    streamThinking.value = ''
    streamToolCalls.value = []
    abortController.value = null
    scrollToBottom()
  }
}

// 敲定方案
async function handleFinalizePlan() {
  finalizingPlan.value = true
  streaming.value = true
  streamContent.value = ''
  streamThinking.value = ''
  abortController.value = new AbortController()

  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }

    const response = await fetch(discussionApi.finalizePlanUrl(props.project.id), {
      method: 'POST',
      headers,
      signal: abortController.value.signal,
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    if (!reader) throw new Error('No response body')

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value, { stream: true })
      for (const line of text.split('\n')) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.type === 'content') {
            streamContent.value += data.content
            scrollToBottom()
          } else if (data.type === 'thinking') {
            streamThinking.value += data.content
            scrollToBottom()
          } else if (data.type === 'done') {
            message.success(`设计稿已生成 (v${data.plan_version})`)
            emit('plan-finalized')
          } else if (data.type === 'error') {
            message.error(data.error)
          }
        } catch {}
      }
    }

    // 保存 plan 消息到列表
    if (streamContent.value) {
      messages.value.push({
        id: Date.now(),
        role: 'assistant',
        sender_name: `Plan Generator (${selectedModel.value})`,
        content: streamContent.value,
        message_type: 'plan_final',
        created_at: new Date().toISOString(),
      })
    }
  } catch (e: any) {
    if (e.name !== 'AbortError') {
      message.error('Plan 生成异常: ' + (e.message || ''))
    }
  } finally {
    finalizingPlan.value = false
    streaming.value = false
    streamContent.value = ''
    streamThinking.value = ''
    abortController.value = null
    scrollToBottom()
  }
}

// ==================== AI 禁言控制 ====================

async function toggleAiMute() {
  muteLoading.value = true
  try {
    const { data } = await discussionApi.toggleAiMute(props.project.id)
    aiMuted.value = data.ai_muted
    if (data.ai_muted) {
      message.warning('AI 已禁言 · 仅人工讨论模式')
    } else {
      message.success('AI 已解除禁言 · 发送消息将触发 AI 回复')
    }
  } catch (e: any) {
    if (e.response?.status === 401) {
      message.error('Token 已过期，请刷新页面重新登录')
    } else {
      message.error(e.response?.data?.detail || '操作失败')
    }
  } finally {
    muteLoading.value = false
  }
}

// 轮询远程流式输出状态 (检测其他用户是否在使用 AI)
function startStreamingPoll() {
  stopStreamingPoll() // 确保不重复启动
  streamingPollTimer = setInterval(async () => {
    if (streaming.value) return // 自己正在流式输出, 不需要轮询
    try {
      const { data } = await discussionApi.getStreamingStatus(props.project.id)
      const wasStreaming = remoteStreaming.value
      remoteStreaming.value = data.streaming
      // 远程流式结束时刷新消息列表 (可能有新 AI 回复)
      if (wasStreaming && !data.streaming) {
        const { data: msgs } = await discussionApi.getMessages(props.project.id)
        messages.value = msgs
        scrollToBottom()
      }
    } catch {}
  }, 5000)
}

function stopStreamingPoll() {
  if (streamingPollTimer) {
    clearInterval(streamingPollTimer)
    streamingPollTimer = null
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
    e.preventDefault()
    sendMessage()
  }
}

async function handleModelChange(val: string) {
  try {
    await projectApi.update(props.project.id, { discussion_model: val })
  } catch {}

  // 切换模型后检查上下文使用情况
  const myVersion = ++contextCheckVersion
  contextCompressing.value = true
  try {
    const { data } = await discussionApi.checkContext(props.project.id, val)
    // 快速切换时忽略过期结果
    if (myVersion !== contextCheckVersion) return
    if (data.context) {
      persistentContextInfo.value = data.context
    }
    if (data.summarized && data.summary_text) {
      message.info('上下文已自动压缩以适应新模型窗口')
    }
  } catch {} finally {
    if (myVersion === contextCheckVersion) {
      contextCompressing.value = false
    }
  }
}

onMounted(async () => {
  // 加载消息历史
  try {
    const { data } = await discussionApi.getMessages(props.project.id)
    messages.value = data
    scrollToBottom()
  } catch {}

  // 加载 AI 禁言状态
  try {
    const { data } = await discussionApi.getAiMuteStatus(props.project.id)
    aiMuted.value = data.ai_muted
  } catch {}

  // 加载模型列表 (使用后端缓存，不阻塞页面; 手动点击刷新按钮强制刷新)
  modelApi.list({ category: 'discussion', custom_models: studioConfig.customModelsEnabled }).then(({ data }) => {
    models.value = data
    if (data.length && !data.find((m: any) => m.id === selectedModel.value)) {
      selectedModel.value = data[0].id
    }
    // 模型加载完成后，获取当前模型的上下文使用率
    discussionApi.checkContext(props.project.id, selectedModel.value).then(({ data: ctx }) => {
      if (ctx.context) persistentContextInfo.value = ctx.context
    }).catch(() => {})
  }).catch(() => {})

  // 启动远程流式输出轮询
  startStreamingPoll()
})

onUnmounted(() => {
  stopStreamingPoll()
})
</script>

<style>
.markdown-body {
  color: #e0e0e0;
  line-height: 1.5;
  font-size: 13px;
}
.markdown-body pre {
  background: #0d1b2a;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}
.markdown-body code {
  background: #0d1b2a;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}
.markdown-body pre code {
  background: none;
  padding: 0;
}
.markdown-body p { margin: 0.4em 0; }
.markdown-body h1, .markdown-body h2, .markdown-body h3 { color: #e94560; margin: 0.6em 0 0.3em; }
.markdown-body ul, .markdown-body ol { padding-left: 1.5em; }
.markdown-body blockquote {
  border-left: 3px solid #e94560;
  margin: 0.4em 0;
  padding: 0.3em 0.8em;
  background: rgba(233, 69, 96, 0.1);
}
.markdown-body table { border-collapse: collapse; width: 100%; }
.markdown-body th, .markdown-body td { border: 1px solid #333; padding: 4px 10px; }
.markdown-body th { background: #0d1b2a; }
.markdown-body img { max-width: 100%; border-radius: 6px; }
.thinking-block {
  color: #999;
  font-size: 12px;
  line-height: 1.4;
  font-style: italic;
  border-left: 2px solid #555;
  padding-left: 8px;
  margin: 3px 0;
}
.thinking-block p { margin: 0.2em 0; }

/* 消息操作按钮 (header 内联, 默认半透明) */
.msg-actions {
  opacity: 0.2;
  transition: opacity 0.15s ease;
  flex-shrink: 0;
}
.msg-actions:hover, .msg-actions-visible {
  opacity: 0.8;
}
.msg-actions .n-button {
  padding: 0 3px !important;
}

/* Tool call visualization */
.tool-calls-section {
  margin: 4px 0;
}
.tool-call-item {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 5px;
  padding: 4px 8px;
  margin: 3px 0;
  font-size: 11px;
}
.tool-call-header {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
  color: #ccc;
}
.tool-call-args {
  color: #888;
  font-size: 10px;
  margin-left: 20px;
  margin-top: 1px;
  font-family: 'Fira Code', 'Cascadia Code', monospace;
  word-break: break-all;
}
.tool-result-content {
  color: #999;
  font-size: 10px;
  margin-top: 3px;
  max-height: 160px;
  overflow-y: auto;
  white-space: pre-wrap;
  font-family: 'Fira Code', 'Cascadia Code', monospace;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  padding: 4px 6px;
}
.tool-icon-ok { color: #63e2b7; }
.tool-icon-error { color: #e88080; }
.tool-icon-pending { color: #f2c97d; }

/* ============ 输入区布局 ============ */
.input-area {
  background: #16213e;
  border-radius: 10px;
  padding: 8px 10px;
  flex-shrink: 0;
}

/* 第 1 行工具栏: flexbox + nowrap + 模型选择器自动缩小 */
.toolbar-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
}
.toolbar-row > * {
  flex-shrink: 0;
}
/* 模型选择器适应内容宽度，空间不足时可缩小 */
.model-select-group {
  display: flex;
  align-items: center;
  flex: 0 1 auto;
  min-width: 100px;
  overflow: hidden;
}
.model-select-group .n-select {
  min-width: 0;
}
.model-select-group .n-base-selection {
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}
.model-refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 28px;
  border: 1px solid rgba(255,255,255,0.15);
  border-left: none;
  border-radius: 0 4px 4px 0;
  background: rgba(255,255,255,0.04);
  color: #aaa;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.model-refresh-btn:hover:not(:disabled) {
  background: rgba(255,255,255,0.1);
  color: #e0e0e0;
}
.model-refresh-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 第 3 行操作栏 */
.action-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.action-bar-item {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.action-bar-stat {
  font-size: 10px;
  color: rgba(255,255,255,0.35);
  white-space: nowrap;
  flex-shrink: 0;
}
.action-bar-spring {
  flex: 1;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.spin-icon {
  display: inline-block;
  animation: spin 0.8s linear infinite;
}
</style>
