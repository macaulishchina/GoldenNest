import { defineStore } from 'pinia'
import { ref } from 'vue'
import { approvalApi } from '@/api'
import { useUserStore } from '@/stores/user'

export const useApprovalStore = defineStore('approval', () => {
  const pendingCount = ref(0)
  const lastFetchTime = ref(0)
  const FETCH_INTERVAL = 5000 // 5秒防抖

  async function fetchPendingCount() {
    const now = Date.now()
    if (now - lastFetchTime.value < FETCH_INTERVAL) {
      return
    }

    // 检查用户是否已登录且已加入家庭
    const userStore = useUserStore()
    if (!userStore.isLoggedIn || !userStore.user?.family_id) {
      pendingCount.value = 0
      return
    }

    try {
      const res = await approvalApi.getPending()
      pendingCount.value = Array.isArray(res.data) ? res.data.length : 0
      lastFetchTime.value = now
    } catch (error) {
      console.error('获取待审批数量失败:', error)
      // 出错时不更新计数，保持之前的值
    }
  }

  function resetCount() {
    pendingCount.value = 0
    lastFetchTime.value = 0
  }

  return {
    pendingCount,
    fetchPendingCount,
    resetCount
  }
})