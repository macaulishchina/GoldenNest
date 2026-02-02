<template>
  <n-layout class="layout" has-sider>
    <!-- 侧边栏 -->
    <n-layout-sider 
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
      <n-layout-header bordered class="header">
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
      
      <n-layout-content class="content">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
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
  DocumentTextOutline
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const userStore = useUserStore()

const collapsed = ref(false)
const family = ref<any>(null)

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
  loadFamily()
})
</script>

<style scoped>
.layout {
  min-height: 100vh;
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
</style>
