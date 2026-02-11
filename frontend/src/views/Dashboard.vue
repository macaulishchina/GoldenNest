<template>
  <div class="page-container">
    <div class="page-header-row">
      <h1 class="page-title">
        <span class="icon">📊</span>
        仪表盘
      </h1>
      <div class="header-actions">
        <n-button
          secondary
          type="info"
          size="small"
          @click="showAIChat = true"
          class="ai-chat-btn"
        >
          <template #icon>
            <span style="font-size: 16px">🤖</span>
          </template>
          AI 助手
        </n-button>
        <button class="privacy-toggle" @click="togglePrivacy" :title="privacyMode ? '显示金额' : '隐藏金额'">
          <svg v-if="privacyMode" class="privacy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
            <line x1="1" y1="1" x2="23" y2="23"/>
          </svg>
          <svg v-else class="privacy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </button>
      </div>
    </div>
    
    <!-- AI Chat Dialog -->
    <AIChatDialog
      v-model:show="showAIChat"
      title="💰 财务 AI 助手"
      ai-name="小金助手"
      context-type="dashboard"
      :suggestions="[
        '分析我的储蓄习惯',
        '如何提高家庭资产增长率',
        '给我一些理财建议'
      ]"
      :on-chat="handleAIChat"
    />
    
    <template v-if="hasFamily">
      <!-- 储蓄目标 -->
      <n-card class="target-card card-hover">
        <div class="target-header">
          <h2 class="target-title">🎯 储蓄目标</h2>
          <n-button text @click="showSavingsHelp = !showSavingsHelp" size="small" class="expand-btn">
            {{ showSavingsHelp ? '收起 ▲' : '详情 ▼' }}
          </n-button>
        </div>
        <div class="target-amounts">
          <span class="current-amount">¥{{ formatNumber(equity?.total_savings || 0) }}</span>
          <span class="amount-separator">/</span>
          <span class="target-amount-value">¥{{ formatNumber(equity?.savings_target || 2000000) }}</span>
        </div>
        
        <!-- 简化进度条 -->
        <div class="progress-wrapper">
          <n-progress
            type="line"
            :percentage="Math.min(((equity?.total_savings || 0) / (equity?.savings_target || 2000000)) * 100, 100)"
            :show-indicator="false"
            :height="24"
            :border-radius="12"
            :fill-border-radius="12"
            status="success"
          />
          <div class="progress-text">{{ Math.min(((equity?.total_savings || 0) / (equity?.savings_target || 2000000)) * 100, 100).toFixed(1) }}%</div>
        </div>
        
        <div class="remaining-tip">
          <span class="tip-icon">💰</span>
          <span class="tip-text">还需储蓄</span>
          <strong class="remaining-amount">¥{{ formatNumber(Math.max(0, (equity?.savings_target || 2000000) - (equity?.total_savings || 0))) }}</strong>
        </div>
        <Transition name="fade-slide">
          <div v-show="showSavingsHelp" class="help-content">
            <p><strong>📊 储蓄说明：</strong></p>
            <ul>
              <li>当前储蓄 = 家庭自由资金 + 理财实际价值</li>
              <li>家庭自由资金：可随时支配的现金余额</li>
              <li>理财实际价值：所有理财产品的持仓本金 + 累计收益</li>
              <li>通过"资金注入"和理财投资增加家庭储蓄</li>
            </ul>
            <p><strong>💰 资产计算：</strong></p>
            <div class="assets-summary">
              <div class="summary-item">
                <span class="summary-label">📈 家庭总资产</span>
                <span class="summary-value">¥{{ formatNumber(totalAssets) }}</span>
              </div>
              <div class="summary-divider">=</div>
              <div class="summary-item">
                <span class="summary-label">💵 自由资金</span>
                <span class="summary-value">¥{{ formatNumber(freeBalance) }}</span>
              </div>
              <div class="summary-divider">+</div>
              <div class="summary-item">
                <span class="summary-label">📊 投资本金</span>
                <span class="summary-value">¥{{ formatNumber(investmentTotal) }}</span>
              </div>
              <div class="summary-divider">+</div>
              <div class="summary-item">
                <span class="summary-label">💎 投资收益</span>
                <span class="summary-value">¥{{ formatNumber(investmentIncome) }}</span>
              </div>
            </div>
          </div>
        </Transition>
      </n-card>
      
      <!-- 家庭资金池 -->
      <n-card class="assets-overview card-hover">
        <div class="overview-header">
          <h2 class="overview-title">💰 家庭资金池</h2>
        </div>
        
        <div class="assets-grid">
          <!-- 家庭自由资金 -->
          <div class="asset-card primary-card">
            <div class="asset-icon">💵</div>
            <div class="asset-content">
              <div class="asset-label">家庭自由资金</div>
              <div class="asset-value primary-value">¥{{ formatNumber(freeBalance) }}</div>
              <div class="asset-detail">共享资金池，可用于投资或支出</div>
            </div>
          </div>
          
          <!-- 投资资产 -->
          <div class="asset-card clickable" @click="goToInvestment">
            <div class="asset-icon">📊</div>
            <div class="asset-content">
              <div class="asset-label">投资资产</div>
              <div class="asset-value">¥{{ formatNumber(investmentTotal) }}</div>
              <div class="asset-detail">
                {{ investmentSummary?.active_count || 0 }} 个理财产品 • 
                <span :class="investmentIncome >= 0 ? 'positive-value' : 'negative-value'">
                  {{ investmentIncome >= 0 ? '+' : '' }}¥{{ formatNumber(investmentIncome) }}
                </span>
                ({{ investmentROI }}%)
                <span v-if="averageAnnualizedReturn > 0" style="margin-left: 8px;">
                  • 年化 {{ averageAnnualizedReturn }}%
                </span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 冻结资金说明（如果存在） -->
        <div v-if="frozenAmount > 0" class="frozen-amount-notice">
          <n-alert type="info" :bordered="false">
            <template #icon>
              <span style="font-size: 18px;">🔒</span>
            </template>
            冻结资金（投票中）：<strong>¥{{ formatNumber(frozenAmount) }}</strong>
            <div style="font-size: 12px; margin-top: 4px; opacity: 0.8;">
              该资金已从自由资金中扣除，正在股东大会投票表决中，不计入家庭总资产
            </div>
          </n-alert>
        </div>
      </n-card>
      
      <!-- 股权与储蓄 -->
      <div class="equity-savings-section">
        <!-- 股权分布 -->
        <n-card class="equity-card card-hover">
        <div class="equity-header">
          <h2 class="equity-title">👥 股权分布 <span class="member-count">{{ equity?.members?.length || 0 }}位</span></h2>
          <n-button text @click="showEquityDetail = !showEquityDetail" size="small" class="expand-btn">
            {{ showEquityDetail ? '收起 ▲' : '详情 ▼' }}
          </n-button>
        </div>
        
        <div v-if="equity?.members?.length" class="equity-content">
          <!-- 饼图容器 -->
          <div class="equity-chart-wrapper">
            <div class="equity-chart" ref="chartContainer">
              <v-chart :option="equityChartOption" :autoresize="true" style="height: 260px;" ref="pieChart" />
              
              <!-- 头像覆盖层 -->
              <div class="avatar-overlay">
                <div 
                  v-for="(member, index) in equity?.members" 
                  :key="member.user_id"
                  class="avatar-label"
                  :style="getAvatarPosition(index, equity.members.length)"
                >
                  <UserAvatar 
                    :userId="member.user_id" 
                    :name="member.nickname" 
                    :avatarVersion="member.avatar_version" 
                    :size="36" 
                  />
                  <div class="avatar-percent">{{ ((member.total_deposit / getTotalDeposit()) * 100).toFixed(1) }}%</div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 成员列表（可展开） -->
          <Transition name="fade-slide">
            <div v-show="showEquityDetail" class="equity-list">
              <div v-for="member in equity?.members" :key="member.user_id" class="equity-item">
                <div class="member-info">
                  <UserAvatar :userId="member.user_id" :name="member.nickname" :avatarVersion="member.avatar_version" :size="32" />
                  <div class="member-details">
                    <span class="member-name">{{ member.nickname }}</span>
                    <span class="member-deposit">贡献 ¥{{ formatNumber(member.total_deposit || 0) }}</span>
                  </div>
                </div>
                <div class="member-equity">
                  <div class="equity-bar-wrapper">
                    <n-progress 
                      type="line"
                      :percentage="member.equity_percentage || 0"
                      :height="12"
                      :border-radius="6"
                      :show-indicator="false"
                      :color="getProgressColor(member.equity_percentage || 0)"
                    />
                  </div>
                  <span class="equity-value">{{ (member.equity_percentage || 0).toFixed(1) }}%</span>
                </div>
              </div>
            </div>
          </Transition>
        </div>
        
        <n-empty v-if="!equity?.members?.length" description="暂无成员数据" />
      </n-card>
      </div>
    </template>
    
    <!-- 没有家庭时的引导 -->
    <template v-else>
      <n-card class="welcome-card">
        <n-empty description="您还没有加入家庭">
          <template #extra>
            <n-space>
              <n-button type="primary" @click="router.push('/family')">创建/加入家庭</n-button>
            </n-space>
          </template>
        </n-empty>
      </n-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { equityApi, familyApi, transactionApi, investmentApi, aiChatApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { usePrivacyStore } from '@/stores/privacy'
import UserAvatar from '@/components/UserAvatar.vue'
import AIChatDialog from '@/components/AIChatDialog.vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { NIcon } from 'naive-ui'
import { List as ListOutline, ChevronUp as ChevronUpOutline } from '@vicons/ionicons5'

use([CanvasRenderer, PieChart, TitleComponent, TooltipComponent, LegendComponent])

const router = useRouter()
const userStore = useUserStore()
const privacyStore = usePrivacyStore()
const { privacyMode } = storeToRefs(privacyStore)

const equity = ref<any>(null)
const hasFamily = ref(false)
const balance = ref(0) // 当前余额
const investmentSummary = ref<any>(null) // 理财汇总
const showAIChat = ref(false)
const showSavingsHelp = ref(false) // 储蓄说明展开状态
const showEquityDetail = ref(false) // 股权详情展开状态

// 当前用户的成员信息
const currentMember = computed(() => {
  if (!equity.value?.members || !userStore.user?.id) return null
  return equity.value.members.find((m: any) => m.user_id === userStore.user?.id)
})

// 资金统计计算
const totalAssets = computed(() => {
  // 总资产 = 余额 + 理财本金 + 理财收益
  const investmentPrincipal = investmentSummary.value?.total_principal || 0
  const investmentIncome = investmentSummary.value?.total_income || 0
  return balance.value + investmentPrincipal + investmentIncome
})

const freeBalance = computed(() => {
  // 自由资金 = 当前余额
  return balance.value
})

const investmentTotal = computed(() => {
  // 理财总额（实时CNY价值，外币投资使用实时汇率换算）
  return investmentSummary.value?.total_cny_value || investmentSummary.value?.total_principal || 0
})

const frozenAmount = computed(() => {
  // 冻结资金（投票中的分红）
  return equity.value?.frozen_amount || 0
})

const investmentIncome = computed(() => {
  // 理财总收益
  return investmentSummary.value?.total_income || 0
})

const investmentROI = computed(() => {
  // 理财投资回报率
  const principal = investmentSummary.value?.total_principal || 0
  const income = investmentSummary.value?.total_income || 0
  if (principal === 0) return 0
  return ((income / principal) * 100).toFixed(2)
})

const averageAnnualizedReturn = computed(() => {
  // 综合平均年化收益率
  const rate = investmentSummary.value?.average_annualized_return || 0
  return rate > 0 ? rate.toFixed(2) : 0
})

// 饼图配置
const equityChartOption = computed(() => {
  if (!equity.value?.members?.length) return {}
  
  const colors = ['#18a058', '#2080f0', '#f0a020', '#d03050', '#722ed1', '#13c2c2', '#eb2f96', '#52c41a']
  
  const data = equity.value.members.map((member: any, index: number) => ({
    name: member.nickname,
    value: member.total_deposit || 0,
    itemStyle: {
      color: colors[index % colors.length]
    }
  }))
  
  return {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const percentage = params.percent.toFixed(2)
        return `${params.name}<br/>贡献: ¥${formatNumber(params.value)}<br/>占比: ${percentage}%`
      },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e0e0e6',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      }
    },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        padAngle: 2,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'outside',
          formatter: () => '',  // 空字符串，只显示引导线
          color: 'inherit',
          distanceToLabelLine: 8
        },
        labelLine: {
          show: true,
          length: 15,
          length2: 10,
          smooth: true,
          lineStyle: {
            width: 1.5
          }
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.3)'
          }
        },
        data: data
      }
    ]
  }
})

// 计算总贡献
const getTotalDeposit = () => {
  return equity.value?.members?.reduce((sum: number, m: any) => sum + (m.total_deposit || 0), 0) || 1
}

// 计算头像位置
const getAvatarPosition = (index: number, total: number) => {
  const radius = 130  // 标签距离中心的距离（像素）
  const centerX = 50  // 中心点 X 百分比
  const centerY = 50  // 中心点 Y 百分比
  
  // 计算当前扇区的起始角度和结束角度
  let startAngle = -90  // 从12点钟方向开始
  for (let i = 0; i < index; i++) {
    const percent = ((equity.value.members[i].total_deposit || 0) / getTotalDeposit()) * 100
    startAngle += (percent / 100) * 360
  }
  
  const currentPercent = ((equity.value.members[index].total_deposit || 0) / getTotalDeposit()) * 100
  const middleAngle = startAngle + (currentPercent / 100) * 360 / 2
  
  // 转换为弧度
  const radian = (middleAngle * Math.PI) / 180
  
  // 计算位置
  const x = centerX + (radius / 160) * 50 * Math.cos(radian)  // 160是半个容器宽度的估算
  const y = centerY + (radius / 160) * 50 * Math.sin(radian)
  
  return {
    left: `${x}%`,
    top: `${y}%`,
    transform: 'translate(-50%, -50%)'
  }
}

// 根据时间返回问候语
function getGreeting() {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了，注意休息 🌙'
  if (hour < 9) return '早上好！新的一天开始了 ☀️'
  if (hour < 12) return '上午好！精神满满 💪'
  if (hour < 14) return '中午好！记得吃午饭 🍚'
  if (hour < 18) return '下午好！继续加油 ⭐'
  if (hour < 22) return '晚上好！辛苦一天了 🌆'
  return '夜深了，早点休息 🌙'
}

function togglePrivacy() {
  privacyStore.togglePrivacy()
}

function formatNumber(num: number) {
  return privacyStore.formatMoney(num)
}

function getProgressColor(percentage: number) {
  if (percentage >= 50) return 'var(--theme-success)'
  if (percentage >= 30) return 'var(--theme-info)'
  return 'var(--theme-warning)'
}

function goToInvestment() {
  router.push('/investment')
}

async function handleAIChat(message: string) {
  const response = await aiChatApi.chat({
    message,
    context_type: 'dashboard'
  })
  return {
    reply: response.data.reply,
    suggestions: response.data.suggestions
  }
}

async function loadData() {
  try {
    // 确保用户信息已加载
    if (!userStore.user) {
      await userStore.fetchUser()
    }
    
    // 检查是否有家庭
    if (!userStore.user?.family_id) {
      hasFamily.value = false
      return
    }
    
    // 用户有family_id，设置为true
    hasFamily.value = true
    
    // 并行加载所有数据，单个失败不影响整体
    try {
      const [equityRes, transactionRes, investmentRes] = await Promise.all([
        equityApi.getSummary().catch(err => {
          console.error('Failed to load equity:', err)
          return { data: null }
        }),
        transactionApi.list({ time_range: 'all' }).catch(err => {
          console.error('Failed to load transactions:', err)
          return { data: [] }
        }),
        investmentApi.getSummary().catch(err => {
          console.error('Failed to load investment summary:', err)
          return { data: { total_principal: 0, total_income: 0, active_count: 0, investments: [] } }
        })
      ])
      
      equity.value = equityRes.data
      
      // 获取最新余额
      if (transactionRes.data && transactionRes.data.length > 0) {
        balance.value = transactionRes.data[0].balance_after || 0
      }
      
      // 投资汇总
      investmentSummary.value = investmentRes.data
    } catch (err) {
      console.error('Error loading dashboard data:', err)
      // 即使数据加载失败，仍然保持hasFamily=true，显示空状态
    }
  } catch (err) {
    console.error('Error loading user info:', err)
    hasFamily.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
/* 页面头部行 */
.page-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header-row .page-title {
  margin-bottom: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ai-chat-btn {
  font-weight: 500;
}

.privacy-toggle {
  background: none;
  border: 1px solid var(--theme-border);
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.privacy-toggle:hover {
  background: var(--theme-border-light);
  border-color: var(--theme-border);
}

.privacy-toggle:active {
  transform: scale(0.95);
}

.privacy-icon {
  width: 20px;
  height: 20px;
  color: var(--theme-text-secondary);
}

.privacy-toggle:hover .privacy-icon {
  color: var(--theme-text-primary);
}

/* 个人信息区域 */
.profile-section {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: linear-gradient(135deg, var(--theme-bg-card) 0%, var(--theme-bg-secondary) 100%);
  border-radius: 16px;
  margin-bottom: 24px;
  border: 1px solid var(--theme-border);
}

.profile-avatar {
  background: linear-gradient(135deg, var(--theme-success) 0%, var(--theme-success-dark) 100%);
  color: white;
  font-weight: 600;
  font-size: 18px;
  flex-shrink: 0;
}

.profile-info {
  flex: 1;
  min-width: 0;
}

.profile-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--theme-text-primary);
  margin-bottom: 6px;
}

.profile-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.profile-greeting {
  font-size: 14px;
  color: var(--theme-text-secondary);
}

/* 资金概览 */
.assets-overview {
  margin-bottom: 24px;
  background: var(--theme-success-bg);
  border: 1px solid var(--theme-success);
}

.assets-overview {
  margin-bottom: 16px;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--theme-success);
}

.overview-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--theme-text-primary);
  margin: 0;
}

.assets-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

@media (max-width: 768px) {
  .assets-grid {
    grid-template-columns: 1fr;
  }
}

.asset-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: var(--theme-bg-card);
  border-radius: 10px;
  border: 1px solid var(--theme-border-light);
  transition: all 0.3s;
}

.asset-card.clickable {
  cursor: pointer;
}

.asset-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
}

.asset-card.clickable:hover {
  border-color: var(--theme-success);
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.25);
}

.asset-card.primary-card {
  background: linear-gradient(135deg, var(--theme-success) 0%, #0c7a43 100%);
  border: none;
}

.asset-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.primary-card .asset-icon {
  font-size: 40px;
}

.asset-content {
  flex: 1;
  min-width: 0;
}

.asset-label {
  font-size: 13px;
  color: var(--theme-text-secondary);
  margin-bottom: 4px;
}

.primary-card .asset-label {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
}

.asset-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--theme-text-primary);
  margin-bottom: 2px;
}

.primary-card .asset-value {
  font-size: 32px;
  color: white;
}

.asset-detail {
  font-size: 12px;
  color: var(--theme-text-tertiary);
}

.primary-card .asset-detail {
  color: rgba(255, 255, 255, 0.8);
}

/* 资金总览 */
.assets-summary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  background: var(--theme-bg-card);
  border-radius: 12px;
  border: 1px solid var(--theme-border-light);
  margin-top: 16px;
  flex-wrap: wrap;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 0;
  flex-shrink: 1;
}

.summary-label {
  font-size: 11px;
  color: var(--theme-text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.summary-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--theme-text-primary);
  white-space: nowrap;
}

.summary-divider {
  font-size: 18px;
  color: var(--theme-text-tertiary);
  font-weight: 600;
  padding: 0 4px;
  flex-shrink: 0;
}

.frozen-amount-notice {
  margin-top: 12px;
}

.frozen-amount-notice :deep(.n-alert) {
  background: var(--theme-info-light);
  border-radius: 8px;
}

/* 股权与储蓄区域 */
.equity-savings-section {
  margin-bottom: 24px;
}

.positive-value {
  color: var(--theme-success) !important;
}

.negative-value {
  color: var(--theme-error) !important;
}

.asset-distribution {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed var(--theme-warning);
}

.distribution-bar {
  height: 32px;
  background: var(--theme-bg-secondary);
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  margin-bottom: 12px;
}

.bar-segment {
  height: 100%;
  transition: width 0.5s ease;
  cursor: pointer;
}

.balance-segment {
  background: var(--theme-success);
}

.investment-segment {
  background: var(--theme-info);
}

.distribution-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  font-size: 13px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--theme-text-secondary);
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.balance-dot {
  background: var(--theme-success);
}

.investment-dot {
  background: var(--theme-info);
}

.target-card {
  background: var(--theme-warning-bg);
  border: 1px solid var(--theme-warning);
  margin-bottom: 16px;
}

.target-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.target-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--theme-text-primary);
  margin: 0;
}

.target-amounts {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 12px;
  justify-content: center;
}

.current-amount {
  font-size: 24px;
  font-weight: 700;
  color: var(--theme-success);
}

.amount-separator {
  font-size: 16px;
  color: var(--theme-text-primary);
  margin: 0 4px;
}

.target-amount-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--theme-text-secondary);
}

.expand-btn {
  color: var(--theme-text-primary);
  font-size: 12px;
  font-weight: 500;
}

/* 简化进度条 */
.progress-wrapper {
  position: relative;
  margin: 12px 0;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  pointer-events: none;
  z-index: 2;
}

.remaining-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 14px;
  background: var(--theme-bg-secondary);
  border-radius: 8px;
  border-left: 3px solid var(--theme-warning);
}

.tip-icon {
  font-size: 16px;
}

.tip-text {
  font-size: 13px;
  color: var(--theme-text-primary);
  font-weight: 600;
}

.remaining-amount {
  font-size: 16px;
  font-weight: 700;
  color: var(--theme-warning);
  margin-left: auto;
}

.help-content {
  margin-top: 12px;
  padding: 16px;
  background: var(--theme-bg-secondary);
  border-radius: 8px;
  border: 1px dashed var(--theme-warning);
}

.help-content p {
  margin: 0 0 8px 0;
  color: var(--theme-text-primary);
  font-size: 13px;
}

.help-content ul {
  margin: 0;
  padding-left: 20px;
  color: var(--theme-text-primary);
  font-size: 13px;
  line-height: 1.8;
}

.help-content li {
  margin-bottom: 4px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  font-size: 32px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--theme-text-primary);
}

.stat-label {
  font-size: 13px;
  color: var(--theme-text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.growth-value {
  color: var(--theme-success);
}

.help-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  font-size: 11px;
  font-weight: 600;
  background: var(--theme-border);
  color: var(--theme-text-secondary);
  border-radius: 50%;
  cursor: help;
}

/* 股权分布卡片 */
.equity-card {
  background: var(--theme-info-bg);
  border: 1px solid var(--theme-purple);
  margin-bottom: 16px;
}

.equity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--theme-purple);
}

.equity-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--theme-text-primary);
  margin: 0;
}

.equity-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.equity-chart-wrapper {
  position: relative;
  width: 100%;
}

.equity-chart {
  width: 100%;
  min-height: 260px;
  position: relative;
}

.avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
}

.avatar-label {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  pointer-events: auto;
}

.avatar-label :deep(.user-avatar) {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border: 2px solid #fff;
}

.avatar-percent {
  font-size: 14px;
  font-weight: 600;
  color: var(--theme-text-primary);
  background: var(--theme-card-bg);
  padding: 2px 8px;
  border-radius: 10px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  white-space: nowrap;
}

.equity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--theme-border);
}

.equity-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px;
  background: var(--theme-bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--theme-border-light);
  transition: all 0.3s ease;
}

.equity-item:hover {
  background: var(--theme-bg-card);
  border-color: var(--theme-purple);
  transform: translateX(4px);
  box-shadow: 0 2px 8px var(--theme-shadow-sm);
}

.member-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 140px;
  flex-shrink: 0;
}

.member-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.member-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--theme-text-primary);
}

.member-deposit {
  font-size: 12px;
  color: var(--theme-text-secondary);
}

.member-equity {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.equity-bar-wrapper {
  flex: 1;
  min-width: 80px;
}

.equity-value {
  font-weight: 700;
  font-size: 16px;
  color: var(--theme-purple);
  min-width: 55px;
  text-align: right;
  flex-shrink: 0;
}

.welcome-card {
  padding: 48px;
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* ============================================
   移动端适配
   ============================================ */
@media (max-width: 767px) {
  /* 资金概览移动端 */
  .assets-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .asset-value {
    font-size: 20px;
  }
  
  .primary-card .asset-value {
    font-size: 26px;
  }
  
  .asset-icon {
    font-size: 28px;
  }
  
  .primary-card .asset-icon {
    font-size: 36px;
  }

  /* 资金总览移动端 - 更紧凑 */
  .assets-summary {
    gap: 4px;
    padding: 10px 8px;
  }

  .summary-label {
    font-size: 10px;
  }

  .summary-value {
    font-size: 14px;
  }

  .summary-divider {
    font-size: 16px;
    padding: 0 2px;
  }
  
  /* 个人信息区域移动端 */
  .profile-section {
    padding: 12px 16px;
    margin-bottom: 16px;
    gap: 12px;
  }
  
  .profile-avatar {
    width: 40px !important;
    height: 40px !important;
    font-size: 16px !important;
  }
  
  .profile-name {
    font-size: 16px;
    margin-bottom: 4px;
  }
  
  .profile-meta {
    gap: 8px;
  }
  
  .profile-greeting {
    font-size: 13px;
  }
  
  .target-card {
    margin-bottom: 16px;
  }
  
  .target-header {
    flex-direction: row;
    align-items: center;
  }
  
  .target-title {
    font-size: 15px;
  }
  
  .target-amounts {
    flex-wrap: wrap;
  }
  
  .current-amount {
    font-size: 20px;
  }
  
  .target-amount-value {
    font-size: 16px;
  }
  
  .remaining-tip {
    padding: 8px 12px;
    font-size: 12px;
  }
  
  .remaining-amount {
    font-size: 14px;
  }
  
  /* 数据卡片 2列 */
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }
  
  .stat-card {
    padding: 12px;
  }
  
  .stat-icon {
    font-size: 24px;
  }
  
  .stat-value {
    font-size: 16px;
  }
  
  .stat-label {
    font-size: 12px;
  }
  
  /* 股权内容移动端 */
  .equity-chart {
    min-height: 280px;
  }
  
  /* 股权列表移动端 */
  .equity-item {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    padding: 12px;
  }
  
  .equity-item:hover {
    transform: none;
  }
  
  .member-info {
    min-width: unset;
    justify-content: flex-start;
  }
  
  .member-details {
    flex: 1;
  }
  
  .member-name {
    font-size: 15px;
  }
  
  .member-deposit {
    font-size: 13px;
  }
  
  .member-equity {
    width: 100%;
  }
  
  .equity-bar-wrapper {
    min-width: 0;
  }
  
  .equity-value {
    font-size: 15px;
    min-width: 50px;
  }
  
  .welcome-card {
    padding: 24px;
  }
}

/* Transition 动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
