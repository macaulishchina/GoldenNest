<template>
  <n-config-provider :theme="themeStore.naiveTheme" :theme-overrides="themeStore.themeOverrides">
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
import { onMounted, onUnmounted, watch } from 'vue'
import AchievementToast from '@/components/AchievementToast.vue'
import { fetchUnshownAchievements } from '@/utils/achievement'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

// 监听主题变化，更新 body 类名
watch(() => themeStore.currentTheme, (newTheme) => {
  console.log('App.vue 检测到主题变化:', newTheme)
  document.body.className = `theme-${newTheme}`
}, { immediate: true })

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
</script>

<style>
#app {
  min-height: 100vh;
}
</style>
