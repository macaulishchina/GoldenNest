<template>
  <n-config-provider :theme="themeStore.naiveTheme" :theme-overrides="themeStore.themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <router-view />
          <!-- Steam 风格成就解锁弹窗 -->
          <AchievementToast />
          <!-- AI 模型调用提示 -->
          <AIModelToast ref="aiModelToastRef" />
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, watch, ref, provide } from 'vue'
import AchievementToast from '@/components/AchievementToast.vue'
import AIModelToast from '@/components/AIModelToast.vue'
import { fetchUnshownAchievements } from '@/utils/achievement'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'
import { setupAIModelInterceptor } from '@/utils/aiModelNotify'
import { initSiteMeta } from '@/utils/siteMeta'

const themeStore = useThemeStore()

// AI 模型调用提示
const aiModelToastRef = ref<InstanceType<typeof AIModelToast> | null>(null)
provide('aiModelToast', aiModelToastRef)

// 监听主题变化，更新 body 类名
watch(() => themeStore.currentTheme, (newTheme) => {
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
  // 注册 AI 模型调用拦截器
  setupAIModelInterceptor(aiModelToastRef)
  // 初始化站点图标和 PWA 元数据
  initSiteMeta()
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
