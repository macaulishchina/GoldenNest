import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { studioAuthApi } from '@/api'

interface StudioUser {
  username: string
  nickname: string
  source: 'admin' | 'main_project'
  main_user_id?: number | null
}

export const useAuthStore = defineStore('studioAuth', () => {
  const token = ref<string | null>(localStorage.getItem('studio_token'))
  const user = ref<StudioUser | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.source === 'admin')

  function setToken(newToken: string, userInfo: StudioUser) {
    token.value = newToken
    user.value = userInfo
    localStorage.setItem('studio_token', newToken)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('studio_token')
  }

  /**
   * 自动认证流程:
   * 1. 检查已有 studio token
   * 2. 尝试复用主项目 session (localStorage 'token')
   * 3. 都没有 → 需要登录
   */
  async function autoAuth(): Promise<boolean> {
    // 1. 已有 studio token → 验证
    if (token.value) {
      try {
        const { data } = await studioAuthApi.me()
        user.value = data
        return true
      } catch {
        // token 无效, 清除
        logout()
      }
    }

    // 2. 尝试主项目 session
    const mainToken = localStorage.getItem('token')
    if (mainToken) {
      try {
        const { data } = await studioAuthApi.verifyMainToken(mainToken)
        setToken(data.access_token, {
          username: data.username,
          nickname: data.nickname,
          source: data.source as 'admin' | 'main_project',
        })
        return true
      } catch {
        // 主项目 token 也无效
      }
    }

    // 3. 需要登录
    return false
  }

  /**
   * 管理员登录
   */
  async function adminLogin(username: string, password: string) {
    loading.value = true
    try {
      const { data } = await studioAuthApi.login(username, password)
      setToken(data.access_token, {
        username: data.username,
        nickname: data.nickname,
        source: data.source as 'admin' | 'main_project',
      })
      return true
    } finally {
      loading.value = false
    }
  }

  return {
    token, user, loading,
    isLoggedIn, isAdmin,
    setToken, logout, autoAuth, adminLogin,
  }
})
