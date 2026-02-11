import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

interface User {
  id: number
  username: string
  nickname: string
  email: string
  family_id: number | null
  avatar: string | null
  avatar_version: number
  phone: string | null
  gender: string | null
  birthday: string | null
  bio: string | null
  created_at: string
  role: string | null
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)
  
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  
  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }
  
  async function fetchUser() {
    if (!token.value) return
    
    try {
      const response = await authApi.getMe()
      user.value = response.data
    } catch (error) {
      console.error('Failed to fetch user:', error)
      logout()
    }
  }
  
  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }
  
  // 初始化时获取用户信息
  if (token.value) {
    fetchUser()
  }
  
  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    setToken,
    fetchUser,
    logout
  }
})