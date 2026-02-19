<template>
  <n-layout has-sider style="height: 100vh">
    <!-- 侧边栏 -->
    <n-layout-sider
      bordered
      :collapsed="collapsed"
      collapse-mode="width"
      :collapsed-width="64"
      :width="220"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
      :native-scrollbar="false"
      style="background: #16213e"
    >
      <div style="padding: 16px; text-align: center">
        <n-text style="font-size: 20px; color: #e94560" strong>
          {{ collapsed ? '🤖' : '🤖 AI设计院' }}
        </n-text>
      </div>

      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeKey"
        @update:value="handleMenuClick"
        :root-indent="20"
      />

      <div v-if="!collapsed" style="position: absolute; bottom: 16px; left: 16px; right: 16px">
        <n-text depth="3" style="font-size: 12px">
          设计院 Studio v1.0
        </n-text>
      </div>
    </n-layout-sider>

    <!-- 主内容区 -->
    <n-layout>
      <n-layout-header bordered style="height: 56px; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; background: #16213e">
        <n-breadcrumb>
          <n-breadcrumb-item @click="$router.push('/')">设计院</n-breadcrumb-item>
          <n-breadcrumb-item v-if="routeName">{{ routeName }}</n-breadcrumb-item>
        </n-breadcrumb>

        <n-space align="center" :size="12">
          <n-tag :bordered="false" type="success" size="small" round>
            <template #icon><n-icon :component="PulseOutline" /></template>
            运行中
          </n-tag>

          <!-- 当前用户 -->
          <n-tag v-if="authStore.user" :bordered="false" :type="authStore.isAdmin ? 'warning' : 'info'" size="small" round>
            {{ authStore.user.nickname || authStore.user.username }}
            <template #icon>
              <span style="font-size: 12px">{{ authStore.isAdmin ? '👑' : '👤' }}</span>
            </template>
          </n-tag>

          <n-button quaternary circle size="small" @click="$router.push('/settings')">
            <template #icon><n-icon :component="SettingsOutline" /></template>
          </n-button>
          <n-button quaternary circle size="small" tag="a" href="/" target="_blank">
            <template #icon><n-icon :component="OpenOutline" /></template>
          </n-button>
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button quaternary circle size="small" @click="handleLogout">
                <template #icon><n-icon :component="LogOutOutline" /></template>
              </n-button>
            </template>
            退出登录
          </n-tooltip>
        </n-space>
      </n-layout-header>

      <n-layout-content
        content-style="padding: 24px"
        :native-scrollbar="false"
        style="background: #0f3460"
      >
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, computed, h, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import {
  HomeOutline,
  DocumentTextOutline,
  CameraOutline,
  SettingsOutline,
  PulseOutline,
  OpenOutline,
  LogOutOutline,
} from '@vicons/ionicons5'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const collapsed = ref(false)

const activeKey = computed(() => {
  const path = route.path
  if (path === '/' || path === '') return 'projects'
  if (path.includes('/projects/')) return 'projects'
  if (path.includes('/projects')) return 'projects'
  if (path.includes('/snapshots')) return 'snapshots'
  if (path.includes('/settings')) return 'settings'
  return 'projects'
})

const routeName = computed(() => {
  const map: Record<string, string> = {
    Dashboard: '项目',
    ProjectList: '项目',
    ProjectDetail: '项目详情',
    Snapshots: '快照管理',
    Settings: '设置',
  }
  return map[route.name as string] || ''
})

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  { label: '项目', key: 'projects', icon: renderIcon(DocumentTextOutline) },
  { label: '快照管理', key: 'snapshots', icon: renderIcon(CameraOutline) },
  { label: '设置', key: 'settings', icon: renderIcon(SettingsOutline) },
]

// 持久化每个菜单区域最后访问的路径
const lastPaths: Record<string, string> = {
  projects: sessionStorage.getItem('nav_projects') || '/',
  snapshots: sessionStorage.getItem('nav_snapshots') || '/snapshots',
  settings: sessionStorage.getItem('nav_settings') || '/settings',
}

// 监听路由变化，记录当前菜单区域的路径
watch(() => route.fullPath, (path) => {
  const key = activeKey.value
  if (key) {
    lastPaths[key] = path
    sessionStorage.setItem(`nav_${key}`, path)
  }
}, { immediate: true })

function handleMenuClick(key: string) {
  router.push(lastPaths[key] || '/')
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>
