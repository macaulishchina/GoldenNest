<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <router-view />
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import type { GlobalThemeOverrides } from 'naive-ui'

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
