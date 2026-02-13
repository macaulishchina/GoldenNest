import axios from 'axios'
import { useUserStore } from '@/stores/user'

export const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API 接口
export const authApi = {
  login: (username: string, password: string) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },
  register: (data: { username: string; email: string; password: string; nickname?: string }) => 
    api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  updateProfile: (data: { nickname?: string; email?: string; phone?: string; gender?: string; birthday?: string; bio?: string }) =>
    api.put('/auth/profile', data),
  changePassword: (data: { old_password: string; new_password: string }) =>
    api.put('/auth/password', data)
}

export const familyApi = {
  create: (data: { name: string; savings_target?: number; equity_rate?: number }) => 
    api.post('/family/create', data),
  join: (invite_code: string) => api.post('/family/join', { invite_code }),
  getMy: () => api.get('/family/my'),
  update: (data: { name?: string; savings_target?: number; equity_rate?: number }) =>
    api.put('/family/update', data),
  refreshInviteCode: () => api.post('/family/refresh-invite-code'),
  
  // 通知配置
  getNotificationConfig: () => api.get('/family/notification/config'),
  updateNotificationConfig: (data: { notification_enabled?: boolean; wechat_webhook_url?: string; external_base_url?: string }) =>
    api.put('/family/notification/config', data),
  testNotification: (webhook_url?: string) => 
    api.post('/family/notification/test', { webhook_url }),
  deleteWebhook: () => api.delete('/family/notification/webhook')
}

export const depositApi = {
  create: (data: { amount: number; deposit_date: string; note?: string }) => 
    api.post('/deposit/create', data),
  list: (params?: { time_range?: string }) => api.get('/deposit/list', { params }),
  my: (params?: { time_range?: string }) => api.get('/deposit/my', { params })
}

export const equityApi = {
  getSummary: () => api.get('/equity/summary')
}

export const investmentApi = {
  create: (data: {
    name: string
    investment_type: 'fund' | 'stock' | 'bond' | 'deposit' | 'other'
    principal: number
    start_date: string
    end_date?: string
    note?: string
  }) => api.post('/investment/create', data),
  list: (params?: { time_range?: string }) => api.get('/investment/list', { params }),
  update: (id: number, data: {
    name?: string
    principal?: number
    end_date?: string
    is_active?: boolean
    note?: string
  }) => api.put(`/investment/${id}`, data),
  updateInfo: (id: number, data: {
    name?: string
    end_date?: string
    note?: string
  }) => api.patch(`/investment/${id}/info`, data),
  addIncome: (id: number, data: { amount: number; income_date: string; note?: string }) => 
    api.post(`/investment/${id}/income`, data),
  getSummary: () => api.get('/investment/summary'),
  // 获取投资的操作历史
  getHistory: (id: number) => api.get(`/investment/${id}/history`)
}

// expenseApi 已废弃，支出申请请使用 approvalApi.createExpense()

export const transactionApi = {
  list: (params?: { time_range?: string }) => api.get('/transaction/list', { params })
}

// 成就系统 API
export const achievementApi = {
  // 获取所有成就定义（带解锁状态）
  getDefinitions: (includeHidden = false) => 
    api.get(`/achievement/definitions?include_hidden=${includeHidden}`),
  // 获取我的已解锁成就
  getMy: () => api.get('/achievement/my'),
  // 获取成就进度统计
  getProgress: () => api.get('/achievement/progress'),
  // 手动触发成就检查
  check: () => api.post('/achievement/check'),
  // 获取家庭成员最近解锁
  getRecent: (limit = 10) => api.get(`/achievement/recent?limit=${limit}`),
  // 获取未展示的成就（用于轮询/路由切换时检查）
  getUnshown: () => api.get('/achievement/unshown')
}

// 股权赠与 API
export const giftApi = {
  // 发送股权赠与
  send: (data: { to_user_id: number; amount: number; gift_money?: number; message?: string }) =>
    api.post('/gift/send', data),
  // 获取赠与列表
  list: (params?: { time_range?: string }) => api.get('/gift/list', { params }),
  // 响应赠与（接受/拒绝）
  respond: (giftId: number, accept: boolean) =>
    api.post(`/gift/${giftId}/respond`, { accept }),
  // 取消赠与
  cancel: (giftId: number) => api.delete(`/gift/${giftId}`),
  // 获取赠与统计
  getStats: () => api.get('/gift/stats'),
  // 获取待处理数量
  getPendingCount: () => api.get('/gift/pending-count')
}

// 通用审批 API
export const approvalApi = {
  // 资金注入申请
  createDeposit: (data: { amount: number; deposit_date: string; note?: string }) =>
    api.post('/approval/deposit', data),
  
  // 理财产品创建申请
  createInvestment: (data: {
    name: string
    investment_type: string
    principal?: number
    currency?: string
    foreign_amount?: number
    start_date: string
    end_date?: string
    deduct_from_cash?: boolean
    note?: string
  }) => api.post('/approval/investment/create', data),
  
  // 理财产品更新申请
  updateInvestment: (data: {
    investment_id: number
    name?: string
    principal?: number
    end_date?: string
    is_active?: boolean
    note?: string
  }) => api.post('/approval/investment/update', data),
  
  // 理财收益登记申请（支持新旧两种模式）
  createInvestmentIncome: (data: {
    investment_id: number
    amount?: number  // 老模式：直接记录收益金额
    current_value?: number  // 新模式：记录当前总价值，系统自动计算收益
    income_date: string
    note?: string
  }) => api.post('/approval/investment/income', data),
  
  // 投资增持申请
  increaseInvestment: (data: {
    investment_id: number
    amount?: number
    foreign_amount?: number
    operation_date: string
    note?: string
    deduct_from_cash?: boolean
  }) => api.post('/approval/investment/increase', data),
  
  // 投资减持申请
  decreaseInvestment: (data: {
    investment_id: number
    amount?: number
    foreign_amount?: number
    operation_date: string
    note?: string
  }) => api.post('/approval/investment/decrease', data),
  
  // 删除投资产品申请
  deleteInvestment: (data: {
    investment_id: number
    reason?: string
  }) => api.post('/approval/investment/delete', data),
  
  // 资产登记申请（统一入口）
  createAsset: (data: {
    user_id: number
    name: string
    asset_type: 'cash' | 'time_deposit' | 'fund' | 'stock' | 'bond' | 'other'
    currency: 'CNY' | 'USD' | 'HKD' | 'JPY' | 'EUR' | 'GBP' | 'AUD' | 'CAD' | 'SGD' | 'KRW'
    amount?: number  // CNY金额
    foreign_amount?: number  // 外币金额

    start_date: string
    end_date?: string
    bank_name?: string
    deduct_from_cash: boolean
    note?: string
  }) => api.post('/approval/asset/create', data),
  
  // 支出申请
  createExpense: (data: {
    title: string
    amount: number
    reason: string
    deduction_ratios: Array<{ user_id: number; ratio: number }>
  }) => api.post('/approval/expense', data),
  
  // 成员加入申请（通常由 join_family 接口自动创建）
  createMemberJoin: (data: { family_id: number }) =>
    api.post('/approval/member/join', data),
  
  // 成员剔除申请
  createMemberRemove: (data: { target_user_id: number; reason?: string }) =>
    api.post('/approval/member/remove', data),
  
  // 获取申请列表
  list: (params?: { request_type?: string; status?: string; time_range?: string }) =>
    api.get('/approval/list', { params }),
  
  // 获取待我审批的申请
  getPending: () => api.get('/approval/pending'),
  
  // 获取申请详情
  get: (id: number) => api.get(`/approval/${id}`),
  
  // 同意申请
  approve: (id: number) => api.post(`/approval/${id}/approve`),
  
  // 拒绝申请
  reject: (id: number, reason?: string) => 
    api.post(`/approval/${id}/reject`, { reason }),
  
  // 取消申请
  cancel: (id: number) => api.post(`/approval/${id}/cancel`),
  
  // 催促审核
  remind: (id: number) => api.post(`/approval/${id}/remind`),
  
  // 重试执行失败的申请
  retry: (id: number) => api.post(`/approval/${id}/retry`)
}

// 资产管理 API（统一入口）
export const assetApi = {
  // 获取活期现金余额
  getCashBalance: () => api.get('/asset/cash-balance'),
  
  // 获取资产汇总
  getSummary: () => api.get('/asset/summary'),
  
  // 获取资产列表
  list: (params?: { 
    asset_type?: string
    currency?: string
    user_id?: number
    is_active?: boolean
  }) => api.get('/asset/list', { params }),
  
  // 获取我的资产
  myAssets: (params?: { asset_type?: string; currency?: string }) => api.get('/asset/my-assets', { params }),
  
  // 获取实时汇率
  getExchangeRate: (currency: string) => api.get(`/asset/exchange-rate/${currency}`),
  
  // 解析资产凭证图片
  parseImage: (image: string) => api.post('/asset/parse-image', { image }, { timeout: 60000 }),
  
  // 更新资产非金额信息（直接生效，不需审批）
  updateInfo: (id: number, data: {
    name?: string
    end_date?: string
    bank_name?: string
    note?: string
  }) => api.patch(`/asset/${id}/info`, data)
}

// 投票 API
export const voteApi = {
  // 获取待投票数量（用于红点显示）
  getPendingCount: () => api.get('/vote/pending-count')
}

// AI 服务商配置 API
export const aiConfigApi = {
  // 获取服务商模板列表
  getTemplates: () => api.get('/ai-config/templates'),
  // 获取所有已配置的服务商
  listProviders: () => api.get('/ai-config/providers'),
  // 创建服务商
  createProvider: (data: { name: string; provider_type: string; api_key: string; base_url: string; default_model: string }) =>
    api.post('/ai-config/providers', data),
  // 更新服务商
  updateProvider: (id: number, data: { name?: string; api_key?: string; base_url?: string; default_model?: string; is_enabled?: boolean }) =>
    api.put(`/ai-config/providers/${id}`, data),
  // 删除服务商
  deleteProvider: (id: number) => api.delete(`/ai-config/providers/${id}`),
  // 激活服务商
  activateProvider: (id: number) => api.post(`/ai-config/providers/${id}/activate`),
  // 取消激活
  deactivateProvider: (id: number) => api.post(`/ai-config/providers/${id}/deactivate`),
  // 设置模型
  setModel: (id: number, model: string) => api.post(`/ai-config/providers/${id}/set-model`, { model }),
  // 获取服务商可用模型列表
  fetchModels: (id: number) => api.get(`/ai-config/providers/${id}/models`),
  // 获取 AI 服务状态
  getStatus: () => api.get('/ai-config/status'),
  // 获取功能注册表
  getFunctionRegistry: () => api.get('/ai-config/functions/registry'),
  // 获取所有功能配置状态
  getFunctionConfigs: () => api.get('/ai-config/functions/configs'),
  // 更新功能模型配置
  updateFunctionConfig: (functionKey: string, data: { provider_id?: number | null; model_name: string; is_enabled?: boolean }) =>
    api.put(`/ai-config/functions/${functionKey}/config`, data),
  // 重置功能配置（使用全局默认）
  resetFunctionConfig: (functionKey: string) => api.delete(`/ai-config/functions/${functionKey}/config`)
}

// AI Chat API - 通用 AI 对话助手
export const aiChatApi = {
  // 与 AI 助手对话
  chat: (data: { message: string; context_type?: string; history?: Array<{role: string; content: string}>; persona?: string }) => 
    api.post('/ai/chat', data),
  // 语音转文字
  voiceToText: (formData: FormData) =>
    api.post('/ai/chat/voice-to-text', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    }),
}

// Transaction AI API - 交易智能分析
export const transactionAiApi = {
  // AI 分析交易数据
  analyze: (params?: { time_range?: string }) =>
    api.post('/transaction/ai/analyze', null, { params }),
  // AI 智能分类交易
  categorize: (data: { description: string; amount: number }) =>
    api.post('/transaction/ai/categorize', data)
}

// Pet AI API - 宠物对话
export const petAiApi = {
  // 与宠物对话
  chat: (data: { message: string; history?: Array<{role: string; content: string}> }) =>
    api.post('/pet/chat', data)
}

// Todo AI API - 任务智能管理
export const todoAiApi = {
  // AI 任务建议
  suggest: (data: { context: string }) =>
    api.post('/todo/ai/suggest', data),
  // AI 任务优先级分析
  prioritize: (data: { task_ids?: number[] }) =>
    api.post('/todo/ai/prioritize', data)
}

// Investment AI API - 投资组合分析
export const investmentAiApi = {
  // AI 分析投资组合
  analyze: () =>
    api.post('/investment/ai/analyze')
}

// Announcement AI API - 公告内容助手
export const announcementAiApi = {
  // AI 生成公告草稿
  draft: (data: { topic: string; style?: string }) =>
    api.post('/announcements/ai/draft', data),
  // AI 改进公告内容
  improve: (data: { content: string; improve_type?: string }) =>
    api.post('/announcements/ai/improve', data)
}

// 站点配置 API - 图标 / PWA / 站点名称
export const siteConfigApi = {
  // 获取站点信息（公开）
  getInfo: () => api.get('/site-config/info'),
  // 获取站点设置（管理员）
  getSettings: () => api.get('/site-config/settings'),
  // 更新站点设置（管理员）
  updateSettings: (data: { site_name?: string; short_name?: string; theme_color?: string; bg_color?: string }) =>
    api.put('/site-config/settings', data),
  // 上传图标（管理员）
  uploadIcon: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/site-config/icon', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  // 删除图标（管理员）
  deleteIcon: () => api.delete('/site-config/icon'),
}
