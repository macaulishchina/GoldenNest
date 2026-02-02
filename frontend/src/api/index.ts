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
  register: (data: { username: string; password: string; nickname: string }) => 
    api.post('/auth/register', data),
  getMe: () => api.get('/auth/me')
}

export const familyApi = {
  create: (data: { name: string; target_amount?: number }) => 
    api.post('/family/', data),
  join: (invite_code: string) => api.post(`/family/join/${invite_code}`),
  get: () => api.get('/family/'),
  getMembers: () => api.get('/family/members')
}

export const depositApi = {
  create: (data: { amount: number; deposit_date: string; note?: string }) => 
    api.post('/deposits/', data),
  list: () => api.get('/deposits/')
}

export const equityApi = {
  getSummary: () => api.get('/equity/summary')
}

export const investmentApi = {
  create: (data: {
    name: string
    amount: number
    expected_rate: number
    start_date: string
    note?: string
  }) => api.post('/investments/', data),
  list: () => api.get('/investments/'),
  registerReturn: (id: number, amount: number) => 
    api.post(`/investments/${id}/return`, { amount })
}

export const expenseApi = {
  create: (data: {
    amount: number
    purpose: string
    equity_deduction_ratio: number
  }) => api.post('/expenses/', data),
  list: () => api.get('/expenses/'),
  approve: (id: number, approved: boolean) => 
    api.post(`/expenses/${id}/approve`, { approved })
}

export const transactionApi = {
  list: () => api.get('/transactions/')
}