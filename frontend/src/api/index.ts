import axios from 'axios'
import { useUserStore } from '@/stores/user'

export const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
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
  getMe: () => api.get('/auth/me')
}

export const familyApi = {
  create: (data: { name: string; savings_target?: number; equity_rate?: number }) => 
    api.post('/family/create', data),
  join: (invite_code: string) => api.post('/family/join', { invite_code }),
  getMy: () => api.get('/family/my'),
  update: (data: { name?: string; savings_target?: number; equity_rate?: number }) =>
    api.put('/family/update', data),
  refreshInviteCode: () => api.post('/family/refresh-invite-code')
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
    expected_rate: number
    start_date: string
    end_date?: string
    note?: string
  }) => api.post('/investment/create', data),
  list: (params?: { time_range?: string }) => api.get('/investment/list', { params }),
  update: (id: number, data: {
    name?: string
    principal?: number
    expected_rate?: number
    end_date?: string
    is_active?: boolean
    note?: string
  }) => api.put(`/investment/${id}`, data),
  addIncome: (id: number, data: { amount: number; income_date: string; note?: string }) => 
    api.post(`/investment/${id}/income`, data),
  getSummary: () => api.get('/investment/summary')
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
  send: (data: { to_user_id: number; amount: number; message?: string }) =>
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
    principal: number
    expected_rate: number
    start_date: string
    end_date?: string
    note?: string
  }) => api.post('/approval/investment/create', data),
  
  // 理财产品更新申请
  updateInvestment: (data: {
    investment_id: number
    name?: string
    principal?: number
    expected_rate?: number
    end_date?: string
    is_active?: boolean
    note?: string
  }) => api.post('/approval/investment/update', data),
  
  // 理财收益登记申请
  createInvestmentIncome: (data: {
    investment_id: number
    amount: number
    income_date: string
    note?: string
  }) => api.post('/approval/investment/income', data),
  
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
  cancel: (id: number) => api.post(`/approval/${id}/cancel`)
}
