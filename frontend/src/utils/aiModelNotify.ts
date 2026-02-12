/**
 * AI 模型调用通知工具
 *
 * 在 axios 响应拦截器中检测 X-AI-* 响应头，
 * 当用户开启了「显示 AI 模型信息」时，触发一个优雅的短暂提示。
 */
import { type Ref } from 'vue'
import { api } from '@/api'

// localStorage key
const STORAGE_KEY = 'showAIModelInfo'

/** 读取用户设置 */
export function getShowAIModelInfo(): boolean {
  return localStorage.getItem(STORAGE_KEY) === 'true'
}

/** 保存用户设置 */
export function setShowAIModelInfo(val: boolean) {
  localStorage.setItem(STORAGE_KEY, val ? 'true' : 'false')
}

/** 注册 axios 响应拦截器（在 App.vue onMounted 中调用一次） */
export function setupAIModelInterceptor(
  toastRef: Ref<{ show: (fn: string, model: string) => void } | null>
) {
  console.log('[AI-Model-Notify] 拦截器已注册')

  api.interceptors.response.use(
    (response) => {
      // 始终检测并打印 AI 响应头（无论开关是否开启）
      // 后端对中文做了 URL-encode，前端需要 decode
      const _d = (v: string | undefined) => {
        if (!v) return v
        try { return decodeURIComponent(v) } catch { return v }
      }
      const fnName = _d(response.headers['x-ai-function-name'])
      const model = _d(response.headers['x-ai-model'])
      const fnKey = _d(response.headers['x-ai-function'])
      const source = _d(response.headers['x-ai-source'])

      if (fnName || model) {
        console.log(
          `[AI-Model-Notify] 🤖 AI调用 → 功能: ${fnName || '(无)'} | 模型: ${model || '(无)'} | key: ${fnKey || '-'} | 来源: ${source || '-'}`
        )
      }

      // 仅在用户开启了设置时显示 Toast
      const enabled = getShowAIModelInfo()
      if (!enabled) {
        if (fnName || model) {
          console.log('[AI-Model-Notify] Toast开关未开启，跳过显示（可在系统设置中开启）')
        }
        return response
      }

      if (fnName && model) {
        if (toastRef.value) {
          console.log(`[AI-Model-Notify] ✅ 触发Toast: ${fnName} · ${model}`)
          toastRef.value.show(fnName, model)
        } else {
          console.warn('[AI-Model-Notify] ⚠️ toastRef.value 为 null，无法显示Toast')
        }
      }

      return response
    },
    // 不影响错误处理链
    (error) => Promise.reject(error)
  )
}
