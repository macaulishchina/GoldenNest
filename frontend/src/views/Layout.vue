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
      
      <div class="sider-footer" v-show="!collapsed">
        <n-button text @click="handleLogout">
          退出登录
        </n-button>
      </div>
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
            <n-tag v-if="family" type="success" round>
              🏡 {{ family.name }}
            </n-tag>
          </div>
        </div>
      </n-layout-header>
      
      <!-- 移动端顶部 - 带汉堡菜单 -->
      <div v-if="isMobile" class="mobile-header">
        <div class="mobile-header-content">
          <span class="mobile-logo">🏠 小金库</span>
          <div class="mobile-header-right">
            <n-tag v-if="family" type="success" size="small" round>
              {{ family.name }}
            </n-tag>
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
            <n-icon :size="24">
              <component :is="tab.icon" />
            </n-icon>
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
          <!-- 资金管理 -->
          <div class="drawer-section">
            <div class="drawer-section-title">💰 资金管理</div>
            <div class="drawer-menu-items">
              <div class="drawer-menu-item" @click="navigateAndClose('/deposit')">
                <n-icon :size="20"><WalletOutline /></n-icon>
                <span>存款管理</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/expense')">
                <n-icon :size="20"><CardOutline /></n-icon>
                <span>支出申请</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/transaction')">
                <n-icon :size="20"><ListOutline /></n-icon>
                <span>交易记录</span>
              </div>
            </div>
          </div>
          
          <!-- 财务分析 -->
          <div class="drawer-section">
            <div class="drawer-section-title">📊 财务分析</div>
            <div class="drawer-menu-items">
              <div class="drawer-menu-item" @click="navigateAndClose('/equity')">
                <n-icon :size="20"><PieChartOutline /></n-icon>
                <span>股权结构</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/investment')">
                <n-icon :size="20"><TrendingUpOutline /></n-icon>
                <span>理财配置</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/gift')">
                <n-icon :size="20"><GiftOutline /></n-icon>
                <span>股权赠与</span>
              </div>
            </div>
          </div>
          
          <!-- 家庭互动 -->
          <div class="drawer-section">
            <div class="drawer-section-title">🎉 家庭互动</div>
            <div class="drawer-menu-items">
              <div class="drawer-menu-item" @click="navigateAndClose('/achievement')">
                <n-icon :size="20"><TrophyOutline /></n-icon>
                <span>成就殿堂</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/vote')">
                <n-icon :size="20"><CheckboxOutline /></n-icon>
                <span>股东大会</span>
              </div>
              <div class="drawer-menu-item" @click="navigateAndClose('/announcement')">
                <n-icon :size="20"><MegaphoneOutline /></n-icon>
                <span>家庭公告</span>
              </div>
            </div>
          </div>
          
          <!-- 账户 -->
          <div class="drawer-section">
            <div class="drawer-section-title">⚙️ 账户</div>
            <div class="drawer-menu-items">
              <div class="drawer-menu-item" @click="navigateAndClose('/family')">
                <n-icon :size="20"><PeopleOutline /></n-icon>
                <span>家庭管理</span>
              </div>
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
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, NIcon } from 'naive-ui'
import { useUserStore } from '@/stores/user'
import { familyApi } from '@/api'
import type { MenuOption } from 'naive-ui'
import { 
  HomeOutline, 
  WalletOutline, 
  PieChartOutline,
  TrendingUpOutline,
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
  BusinessOutline,
  SparklesOutline,
  DocumentTextOutline,
  PersonOutline,
  MenuOutline,
  LogOutOutline,
  AddOutline
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const userStore = useUserStore()

const collapsed = ref(false)
const family = ref<any>(null)
const showDrawer = ref(false)
const showShortcutModal = ref(false)

// 响应式检测 - 768px 断点
const isMobile = ref(window.innerWidth < 768)

function handleResize() {
  isMobile.value = window.innerWidth < 768
}

// 固定的3个Tab（首页、宠物、审批）
const fixedTabItems = [
  { key: 'dashboard', label: '首页', icon: HomeOutline },
  { key: 'pet', label: '宠物', icon: PawOutline },
  { key: 'approval', label: '审批', icon: DocumentTextOutline }
]

// 可选的快捷模块列表
const availableModules = [
  { key: 'report', label: '报告', icon: StatsChartOutline },
  { key: 'deposit', label: '存款', icon: WalletOutline },
  { key: 'expense', label: '支出', icon: CardOutline },
  { key: 'equity', label: '股权', icon: PieChartOutline },
  { key: 'investment', label: '理财', icon: TrendingUpOutline },
  { key: 'achievement', label: '成就', icon: TrophyOutline },
  { key: 'vote', label: '投票', icon: CheckboxOutline },
  { key: 'announcement', label: '公告', icon: MegaphoneOutline }
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

// 渲染图标
function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

// 菜单选项
const menuOptions: MenuOption[] = [
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
    label: '资金管理',
    key: 'finance-group',
    icon: renderIcon(CashOutline),
    children: [
      {
        label: '审批中心',
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
      }
    ]
  },
  {
    label: '投资理财',
    key: 'invest-group',
    icon: renderIcon(TrendingUpOutline),
    children: [
      {
        label: '理财产品',
        key: 'investment',
        icon: renderIcon(TrendingUpOutline)
      },
      {
        label: '年度报告',
        key: 'report',
        icon: renderIcon(StatsChartOutline)
      }
    ]
  },
  {
    type: 'divider',
    key: 'd2'
  },
  {
    label: '家庭事务',
    key: 'family-group',
    icon: renderIcon(BusinessOutline),
    children: [
      {
        label: '家庭管理',
        key: 'family',
        icon: renderIcon(PeopleOutline)
      },
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
        label: '股东大会',
        key: 'vote',
        icon: renderIcon(CheckboxOutline)
      }
    ]
  },
  {
    label: '趣味互动',
    key: 'fun-group',
    icon: renderIcon(SparklesOutline),
    children: [
      {
        label: '家庭宠物',
        key: 'pet',
        icon: renderIcon(PawOutline)
      },
      {
        label: '家庭公告',
        key: 'announcement',
        icon: renderIcon(MegaphoneOutline)
      },
      {
        label: '成就殿堂',
        key: 'achievement',
        icon: renderIcon(TrophyOutline)
      }
    ]
  }
]

function handleMenuClick(key: string) {
  if (key === 'dashboard') {
    router.push('/')
  } else {
    router.push(`/${key}`)
  }
}

function handleLogout() {
  userStore.logout()
  message.success('已退出登录')
  router.push('/login')
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

onMounted(() => {
  window.addEventListener('resize', handleResize)
  loadFamily()
  loadCustomShortcut()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
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
  background: white;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
}

.logo-icon {
  font-size: 28px;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #10b981;
}

.sider-footer {
  margin-top: auto;
  padding: 16px;
  text-align: center;
  border-top: 1px solid #f0f0f0;
}

.header {
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  background: white;
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
  color: #1e293b;
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

.content {
  background: linear-gradient(135deg, #f0fdf4 0%, #ecfeff 100%);
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
  background: linear-gradient(135deg, #f0fdf4 0%, #ecfeff 100%);
  padding: 12px 16px;
  /* 使用阴影替代边框，避免滚动时的视觉瑕疵 */
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
  color: #10b981;
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
  background: #f3f4f6;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}

.hamburger-btn:active {
  background: #e5e7eb;
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
  /* 使用flex布局，让内容和安全区分开 */
  display: flex;
  flex-direction: column;
  background: white;
  border-top: 1px solid #e5e7eb;
}

/* 导航栏内容区 - 固定高度，包含图标和文字 */
.mobile-tabbar-inner {
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
  background: white;
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
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
  min-height: 44px;
}

.tabbar-item:active {
  transform: scale(0.95);
}

.tabbar-item.active {
  color: #10b981;
}

.tabbar-item.active .tabbar-label {
  font-weight: 600;
}

.tabbar-label {
  font-size: 11px;
  line-height: 1;
}

/* ============================================
   抽屉菜单样式
   ============================================ */
.drawer-menu {
  padding: 8px 0;
}

.drawer-section {
  margin-bottom: 24px;
}

.drawer-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  padding: 0 4px 12px;
  border-bottom: 1px solid #f3f4f6;
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
  color: #374151;
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}

.drawer-menu-item:active {
  background: #f3f4f6;
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

/* 气泡菜单 */
.shortcut-popup {
  position: absolute;
  bottom: 70px;
  left: 50%;
  transform: translateX(-50%);
  width: 280px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  z-index: 2000;
  overflow: hidden;
}

/* 气泡箭头 */
.popup-arrow {
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 10px solid transparent;
  border-right: 10px solid transparent;
  border-top: 10px solid white;
  filter: drop-shadow(0 2px 2px rgba(0, 0, 0, 0.1));
}

.popup-header {
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.popup-header span:first-child {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.popup-hint {
  font-size: 12px;
  color: #9ca3af;
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
  color: #6b7280;
  -webkit-tap-highlight-color: transparent;
}

.popup-item:active {
  background: #f3f4f6;
  transform: scale(0.95);
}

.popup-item.selected {
  background: #ecfdf5;
  color: #10b981;
}

.popup-item span {
  font-size: 12px;
  white-space: nowrap;
}

.popup-footer {
  padding: 10px 16px;
  border-top: 1px solid #f0f0f0;
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
</style>
