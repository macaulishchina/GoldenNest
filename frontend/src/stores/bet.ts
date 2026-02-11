import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'
import { useUserStore } from '@/stores/user'

export const useBetStore = defineStore('bet', () => {
  const pendingCount = ref(0)
  const lastFetchTime = ref(0)
  const FETCH_INTERVAL = 5000 // 5秒防抖
  const POLL_INTERVAL = 30000 // 30秒轮询间隔
  let pollTimer: ReturnType<typeof setInterval> | null = null

  async function fetchPendingCount(force = false) {
    const now = Date.now()
    if (!force && now - lastFetchTime.value < FETCH_INTERVAL) {
      return
    }

    // 检查用户是否已登录且已加入家庭
    const userStore = useUserStore()
    if (!userStore.isLoggedIn || !userStore.user?.family_id) {
      pendingCount.value = 0
      return
    }

    try {
      const res = await api.get('/bet/my-pending/count')
      pendingCount.value = res.data?.count || 0
      lastFetchTime.value = now
    } catch (error) {
      console.error('获取待投票赌注数量失败:', error)
    }
  }

  // 立即刷新（忽略防抖限制）
  async function refreshNow() {
    await fetchPendingCount(true)
  }

  // 启动轮询
  function startPolling() {
    if (pollTimer) return
    
    pollTimer = setInterval(() => {
      fetchPendingCount()
    }, POLL_INTERVAL)
  }

  // 停止轮询
  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function resetCount() {
    pendingCount.value = 0
    lastFetchTime.value = 0
    stopPolling()
  }

  return {
    pendingCount,
    fetchPendingCount,
    refreshNow,
    startPolling,
    stopPolling,
    resetCount
  }
})
