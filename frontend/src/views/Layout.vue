<template>
  <n-layout class="layout" :has-sider="!isMobile">
    <!-- 侧边栏 - 仅桌面端显示 -->
    <n-layout-sider 
      v-if="!isMobile"
      bordered 
      collapse-mode="width"
      :collapsed-width="64"
      :width="220"
      :collapsed="collapsed"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
      class="sider"
    >
      <div class="logo" @click="router.push('/')">
        <span class="logo-icon">🏠</span>
        <span v-show="!collapsed" class="logo-text">小金库</span>
      </div>
      
      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeKey"
        @update:value="handleMenuClick"
      />
      
    </n-layout-sider>
    
    <!-- 主内容区 -->
    <n-layout>
      <!-- 顶部导航 - 仅桌面端显示 -->
      <n-layout-header v-if="!isMobile" bordered class="header">
        <div class="header-content">
          <div class="greeting">
            <span class="wave">👋</span>
            <span>{{ greeting }}，{{ userStore.user?.nickname || '用户' }}</span>
          </div>
          <div class="header-actions">
            <n-tag v-if="holidayGreeting" type="warning" round class="holiday-tag">
              {{ holidayGreeting }}
            </n-tag>
            <n-tag v-if="family" type="success" round>
              🏡 {{ family.name }}
            </n-tag>
            <!-- 主题切换按钮 -->
            <ThemeSelector />
          </div>
        </div>
      </n-layout-header>
      
      <!-- 移动端顶部 - 带汉堡菜单 -->
      <div v-if="isMobile" class="mobile-header">
        <div class="mobile-header-content">
          <span class="mobile-logo">🏠 小金库</span>
          <div class="mobile-header-right">
            <n-tag v-if="holidayGreeting" type="warning" size="small" round class="holiday-tag">
              {{ holidayGreeting }}
            </n-tag>
            <n-tag v-else-if="family" type="success" size="small" round>
              {{ family.name }}
            </n-tag>
            <!-- 主题切换按钮 -->
            <ThemeSelector />
            <div class="hamburger-btn" @click="showDrawer = true">
              <n-icon :size="24"><MenuOutline /></n-icon>
            </div>
          </div>
        </div>
      </div>
      
      <n-layout-content class="content" :class="{ 'mobile-content': isMobile }">
        <router-view />
      </n-layout-content>
      
      <!-- 移动端底部导航栏 -->
      <div v-if="isMobile" class="mobile-tabbar">
        <!-- 内容区包装器 - 固定60px高度，不受safe-area影响 -->
        <div class="mobile-tabbar-inner">
          <!-- 前3个固定Tab -->
          <div
            v-for="tab in fixedTabItems"
            :key="tab.key"
            class="tabbar-item"
            :class="{ active: isTabActive(tab.key) }"
            @click="handleTabClick(tab.key)"
          >
            <div style="position: relative">
              <n-icon :size="24">
                <component :is="tab.icon" />
              </n-icon>
              <!-- 审批中心徽章 -->
              <div
                v-if="tab.key === 'approval' && approvalStore.pendingCount > 0"
                class="tabbar-badge"
              >
                {{ approvalStore.pendingCount > 99 ? '99+' : approvalStore.pendingCount }}
              </div>
            </div>
            <span class="tabbar-label">{{ tab.label }}</span>
          </div>
          
          <!-- 第4个：可自定义快捷按钮 -->
          <div class="shortcut-wrapper">
            <div 
              class="tabbar-item shortcut-item"
              :class="{ active: customShortcut && isTabActive(customShortcut.key) }"
              @click="handleShortcutClick"
              @touchstart="handleShortcutTouchStart"
              @touchend="handleShortcutTouchEnd"
              @touchcancel="handleShortcutTouchEnd"
              @contextmenu.prevent="showShortcutPicker"
            >
              <n-icon :size="24">
                <component :is="customShortcut?.icon || AddOutline" />
              </n-icon>
              <span class="tabbar-label">{{ customShortcut?.label || '快捷' }}</span>
            </div>
            
            <!-- 气泡菜单 - 在+按钮上方弹出 -->
            <Transition name="popup">
              <div v-if="showShortcutModal" class="shortcut-popup">
                <div class="popup-header">
                  <span>选择快捷入口</span>
                  <span class="popup-hint">长按可更换</span>
                </div>
                <div class="popup-grid">
                  <div 
                    v-for="mod in availableModules" 
                    :key="mod.key"
                    class="popup-item"
                    :class="{ selected: customShortcut?.key === mod.key }"
                    @click.stop="selectShortcut(mod)"
                  >
                    <n-icon :size="24">
                      <component :is="mod.icon" />
                    </n-icon>
                    <span>{{ mod.label }}</span>
                  </div>
                </div>
                <div class="popup-footer" v-if="customShortcut">
                  <span class="clear-btn" @click.stop="clearShortcut">清除</span>
                </div>
                <!-- 小三角箭头 -->
                <div class="popup-arrow"></div>
              </div>
            </Transition>
            
            <!-- 遮罩层 -->
            <div v-if="showShortcutModal" class="popup-overlay" @click="showShortcutModal = false"></div>
          </div>
          
          <!-- 第5个：我的 -->
          <div 
            class="tabbar-item"
            :class="{ active: isTabActive('family') }"
            @click="handleTabClick('family')"
          >
            <n-icon :size="24">
              <PersonOutline />
            </n-icon>
            <span class="tabbar-label">我的</span>
          </div>
        </div>
        <!-- safe-area 填充区域由 ::after 伪元素处理 -->
      </div>
      
    </n-layout>
    
    <!-- 移动端侧边抽屉菜单 -->
    <n-drawer v-model:show="showDrawer" :width="280" placement="right">
      <n-drawer-content title="更多功能" closable>
        <div class="drawer-menu">
          <!-- 用户信息区域 -->
          <div class="drawer-user-section">
            <div class="drawer-avatar-wrapper" @click="triggerDrawerAvatarUpload">
              <!-- 使用 URL 方式加载头像 -->
              <img 
                v-if="userStore.user?.id && !selfAvatarError" 
                :src="`/api/auth/users/${userStore.user.id}/avatar?t=${avatarCacheKey}`" 
                class="drawer-avatar-img"
                alt="头像"
                @error="selfAvatarError = true"
              />
              <!-- 无头像或加载失败时显示首字母 -->
              <n-avatar 
                v-else
                round 
                :size="56" 
                :style="{ backgroundColor: getAvatarColor(userStore.user?.nickname || '') }"
              >
                {{ userStore.user?.nickname?.[0] || '?' }}
              </n-avatar>
              <div class="drawer-avatar-camera">
                <n-icon :size="12"><CameraOutline /></n-icon>
              </div>
            </div>
            <div class="drawer-user-info">
              <div class="drawer-user-name">{{ userStore.user?.nickname || '用户' }}</div>
              <div class="drawer-user-family" v-if="family">🏡 {{ family.name }}</div>
            </div>
          </div>
          <input 
            ref="drawerAvatarInputRef" 
            type="file" 
            accept="image/jpeg,image/png,image/gif,image/webp" 
            style="display: none" 
            @change="handleDrawerAvatarChange"
          />
          
          <!-- 💰 财务管理 -->
          <div class="drawer-section">
            <div class="drawer-section-title">💰 财务管理</div>
            <div class="drawer-menu-items">
              <div class="drawer-menu-item" @click="navigateAndClose('/approval')">
                <n-icon :size="20"><DocumentTextOutline /></n-icon>
                <span>审批中心</span>
                <n-badge
                  v-if="approvalStore.pendingCount > 0"
                  :value="approvalStore.pendingCount"
                  :max="99"
                  type="error"
                  style="margin-left: auto"
                />
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/deposit')">
                <n-icon :size="20"><WalletOutline /></n-icon>
                <span>资金注入</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/expense')">
                <n-icon :size="20"><CardOutline /></n-icon>
                <span>支出申请</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/transaction')">
                <n-icon :size="20"><ListOutline /></n-icon>
                <span>资金流水</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/investment')">
                <n-icon :size="20"><TrendingUpOutline /></n-icon>
                <span>理财产品</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/asset')">
                <n-icon :size="20"><DiamondOutline /></n-icon>
                <span>资产登记</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/report')">
                <n-icon :size="20"><StatsChartOutline /></n-icon>
                <span>年度报告</span>
              </div>
            </div>
          </div>
          
          <!-- �️ 家庭治理 -->
          <div class="drawer-section">
            <div class="drawer-section-title">🏛️ 家庭治理</div>
            <div class="drawer-menu-items">
              <div class="drawer-menu-item" @click="navigateAndClose('/equity')">
                <n-icon :size="20"><PieChartOutline /></n-icon>
                <span>股权结构</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/gift')">
                <n-icon :size="20"><GiftOutline /></n-icon>
                <span>股权赠与</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/vote')">
                <n-icon :size="20"><CheckboxOutline /></n-icon>
                <span>股东大会</span>
                <n-badge
                  v-if="voteStore.pendingCount > 0"
                  :value="voteStore.pendingCount"
                  :max="99"
                  type="error"
                  style="margin-left: auto"
                />
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/family')">
                <n-icon :size="20"><PeopleOutline /></n-icon>
                <span>家庭管理</span>
              </div>
            </div>
          </div>
          
          <!-- 🌟 生活协作 -->
          <div class="drawer-section">
            <div class="drawer-section-title">🌟 生活协作</div>
            <div class="drawer-menu-items">
              <div class="drawer-menu-item" @click="navigateAndClose('/todo')">
                <n-icon :size="20"><ClipboardOutline /></n-icon>
                <span>家庭清单</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/calendar')">
                <n-icon :size="20"><CalendarOutline /></n-icon>
                <span>共享日历</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/announcement')">
                <n-icon :size="20"><MegaphoneOutline /></n-icon>
                <span>家庭公告</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/pet')">
                <n-icon :size="20"><PawOutline /></n-icon>
                <span>家庭宠物</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/achievement')">
                <n-icon :size="20"><TrophyOutline /></n-icon>
                <span>成就殿堂</span>
              </div>
            </div>
          </div>
          
          <!-- ⚙️ 系统设置 -->
          <div class="drawer-section">
            <div class="drawer-section-title">⚙️ 系统设置</div>
            <div class="drawer-menu-items">
              <div class="drawer-menu-item logout" @click="handleLogout">
                <n-icon :size="20"><LogOutOutline /></n-icon>
                <span>退出登录</span>
              </div>
            </div>
          </div>
        </div>
      </n-drawer-content>
    </n-drawer>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, h, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, NIcon, NBadge } from 'naive-ui'
import { useUserStore } from '@/stores/user'
import { useApprovalStore } from '@/stores/approval'
import { useVoteStore } from '@/stores/vote'
import { familyApi } from '@/api'
import { getHolidayGreeting } from '@/utils/holiday'
import { compressImage, getAvatarColor } from '@/utils/avatar'
import type { MenuOption } from 'naive-ui'
import { markRaw } from 'vue'
import ThemeSelector from '@/components/ThemeSelector.vue'
import { 
  HomeOutline, 
  WalletOutline, 
  PieChartOutline,
  TrendingUpOutline,
  DiamondOutline,
  CardOutline,
  ListOutline,
  PeopleOutline,
  TrophyOutline,
  GiftOutline,
  CheckboxOutline,
  PawOutline,
  MegaphoneOutline,
  StatsChartOutline,
  CashOutline,
  SettingsOutline,
  DocumentTextOutline,
  PersonOutline,
  MenuOutline,
  LogOutOutline,
  AddOutline,
  CameraOutline,
  ClipboardOutline,
  CalendarOutline
} from '@vicons/ionicons5'
import { api } from '@/api'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const userStore = useUserStore()
const approvalStore = useApprovalStore()
const voteStore = useVoteStore()

const collapsed = ref(false)
const family = ref<any>(null)
const showDrawer = ref(false)
const showShortcutModal = ref(false)
const drawerAvatarInputRef = ref<HTMLInputElement | null>(null)
const avatarUploading = ref(false)
const selfAvatarError = ref(false)
const avatarCacheKey = ref(Date.now())

// 响应式检测 - 768px 断点
const isMobile = ref(window.innerWidth < 768)

function handleResize() {
  isMobile.value = window.innerWidth < 768
}

// 固定的3个Tab（首页、宠物、审批）- 使用 markRaw 避免 Vue 将组件变为响应式
const fixedTabItems = [
  { key: 'dashboard', label: '首页', icon: markRaw(HomeOutline) },
  { key: 'pet', label: '宠物', icon: markRaw(PawOutline) },
  { key: 'approval', label: '审批', icon: markRaw(DocumentTextOutline) }
]

// 可选的快捷模块列表（按分类排序：财务管理、家庭事务）- 使用 markRaw 包装图标组件
const availableModules = [
  // 财务管理
  { key: 'deposit', label: '存款', icon: markRaw(WalletOutline) },
  { key: 'expense', label: '支出', icon: markRaw(CardOutline) },
  { key: 'transaction', label: '流水', icon: markRaw(ListOutline) },
  { key: 'investment', label: '理财', icon: markRaw(TrendingUpOutline) },
  { key: 'asset', label: '资产', icon: markRaw(DiamondOutline) },
  { key: 'report', label: '报告', icon: markRaw(StatsChartOutline) },
  // 家庭事务
  { key: 'equity', label: '股权', icon: markRaw(PieChartOutline) },
  { key: 'gift', label: '赠与', icon: markRaw(GiftOutline) },
  { key: 'vote', label: '投票', icon: markRaw(CheckboxOutline) },
  { key: 'todo', label: '清单', icon: markRaw(ClipboardOutline) },
  { key: 'calendar', label: '日历', icon: markRaw(CalendarOutline) },
  { key: 'announcement', label: '公告', icon: markRaw(MegaphoneOutline) },
  { key: 'achievement', label: '成就', icon: markRaw(TrophyOutline) }
]

// 用户自定义的快捷模块
const customShortcut = ref<{ key: string; label: string; icon: any } | null>(null)

// 长按计时器
let longPressTimer: ReturnType<typeof setTimeout> | null = null
const LONG_PRESS_DURATION = 500 // 长按阈值：500ms

// 从 localStorage 加载自定义快捷方式
function loadCustomShortcut() {
  const saved = localStorage.getItem('customShortcut')
  if (saved) {
    try {
      const { key } = JSON.parse(saved)
      const found = availableModules.find(m => m.key === key)
      if (found) {
        customShortcut.value = found
      }
    } catch {
      // 解析失败，忽略
    }
  }
}

// 保存自定义快捷方式到 localStorage
function saveCustomShortcut() {
  if (customShortcut.value) {
    localStorage.setItem('customShortcut', JSON.stringify({ key: customShortcut.value.key }))
  } else {
    localStorage.removeItem('customShortcut')
  }
}

// 显示快捷模块选择器
function showShortcutPicker() {
  showShortcutModal.value = true
}

// 选择快捷模块
function selectShortcut(mod: { key: string; label: string; icon: any }) {
  customShortcut.value = mod
  saveCustomShortcut()
  showShortcutModal.value = false
  message.success(`已设置 "${mod.label}" 为快捷入口`)
}

// 清除快捷方式
function clearShortcut() {
  customShortcut.value = null
  saveCustomShortcut()
  showShortcutModal.value = false
  message.info('已清除快捷方式')
}

// 快捷按钮点击处理
function handleShortcutClick() {
  if (customShortcut.value) {
    // 已设置：跳转到对应页面
    router.push(`/${customShortcut.value.key}`)
  } else {
    // 未设置：弹出选择菜单
    showShortcutPicker()
  }
}

// 触摸开始 - 开始长按计时
function handleShortcutTouchStart() {
  longPressTimer = setTimeout(() => {
    showShortcutPicker()
    longPressTimer = null
  }, LONG_PRESS_DURATION)
}

// 触摸结束 - 取消长按计时
function handleShortcutTouchEnd() {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

// 保留原始的移动端 Tab 配置（兼容）
const mobileTabItems = [
  { key: 'dashboard', label: '首页', icon: HomeOutline },
  { key: 'pet', label: '宠物', icon: PawOutline },
  { key: 'approval', label: '审批', icon: DocumentTextOutline },
  { key: 'report', label: '报告', icon: StatsChartOutline },
  { key: 'family', label: '我的', icon: PersonOutline }
]

// 判断 Tab 是否激活
function isTabActive(key: string): boolean {
  const path = route.path
  if (key === 'dashboard') return path === '/'
  return path === `/${key}`
}

// 移动端 Tab 点击
function handleTabClick(key: string) {
  if (key === 'dashboard') {
    router.push('/')
  } else {
    router.push(`/${key}`)
  }
}

// 抽屉内导航并关闭
function navigateAndClose(path: string) {
  router.push(path)
  showDrawer.value = false
}

// 当前激活的菜单
const activeKey = computed(() => {
  const path = route.path
  if (path === '/') return 'dashboard'
  return path.slice(1)
})

// 问候语
const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

// 节日彩蛋
const holidayGreeting = computed(() => {
  return getHolidayGreeting()
})

// 渲染图标
function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

// 自定义渲染审批中心菜单项（带徽章）
function renderApprovalLabel() {
  return h(
    'div',
    { style: { display: 'flex', alignItems: 'center', gap: '8px', width: '100%' } },
    [
      h('span', '审批中心'),
      approvalStore.pendingCount > 0
        ? h(NBadge, {
            value: approvalStore.pendingCount,
            type: 'error',
            max: 99,
            showZero: false
          })
        : null
    ]
  )
}

// 自定义渲染股东大会菜单项（带徽章）
function renderVoteLabel() {
  return h(
    'div',
    { style: { display: 'flex', alignItems: 'center', gap: '8px', width: '100%' } },
    [
      h('span', '股东大会'),
      voteStore.pendingCount > 0
        ? h(NBadge, {
            value: voteStore.pendingCount,
            type: 'error',
            max: 99,
            showZero: false
          })
        : null
    ]
  )
}

// 自定义渲染财务管理分组（带红点）
function renderFinanceGroupLabel() {
  return h(
    'div',
    { style: { display: 'flex', alignItems: 'center', gap: '8px', width: '100%' } },
    [
      h('span', '财务管理'),
      approvalStore.pendingCount > 0
        ? h(NBadge, {
            dot: true,
            type: 'error',
            showZero: false
          })
        : null
    ]
  )
}

// 自定义渲染家庭治理分组（带红点）
function renderGovernanceGroupLabel() {
  return h(
    'div',
    { style: { display: 'flex', alignItems: 'center', gap: '8px', width: '100%' } },
    [
      h('span', '家庭治理'),
      voteStore.pendingCount > 0
        ? h(NBadge, {
            dot: true,
            type: 'error',
            showZero: false
          })
        : null
    ]
  )
}

// 菜单选项 - 方案B三分类: 财务管理、家庭治理、生活协作
const menuOptions = computed<MenuOption[]>(() => [
  {
    label: '仪表盘',
    key: 'dashboard',
    icon: renderIcon(HomeOutline)
  },
  {
    type: 'divider',
    key: 'd1'
  },
  {
    label: renderFinanceGroupLabel,
    key: 'finance-group',
    icon: renderIcon(CashOutline),
    children: [
      {
        label: renderApprovalLabel,
        key: 'approval',
        icon: renderIcon(DocumentTextOutline)
      },
      {
        label: '资金注入',
        key: 'deposit',
        icon: renderIcon(WalletOutline)
      },
      {
        label: '支出申请',
        key: 'expense',
        icon: renderIcon(CardOutline)
      },
      {
        label: '资金流水',
        key: 'transaction',
        icon: renderIcon(ListOutline)
      },
      {
        label: '理财产品',
        key: 'investment',
        icon: renderIcon(TrendingUpOutline)
      },
      {
        label: '资产登记',
        key: 'asset',
        icon: renderIcon(DiamondOutline)
      },
      {
        label: '年度报告',
        key: 'report',
        icon: renderIcon(StatsChartOutline)
      }
    ]
  },
  {
    label: renderGovernanceGroupLabel,
    key: 'governance-group',
    icon: renderIcon(PieChartOutline),
    children: [
      {
        label: '股权结构',
        key: 'equity',
        icon: renderIcon(PieChartOutline)
      },
      {
        label: '股权赠与',
        key: 'gift',
        icon: renderIcon(GiftOutline)
      },
      {
        label: renderVoteLabel,
        key: 'vote',
        icon: renderIcon(CheckboxOutline)
      },
      {
        label: '家庭管理',
        key: 'family',
        icon: renderIcon(PeopleOutline)
      }
    ]
  },
  {
    label: '生活协作',
    key: 'life-group',
    icon: renderIcon(CalendarOutline),
    children: [
      {
        label: '家庭清单',
        key: 'todo',
        icon: renderIcon(ClipboardOutline)
      },
      {
        label: '共享日历',
        key: 'calendar',
        icon: renderIcon(CalendarOutline)
      },
      {
        label: '家庭公告',
        key: 'announcement',
        icon: renderIcon(MegaphoneOutline)
      },
      {
        label: '家庭宠物',
        key: 'pet',
        icon: renderIcon(PawOutline)
      },
      {
        label: '成就殿堂',
        key: 'achievement',
        icon: renderIcon(TrophyOutline)
      }
    ]
  },
  {
    type: 'divider',
    key: 'd2'
  },
  {
    label: '系统设置',
    key: 'settings-group',
    icon: renderIcon(SettingsOutline),
    children: [
      {
        label: '退出登录',
        key: 'logout',
        icon: renderIcon(LogOutOutline)
      }
    ]
  }
])

function handleMenuClick(key: string) {
  if (key === 'dashboard') {
    router.push('/')
  } else if (key === 'logout') {
    handleLogout()
  } else {
    router.push(`/${key}`)
  }
}

function handleLogout() {
  userStore.logout()
  message.success('已退出登录')
  router.push('/login')
}

// ========== 头像相关功能 ==========

// 触发抽屉头像上传
function triggerDrawerAvatarUpload() {
  if (avatarUploading.value) return
  drawerAvatarInputRef.value?.click()
}

// 处理抽屉头像文件选择
async function handleDrawerAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  
  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    message.error('请选择图片文件')
    return
  }
  
  // 验证原始文件大小（限制20MB，防止浏览器卡死）
  if (file.size > 20 * 1024 * 1024) {
    message.error('图片大小不能超过 20MB')
    return
  }
  
  avatarUploading.value = true
  
  try {
    // 先压缩图片为适合头像的大小（200x200）
    const base64 = await compressImage(file)
    
    // 压缩后检查大小（2MB限制，Base64约为原始数据的1.37倍）
    const compressedSize = base64.length * 0.75 // 估算实际字节数
    if (compressedSize > 2 * 1024 * 1024) {
      message.error('图片压缩后仍超过 2MB，请选择更小的图片')
      avatarUploading.value = false
      return
    }
    
    // 上传到服务器
    const res = await api.put('/auth/avatar', { avatar: base64 })
    
    if (res.data.success) {
      // 更新本地用户信息
      await userStore.fetchUser()
      // 刷新头像缓存
      selfAvatarError.value = false
      avatarCacheKey.value = Date.now()
      message.success('头像更新成功！')
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '头像上传失败')
  } finally {
    avatarUploading.value = false
    // 清空 input，允许再次选择相同文件
    input.value = ''
  }
}

// 读取文件为 base64
function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

async function loadFamily() {
  try {
    if (userStore.user?.family_id) {
      const response = await familyApi.getMy()
      family.value = response.data
    }
  } catch {
    // 用户还没有加入家庭
    family.value = null
  }
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  loadFamily()
  loadCustomShortcut()

  // 初始加载审批徽章计数
  if (userStore.isLoggedIn) {
    await approvalStore.fetchPendingCount()
    // 启动轮询（保底机制）
    approvalStore.startPolling()
    
    // 初始加载投票徽章计数
    await voteStore.fetchPendingCount()
    // 启动轮询（保底机制）
    voteStore.startPolling()
  }
})

// 路由变化时刷新审批计数和投票计数
watch(() => route.path, async () => {
  if (userStore.isLoggedIn) {
    // 每次路由切换都查询一次
    await approvalStore.refreshNow()
    await voteStore.refreshNow()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  // 停止轮询
  approvalStore.stopPolling()
  voteStore.stopPolling()
})
</script>

<style scoped>
.layout {
  min-height: 100vh;
  /* iOS Safari 动态视口高度适配 */
  min-height: calc(var(--vh, 1vh) * 100);
  min-height: 100dvh; /* 现代浏览器支持的动态视口高度 */
}

.sider {
  display: flex;
  flex-direction: column;
  background: var(--theme-bg-card, white);
  border-right: 1px solid var(--theme-border, #f0f0f0);
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  border-bottom: 1px solid var(--theme-border, #f0f0f0);
}

.logo-icon {
  font-size: 28px;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--theme-primary, #10b981);
}

.sider-footer {
  margin-top: auto;
  padding: 16px;
  text-align: center;
  border-top: 1px solid var(--theme-border, #f0f0f0);
}

.header {
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  background: var(--theme-bg-card, white);
  border-bottom: 1px solid var(--theme-border, #e5e7eb);
}

.header-content {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.greeting {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  color: var(--theme-text-primary, #1e293b);
}

.wave {
  animation: wave 1.5s ease-in-out infinite;
}

@keyframes wave {
  0%, 100% {
    transform: rotate(0deg);
  }
  25% {
    transform: rotate(20deg);
  }
  75% {
    transform: rotate(-20deg);
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.holiday-tag {
  animation: holiday-glow 2s ease-in-out infinite;
}

@keyframes holiday-glow {
  0%, 100% {
    box-shadow: 0 0 5px rgba(251, 191, 36, 0.3);
  }
  50% {
    box-shadow: 0 0 15px rgba(251, 191, 36, 0.6);
  }
}

.content {
  /* 移除固定背景，使用透明背景显示 body 的主题色 */
  background: transparent;
  min-height: calc(100vh - 64px);
}

/* ============================================
   移动端样式
   ============================================ */

/* 移动端顶部 */
.mobile-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--theme-bg-card, white);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: 12px 16px;
  border-bottom: 1px solid var(--theme-border, #e5e7eb);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.mobile-header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.mobile-logo {
  font-size: 18px;
  font-weight: 700;
  color: var(--theme-primary, #10b981);
}

.mobile-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 汉堡菜单按钮 */
.hamburger-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--theme-bg-secondary, #f3f4f6);
  color: var(--theme-text-primary, #374151);
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}

.hamburger-btn:active {
  background: var(--theme-border, #e5e7eb);
  transform: scale(0.95);
}

/* 移动端内容区 - 需要为底部导航留空间 */
.mobile-content {
  min-height: calc(100vh - 56px - 60px);
  padding-bottom: 70px;
}

/* 移动端底部导航栏 - 重构为两层结构解决iOS Safari动画问题 */
.mobile-tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  background: var(--theme-bg-card, white);
  border-top: 1px solid var(--theme-border, #e5e7eb);
}

/* 导航栏内容区 - 固定高度，包含图标和文字 */
.mobile-tabbar-inner {
  width: 100%;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  flex-shrink: 0;
}

/* iOS 安全区域填充 - 作为独立元素，不影响内容区 */
.mobile-tabbar::after {
  content: '';
  display: block;
  height: env(safe-area-inset-bottom, 0px);
  background: var(--theme-bg-card, white);
  flex-shrink: 0;
}

.tabbar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 0;
  color: var(--theme-text-secondary, #9ca3af);
  cursor: pointer;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
  min-height: 44px;
}

.tabbar-item:active {
  transform: scale(0.95);
}

.tabbar-item.active {
  color: var(--theme-primary, #10b981);
}

.tabbar-item.active .tabbar-label {
  font-weight: 600;
}

.tabbar-label {
  font-size: 11px;
  line-height: 1;
}

/* 移动端 tabbar 徽章 */
.tabbar-badge {
  position: absolute;
  top: -4px;
  right: -8px;
  background: #f5222d;
  color: white;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 5px;
  border-radius: 10px;
  min-width: 16px;
  text-align: center;
  line-height: 1.2;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* ============================================
   抽屉菜单样式
   ============================================ */
.drawer-menu {
  padding: 8px 0;
}

/* 抽屉用户信息区域 */
.drawer-user-section {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 12px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 14px;
  color: white;
}

.drawer-avatar-wrapper {
  position: relative;
  cursor: pointer;
  flex-shrink: 0;
}

.drawer-avatar-wrapper:active {
  transform: scale(0.95);
}

.drawer-avatar-img {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.drawer-avatar-camera {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.drawer-user-info {
  flex: 1;
  min-width: 0;
}

.drawer-user-name {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.drawer-user-family {
  font-size: 13px;
  opacity: 0.9;
}

.drawer-section {
  margin-bottom: 24px;
}

.drawer-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--theme-text-secondary, #6b7280);
  padding: 0 4px 12px;
  border-bottom: 1px solid var(--theme-border, #f3f4f6);
  margin-bottom: 8px;
}

.drawer-menu-items {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.drawer-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 12px;
  border-radius: 10px;
  color: var(--theme-text-primary, #374151);
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}

.drawer-menu-item:active {
  background: var(--theme-bg-secondary, #f3f4f6);
  transform: scale(0.98);
}

.drawer-menu-item span {
  font-size: 15px;
}

.drawer-menu-item.logout {
  color: #ef4444;
}

.drawer-menu-item.logout:active {
  background: #fef2f2;
}

/* 移动端全局调整 */
@media (max-width: 767px) {
  .content {
    min-height: 100vh;
  }
}

/* ============================================
   快捷按钮气泡菜单样式
   ============================================ */
.shortcut-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  justify-content: center;
}

/* 遮罩层 */
.popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 1999;
}

/* 气泡菜单 - 屏幕居中而非相对于按钮居中 */
.shortcut-popup {
  position: fixed;
  bottom: calc(60px + env(safe-area-inset-bottom, 0px) + 16px);
  left: 50%;
  transform: translateX(-50%);
  width: calc(100vw - 32px);
  max-width: 320px;
  background: var(--theme-bg-card, white);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  z-index: 2000;
  overflow: hidden;
}

/* 气泡箭头 - 指向快捷按钮位置（第4个tab，约60%位置） */
.popup-arrow {
  position: absolute;
  bottom: -8px;
  left: 60%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 10px solid transparent;
  border-right: 10px solid transparent;
  border-top: 10px solid var(--theme-bg-card, white);
  filter: drop-shadow(0 2px 2px rgba(0, 0, 0, 0.1));
}

.popup-header {
  padding: 14px 16px;
  border-bottom: 1px solid var(--theme-border, #f0f0f0);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.popup-header span:first-child {
  font-size: 15px;
  font-weight: 600;
  color: var(--theme-text-primary, #1f2937);
}

.popup-hint {
  font-size: 12px;
  color: var(--theme-text-secondary, #9ca3af);
}

.popup-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  padding: 12px;
}

.popup-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px 8px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--theme-text-secondary, #6b7280);
  -webkit-tap-highlight-color: transparent;
}

.popup-item:active {
  background: var(--theme-bg-secondary, #f3f4f6);
  transform: scale(0.95);
}

.popup-item.selected {
  background: var(--theme-bg-secondary, #ecfdf5);
  color: var(--theme-primary, #10b981);
}

.popup-item span {
  font-size: 12px;
  white-space: nowrap;
}

.popup-footer {
  padding: 10px 16px;
  border-top: 1px solid var(--theme-border, #f0f0f0);
  text-align: center;
}

.clear-btn {
  font-size: 13px;
  color: #ef4444;
  cursor: pointer;
  padding: 4px 12px;
}

.clear-btn:active {
  opacity: 0.7;
}

/* 气泡菜单动画 */
.popup-enter-active,
.popup-leave-active {
  transition: all 0.25s ease;
}

.popup-enter-from,
.popup-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px) scale(0.95);
}

.popup-enter-to,
.popup-leave-from {
  opacity: 1;
  transform: translateX(-50%) translateY(0) scale(1);
}

/* 超窄屏幕优化（<320px） */
@media (max-width: 320px) {
  .shortcut-popup {
    width: calc(100vw - 16px);
  }
  
  .popup-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
