import axios from 'axios'
import type { AxiosInstance } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '/studio-api',
  timeout: 300000,
})

// 请求拦截: 自动带上 Studio token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('studio_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截: 401 → 清除 token (但不自动跳转, 由调用方处理)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('studio_token')
      // 仅在非 XHR 类请求或确实需要强制登录时才重定向
      // 大部分 401 由各组件自行处理 (显示提示而非崩溃跳转)
    }
    return Promise.reject(error)
  },
)

// ==================== 认证 ====================
export const studioAuthApi = {
  check: () => api.get('/auth/check'),
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  verifyMainToken: (token: string) =>
    api.post('/auth/verify-main-token', { token }),
  me: () => api.get('/auth/me'),
}

// ==================== 项目 ====================
export const projectApi = {
  list: (params?: any) => api.get('/projects', { params }),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (data: any) => api.post('/projects', data),
  update: (id: number, data: any) => api.patch(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`),
  listTypes: () => api.get('/projects/types/list'),
}

// ==================== 讨论 ====================
export const discussionApi = {
  getMessages: (projectId: number) => api.get(`/projects/${projectId}/messages`),
  uploadImage: (projectId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/projects/${projectId}/upload-image`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteMessage: (projectId: number, messageId: number) =>
    api.delete(`/projects/${projectId}/messages/${messageId}`),
  deleteMessageAndAfter: (projectId: number, messageId: number) =>
    api.delete(`/projects/${projectId}/messages/${messageId}/and-after`),
  // Plan 版本
  getPlanVersions: (projectId: number) => api.get(`/projects/${projectId}/plan-versions`),
  getPlanVersion: (projectId: number, version: number) =>
    api.get(`/projects/${projectId}/plan-versions/${version}`),
  // SSE 讨论 (特殊处理, 不用 axios)
  discussUrl: (projectId: number) => `/studio-api/projects/${projectId}/discuss`,
  finalizePlanUrl: (projectId: number) => `/studio-api/projects/${projectId}/finalize-plan`,
  // AI 禁言控制
  getAiMuteStatus: (projectId: number) => api.get(`/projects/${projectId}/ai-mute`),
  toggleAiMute: (projectId: number) => api.post(`/projects/${projectId}/ai-mute`),
  getStreamingStatus: (projectId: number) => api.get(`/projects/${projectId}/streaming-status`),
  // 切换模型时上下文检查
  checkContext: (projectId: number, model: string) => api.post(`/projects/${projectId}/context-check`, { model }),
  // 手动总结/清空上下文
  summarizeContext: (projectId: number) => api.post(`/projects/${projectId}/summarize-context`, null, { timeout: 60000 }),
  clearContext: (projectId: number) => api.delete(`/projects/${projectId}/clear-context`),
}

// ==================== 实施 ====================
export const implementationApi = {
  start: (projectId: number, data: any) => api.post(`/projects/${projectId}/implement`, data),
  getStatus: (projectId: number) => api.get(`/projects/${projectId}/implementation`),
  getDiff: (projectId: number) => api.get(`/projects/${projectId}/pr-diff`),
  approvePR: (projectId: number) => api.post(`/projects/${projectId}/pr/approve`),
  prepareReview: (projectId: number) => api.post(`/projects/${projectId}/prepare-review`),
  getWorkspaceInfo: (projectId: number) => api.get(`/projects/${projectId}/workspace-info`),
  startIteration: (projectId: number) => api.post(`/projects/${projectId}/start-iteration`),
}

// ==================== 部署 ====================
export const deploymentApi = {
  deploy: (projectId: number, data: any) => api.post(`/projects/${projectId}/deploy`, data),
  list: (projectId: number) => api.get(`/projects/${projectId}/deployments`),
  // WebSocket URL
  wsUrl: (projectId: number, deploymentId: number) => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${location.host}/studio-api/projects/${projectId}/deploy-ws/${deploymentId}`
  },
}

// ==================== 快照 ====================
export const snapshotApi = {
  list: (params?: any) => api.get('/snapshots', { params }),
  get: (id: number) => api.get(`/snapshots/${id}`),
  create: (data: any) => api.post('/snapshots', data),
  rollback: (id: number, data?: any) => api.post(`/snapshots/${id}/rollback`, data || {}),
}

// ==================== 模型 ====================
export const modelApi = {
  list: (params?: { category?: string; vision_only?: boolean; api_backend?: string; refresh?: boolean; custom_models?: boolean }) =>
    api.get('/models', { params }),
  get: (id: string) => api.get(`/models/${id}`),
  refresh: () => api.post('/models/refresh'),
  cacheStatus: () => api.get('/models/cache-status'),
  getAllCapabilities: () => api.get('/models/capabilities/all'),
  updateCapability: (modelId: string, data: { max_input_tokens?: number; max_output_tokens?: number }) =>
    api.patch(`/models/capabilities/${encodeURIComponent(modelId)}`, data),
  // 定价刷新
  refreshPricing: () => api.post('/models/pricing/refresh', null, { timeout: 30000 }),
  applyPricing: (scraped: Record<string, any>) => api.post('/models/pricing/apply', { scraped }),
  currentPricing: () => api.get('/models/pricing/current'),
  refreshTokenLimits: () => api.post('/models/token-limits/refresh', null, { timeout: 45000 }),
}

// ==================== 模型配置管理 ====================
export const modelConfigApi = {
  // 自定义模型 CRUD
  listModels: (params?: { api_backend?: string; search?: string; enabled_only?: boolean }) =>
    api.get('/model-config/models', { params }),
  createModel: (data: any) => api.post('/model-config/models', data),
  updateModel: (id: number, data: any) => api.put(`/model-config/models/${id}`, data),
  deleteModel: (id: number) => api.delete(`/model-config/models/${id}`),
  resetModels: () => api.post('/model-config/models/reset'),
  // 能力覆盖 CRUD
  listCapabilities: (params?: { search?: string }) =>
    api.get('/model-config/capabilities', { params }),
  upsertCapability: (modelName: string, data: any) =>
    api.put(`/model-config/capabilities/${encodeURIComponent(modelName)}`, data),
  deleteCapability: (modelName: string) =>
    api.delete(`/model-config/capabilities/${encodeURIComponent(modelName)}`),
  resetAllCapabilities: () => api.post('/model-config/capabilities/reset-all'),
  // 合并视图
  getMerged: (params?: { search?: string }) =>
    api.get('/model-config/merged', { params }),
}

// ==================== Copilot OAuth ====================
export const copilotAuthApi = {
  status: () => api.get('/copilot-auth/status'),
  startDeviceFlow: () => api.post('/copilot-auth/device-flow/start'),
  pollDeviceFlow: () => api.post('/copilot-auth/device-flow/poll'),
  logout: () => api.post('/copilot-auth/logout'),
  test: () => api.post('/copilot-auth/test'),
  usage: () => api.get('/copilot-auth/usage'),
}

// ==================== 系统 ====================
export const systemApi = {
  health: () => api.get('/health'),
  status: () => api.get('/system/status'),
}

// ==================== 端点探测 ====================
export const endpointProbeApi = {
  listEndpoints: () => api.get('/endpoint-probe/endpoints'),
  testAll: (timeout?: number) =>
    api.post('/endpoint-probe/test-all', null, { params: timeout ? { timeout } : {}, timeout: 120000 }),
  testOne: (endpointId: string, timeout?: number) =>
    api.post(`/endpoint-probe/test-one/${endpointId}`, null, { params: timeout ? { timeout } : {}, timeout: 60000 }),
}

// ==================== AI 服务提供商 ====================
export const providerApi = {
  list: () => api.get('/providers'),
  create: (data: any) => api.post('/providers', data),
  update: (slug: string, data: any) => api.patch(`/providers/${slug}`, data),
  delete: (slug: string) => api.delete(`/providers/${slug}`),
  test: (slug: string) => api.post(`/providers/${slug}/test`),
  fetchModels: (slug: string) => api.get(`/providers/${slug}/models`),
  seedReset: () => api.post('/providers/seed-reset'),
}

// ==================== 技能管理 ====================
export const skillApi = {
  list: (params?: { enabled_only?: boolean }) => api.get('/skills', { params }),
  get: (id: number) => api.get(`/skills/${id}`),
  create: (data: any) => api.post('/skills', data),
  update: (id: number, data: any) => api.put(`/skills/${id}`, data),
  delete: (id: number) => api.delete(`/skills/${id}`),
  duplicate: (id: number) => api.post(`/skills/${id}/duplicate`),
}

// ==================== AI 任务 ====================
export const tasksApi = {
  /** 获取项目当前活跃的 AI 任务 (向后兼容: 返回第一个) */
  getActiveTask: (projectId: number) => api.get(`/projects/${projectId}/active-task`),
  /** 获取项目所有活跃 AI 任务 (多任务并发) */
  getActiveTasks: (projectId: number) => api.get(`/projects/${projectId}/active-tasks`),
  /** 返回 per-task SSE 流 URL (用于 finalize 等单任务场景) */
  streamUrl: (taskId: number) => `/studio-api/tasks/${taskId}/stream`,
  /** 返回项目事件总线 SSE URL (多人实时同步) */
  projectEventsUrl: (projectId: number) => `/studio-api/projects/${projectId}/events`,
  /** 轻量级任务状态查询 */
  getStatus: (taskId: number) => api.get(`/tasks/${taskId}/status`),
  /** 取消正在运行的任务 */
  cancel: (taskId: number) => api.post(`/tasks/${taskId}/cancel`),
  /** 审批写命令执行 */
  approveCommand: (taskId: number, body: { approved: boolean; scope: string }) =>
    api.post(`/tasks/${taskId}/approve-command`, body),
}

export default api
