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
  list: () => api.get('/deposit/list')
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
  list: () => api.get('/investment/list'),
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

export const expenseApi = {
  create: (data: {
    title: string
    amount: number
    reason: string
    deduction_ratios: Array<{ user_id: number; ratio: number }>
  }) => api.post('/expense/create', data),
  list: () => api.get('/expense/list'),
  approve: (id: number, is_approved: boolean, comment?: string) => 
    api.post(`/expense/${id}/approve`, { is_approved, comment })
}

export const transactionApi = {
  list: () => api.get('/transaction/list')
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
  getRecent: (limit = 10) => api.get(`/achievement/recent?limit=${limit}`)
}

// 股权赠与 API
export const giftApi = {
  // 发送股权赠与
  send: (data: { to_user_id: number; amount: number; message?: string }) =>
    api.post('/gift/send', data),
  // 获取赠与列表
  list: () => api.get('/gift/list'),
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
