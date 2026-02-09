<template>
  <n-popover trigger="click" placement="bottom-end">
    <template #trigger>
      <n-button circle quaternary size="large" :title="'当前主题：' + themeStore.currentThemeInfo.label">
        <template #icon>
          <span style="font-size: 20px;">{{ themeStore.currentThemeInfo.icon }}</span>
        </template>
      </n-button>
    </template>
    
    <div class="theme-selector">
      <div class="theme-title">选择主题</div>
      <n-space vertical>
        <n-button
          v-for="theme in themeStore.themes"
          :key="theme.name"
          :type="themeStore.currentTheme === theme.name ? 'primary' : 'default'"
          :secondary="themeStore.currentTheme !== theme.name"
          block
          size="large"
          @click="selectTheme(theme.name as any)"
          class="theme-button"
        >
          <template #icon>
            <span style="font-size: 18px;">{{ theme.icon }}</span>
          </template>
          <div class="theme-info">
            <div class="theme-name">{{ theme.label }}</div>
            <div class="theme-desc">{{ theme.description }}</div>
          </div>
        </n-button>
      </n-space>
    </div>
  </n-popover>
</template>

<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'
import type { ThemeMode } from '@/stores/theme'

const themeStore = useThemeStore()

const selectTheme = (theme: ThemeMode) => {
  console.log('ThemeSelector: 切换主题到', theme)
  themeStore.setTheme(theme)
  
  // 调试：检查 CSS 变量是否正确设置
  setTimeout(() => {
    const root = document.documentElement
    const cardBg = getComputedStyle(root).getPropertyValue('--theme-bg-card')
    const primary = getComputedStyle(root).getPropertyValue('--theme-primary')
    console.log('CSS 变量检查:')
    console.log('  --theme-bg-card:', cardBg.trim())
    console.log('  --theme-primary:', primary.trim())
    console.log('  body.className:', document.body.className)
  }, 100)
}
</script>

<style scoped>
.theme-selector {
  padding: 8px;
  min-width: 260px;
}

.theme-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  padding: 0 8px;
  color: var(--n-text-color);
}

.theme-button {
  height: auto;
  padding: 12px 16px;
  text-align: left;
}

.theme-button :deep(.n-button__content) {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.theme-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.theme-name {
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
}

.theme-desc {
  font-size: 12px;
  opacity: 0.7;
  line-height: 1.3;
}
</style>
