<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <router-view />
          <!-- Steam 风格成就解锁弹窗 -->
          <AchievementToast />
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import type { GlobalThemeOverrides } from 'naive-ui'
import AchievementToast from '@/components/AchievementToast.vue'
import { fetchUnshownAchievements } from '@/utils/achievement'
import { useUserStore } from '@/stores/user'

// 成就轮询定时器
let achievementPollingTimer: ReturnType<typeof setInterval> | null = null
const POLLING_INTERVAL = 60000 // 60 秒轮询一次

// 启动成就轮询
const startAchievementPolling = () => {
  if (achievementPollingTimer) return
  
  achievementPollingTimer = setInterval(() => {
    const userStore = useUserStore()
    if (userStore.isLoggedIn) {
      fetchUnshownAchievements()
    }
  }, POLLING_INTERVAL)
}

// 停止成就轮询
const stopAchievementPolling = () => {
  if (achievementPollingTimer) {
    clearInterval(achievementPollingTimer)
    achievementPollingTimer = null
  }
}

onMounted(() => {
  startAchievementPolling()
})

onUnmounted(() => {
  stopAchievementPolling()
})

// 自定义主题 - 清新可爱风格
const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#10b981',
    primaryColorHover: '#34d399',
    primaryColorPressed: '#059669',
    primaryColorSuppl: '#6ee7b7',
    borderRadius: '12px',
    borderRadiusSmall: '8px'
  },
  Card: {
    borderRadius: '16px'
  },
  Button: {
    borderRadiusMedium: '10px'
  },
  Tag: {
    borderRadius: '8px'
  }
}
</script>

<style>
#app {
  min-height: 100vh;
}
</style>
