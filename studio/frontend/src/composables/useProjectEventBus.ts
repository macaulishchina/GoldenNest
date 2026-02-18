/**
 * 项目事件总线 SSE 订阅 — 多人实时同步
 * 管理: streamingTasks Map, myTaskIds Set, SSE 连接/重连, 事件分发
 */
import { ref, computed, type Ref } from 'vue'
import { tasksApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useStudioConfigStore } from '@/stores/studioConfig'
import { parseErrorMeta, formatErrorAsMessage } from './useChatUtils'

export interface StreamTaskState {
  taskId: number
  model: string
  senderName: string
  content: string
  thinking: string
  toolCalls: Array<{id: string; name: string; arguments: any; status: string; result?: string; duration_ms?: number}>
  segments: Array<{type: 'content' | 'tool'; text?: string; toolCall?: any}>
  tokenUsage: any
}

interface EventBusOptions {
  projectId: () => number
  messages: Ref<any[]>
  persistentContextInfo: Ref<any>
  lastTokenUsage: Ref<any>
  scrollToBottom: () => void
  refreshContextInfo: () => void
  sendMessage: (content?: string) => void
  onCommandApprovalRequest?: (taskId: number, command: string, toolCallId: string) => void
}

export function useProjectEventBus(options: EventBusOptions) {
  const authStore = useAuthStore()
  const studioConfig = useStudioConfigStore()

  const streamingTasks = ref(new Map<number, StreamTaskState>())
  const myTaskIds = ref(new Set<number>())

  let projectBusAbortController: AbortController | null = null
  let projectBusReconnectTimer: ReturnType<typeof setTimeout> | null = null
  let autoContinueCount = 0

  // 是否有任何活跃流 (包括外部 finalize)
  function anyStreamingWith(externalStreaming: Ref<boolean>) {
    return computed(() => streamingTasks.value.size > 0 || externalStreaming.value)
  }

  function subscribe() {
    unsubscribe()
    projectBusAbortController = new AbortController()

    const url = tasksApi.projectEventsUrl(options.projectId())
    const headers: Record<string, string> = {}
    if (authStore.token) headers['Authorization'] = `Bearer ${authStore.token}`

    fetch(url, { headers, signal: projectBusAbortController.signal })
      .then(response => processStream(response))
      .catch(err => {
        if (err.name !== 'AbortError') {
          projectBusReconnectTimer = setTimeout(subscribe, 3000)
        }
      })
  }

  function unsubscribe() {
    if (projectBusReconnectTimer) {
      clearTimeout(projectBusReconnectTimer)
      projectBusReconnectTimer = null
    }
    if (projectBusAbortController) {
      projectBusAbortController.abort()
      projectBusAbortController = null
    }
  }

  async function processStream(response: Response) {
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    if (!reader) return

    try {
      let eventCount = 0
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            handleEvent(event)
            eventCount++
            if (eventCount % 5 === 0) {
              await new Promise(r => setTimeout(r, 0))
              options.scrollToBottom()
            }
          } catch {}
        }
      }
    } catch (e: any) {
      if (e.name === 'AbortError') return
    }

    // 流正常结束 → 自动重连
    if (projectBusAbortController && !projectBusAbortController.signal.aborted) {
      projectBusReconnectTimer = setTimeout(subscribe, 1000)
    }
  }

  function handleEvent(event: any) {
    const type = event.type
    const taskId = event.task_id

    if (type === 'new_message') {
      const msg = event.message
      if (msg?.id && !options.messages.value.find((m: any) => m.id === msg.id)) {
        options.messages.value.push(msg)
        options.scrollToBottom()
      }
      return
    }

    if (type === 'message_deleted') {
      options.messages.value = options.messages.value.filter((m: any) => m.id !== event.message_id)
      return
    }

    if (type === 'heartbeat') return

    // 命令审批请求: 通知外部 (ChatPanel) 弹出审批对话框
    if (type === 'command_approval_request') {
      if (taskId && options.onCommandApprovalRequest) {
        options.onCommandApprovalRequest(taskId, event.command || '', event.tool_call_id || '')
      }
      return
    }

    if (type === 'task_started') {
      if (taskId && !streamingTasks.value.has(taskId)) {
        streamingTasks.value.set(taskId, {
          taskId,
          model: event.model || '',
          senderName: event.sender_name || '',
          content: '',
          thinking: '',
          toolCalls: [],
          segments: [],
          tokenUsage: null,
        })
        options.scrollToBottom()
      }
      return
    }

    if (!taskId) return

    let state = streamingTasks.value.get(taskId)
    if (!state) {
      state = {
        taskId,
        model: event.model || '',
        senderName: event.sender_name || '',
        content: '',
        thinking: '',
        toolCalls: [],
        segments: [],
        tokenUsage: null,
      }
      streamingTasks.value.set(taskId, state)
    }

    if (type === 'content') {
      const text = event.content || ''
      state.content += text
      const last = state.segments[state.segments.length - 1]
      if (last && last.type === 'content') {
        last.text = (last.text || '') + text
      } else {
        state.segments.push({ type: 'content', text })
      }
    } else if (type === 'thinking') {
      state.thinking += event.content || ''
    } else if (type === 'context') {
      options.persistentContextInfo.value = event.context
    } else if (type === 'tool_call_start') {
      const tc = event.tool_call || event
      const toolCall = { id: tc.id || '', name: tc.name || '', arguments: null as any, status: 'preparing' as const }
      state.toolCalls.push(toolCall)
      state.segments.push({ type: 'tool', toolCall })
    } else if (type === 'tool_call') {
      const tc = event.tool_call || event
      const tcId = tc.id || event.tool_call_id || ''
      const existing = state.toolCalls.find(t => t.id === tcId)
      if (existing) {
        existing.arguments = tc.arguments || event.arguments || ''
        existing.status = 'calling'
      } else {
        const toolCall = { id: tcId, name: tc.name || event.name || '', arguments: tc.arguments || event.arguments || '', status: 'calling' as const }
        state.toolCalls.push(toolCall)
        state.segments.push({ type: 'tool', toolCall })
      }
    } else if (type === 'tool_result') {
      const tc = state.toolCalls.find(t => t.id === event.tool_call_id)
      if (tc) {
        tc.status = 'done'
        tc.result = event.result
        tc.duration_ms = event.duration_ms
      }
    } else if (type === 'tool_error') {
      const tc = state.toolCalls.find(t => t.id === event.tool_call_id)
      if (tc) {
        tc.status = 'error'
        tc.result = event.error
      }
    } else if (type === 'usage') {
      state.tokenUsage = event.usage
      options.lastTokenUsage.value = event.usage
    } else if (type === 'truncated') {
      if (myTaskIds.value.has(taskId) && autoContinueCount < studioConfig.maxAutoContinues) {
        autoContinueCount++
        const count = autoContinueCount
        const max = studioConfig.maxAutoContinues
        setTimeout(() => {
          options.sendMessage(`请继续上面没说完的内容`)
        }, 500)
      }
    } else if (type === 'done') {
      autoContinueCount = 0
      const msgId = event.message_id || Date.now()
      if ((state.content || state.toolCalls.length) && !options.messages.value.find((m: any) => m.id === msgId)) {
        options.messages.value.push({
          id: msgId,
          role: 'assistant',
          sender_name: state.model,
          content: state.content || '',
          model_used: state.model,
          thinking_content: state.thinking || null,
          tool_calls: state.toolCalls.length ? [...state.toolCalls] : null,
          token_usage: state.tokenUsage || null,
          created_at: new Date().toISOString(),
        })
      }
      streamingTasks.value.delete(taskId)
      myTaskIds.value.delete(taskId)
      options.scrollToBottom()
      options.refreshContextInfo()
    } else if (type === 'error') {
      const errText = event.error || 'AI 服务错误'
      const errorMeta = parseErrorMeta(errText, event.error_meta)

      if (state.content) {
        options.messages.value.push({
          id: Date.now(),
          role: 'assistant',
          sender_name: state.model,
          content: state.content + '\n\n---\n' + formatErrorAsMessage(errText, errorMeta),
          model_used: state.model,
          thinking_content: state.thinking || null,
          tool_calls: state.toolCalls.length ? [...state.toolCalls] : null,
          created_at: new Date().toISOString(),
        })
      } else {
        options.messages.value.push({
          id: Date.now(),
          role: 'assistant',
          sender_name: state.model,
          content: formatErrorAsMessage(errText, errorMeta),
          model_used: state.model,
          thinking_content: state.thinking || null,
          tool_calls: state.toolCalls.length ? [...state.toolCalls] : null,
          created_at: new Date().toISOString(),
        })
      }
      if (errorMeta.max_context_tokens || errorMeta.rate_limit) {
        studioConfig.updateModelCapability(state.model, errorMeta)
      }
      streamingTasks.value.delete(taskId)
      myTaskIds.value.delete(taskId)
      options.scrollToBottom()
      options.refreshContextInfo()
    } else if (type === 'cancelled') {
      if (state.content) {
        options.messages.value.push({
          id: Date.now(),
          role: 'assistant',
          sender_name: state.model,
          content: state.content + '\n\n---\n*⏹ 已停止*',
          model_used: state.model,
          thinking_content: state.thinking || null,
          tool_calls: state.toolCalls.length ? [...state.toolCalls] : null,
          created_at: new Date().toISOString(),
        })
      }
      streamingTasks.value.delete(taskId)
      myTaskIds.value.delete(taskId)
      options.scrollToBottom()
    }
  }

  function cancelTask(taskId: number) {
    tasksApi.cancel(taskId).catch(() => {})
    const state = streamingTasks.value.get(taskId)
    if (state && state.content) {
      options.messages.value.push({
        id: Date.now(),
        role: 'assistant',
        sender_name: state.model,
        content: state.content + '\n\n---\n*⏹ 已手动停止*',
        model_used: state.model,
        thinking_content: state.thinking || null,
        tool_calls: state.toolCalls.length ? [...state.toolCalls] : null,
        created_at: new Date().toISOString(),
      })
    }
    streamingTasks.value.delete(taskId)
    myTaskIds.value.delete(taskId)
    options.scrollToBottom()
  }

  return {
    streamingTasks,
    myTaskIds,
    anyStreamingWith,
    subscribe,
    unsubscribe,
    cancelTask,
  }
}
