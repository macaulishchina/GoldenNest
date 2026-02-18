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
  const isGuest = ref<boolean>(localStorage.getItem('isGuest') === 'true')
  
  const isLoggedIn = computed(() => !!token.value && !isGuest.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  
  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
    // 登录时清除游客状态
    isGuest.value = false
    localStorage.removeItem('isGuest')
  }
  
  function enterGuestMode() {
    isGuest.value = true
    localStorage.setItem('isGuest', 'true')
    token.value = null
    user.value = null
  }
  
  function exitGuestMode() {
    isGuest.value = false
    localStorage.removeItem('isGuest')
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
    isGuest.value = false
    localStorage.removeItem('token')
    localStorage.removeItem('isGuest')
  }
  
  // 初始化时获取用户信息
  if (token.value) {
    fetchUser()
  }
  
  return {
    token,
    user,
    isGuest,
    isLoggedIn,
    isAdmin,
    setToken,
    fetchUser,
    logout,
    enterGuestMode,
    exitGuestMode
  }
})