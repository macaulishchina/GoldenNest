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
  api.interceptors.response.use(
    (response) => {
      // 仅在用户开启了设置时处理
      if (!getShowAIModelInfo()) return response

      const fnName = response.headers['x-ai-function-name']
      const model = response.headers['x-ai-model']

      if (fnName && model) {
        toastRef.value?.show(fnName, model)
      }

      return response
    },
    // 不影响错误处理链
    (error) => Promise.reject(error)
  )
}
