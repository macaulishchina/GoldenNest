<template>
  <div class="page-container">
    <div class="page-header-row">
      <h1 class="page-title">
        <span class="icon">📊</span>
        仪表盘
      </h1>
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
    
    <template v-if="hasFamily">
      <!-- 储蓄目标 -->
      <n-card class="target-card card-hover">
        <div class="target-header">
          <div>
            <h2 class="target-title">🎯 储蓄目标</h2>
            <p class="target-subtitle">当前储蓄：¥{{ formatNumber(equity?.total_savings || 0) }} / ¥{{ formatNumber(equity?.savings_target || 2000000) }}</p>
          </div>
        </div>
        <n-progress 
          type="line" 
          :percentage="Math.min(((equity?.total_savings || 0) / (equity?.savings_target || 2000000)) * 100, 100)"
          :height="24"
          :border-radius="12"
          :fill-border-radius="12"
          indicator-placement="inside"
          color="#10b981"
          rail-color="#e2e8f0"
        />
        <div class="target-tips">
          💡 再存 <strong>¥{{ formatNumber(Math.max(0, (equity?.savings_target || 2000000) - (equity?.total_savings || 0))) }}</strong> 就达成目标！
          <n-button text @click="showSavingsHelp = !showSavingsHelp" style="margin-left: 8px;">
            <template #icon>
              <span style="font-size: 14px;">📚</span>
            </template>
            {{ showSavingsHelp ? '隐藏说明' : '查看说明' }}
          </n-button>
        </div>
        <Transition name="fade-slide">
          <div v-show="showSavingsHelp" class="help-content">
            <p><strong>📊 储蓄说明：</strong></p>
            <ul>
              <li>储蓄金额 = 所有家庭成员的“资金注入”总额</li>
              <li>不包含理财收益，只计算实际注入的本金</li>
              <li>通过“资金注入”页面增加家庭储蓄</li>
            </ul>
          </div>
        </Transition>
      </n-card>
      
      <!-- 家庭资金池 -->
      <n-card class="assets-overview card-hover">
        <div class="overview-header">
          <div>
            <h2 class="overview-title">💰 家庭资金池</h2>
            <p class="overview-subtitle">所有家庭成员共同管理的资金</p>
          </div>
          <div class="overview-date">{{ new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' }) }}</div>
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
          <div class="asset-card">
            <div class="asset-icon">📊</div>
            <div class="asset-content">
              <div class="asset-label">投资资产</div>
              <div class="asset-value">¥{{ formatNumber(investmentTotal) }}</div>
              <div class="asset-detail">
                {{ investmentSummary?.active_count || 0 }} 个理财产品
              </div>
            </div>
          </div>
          
          <!-- 投资收益 -->
          <div class="asset-card">
            <div class="asset-icon">💎</div>
            <div class="asset-content">
              <div class="asset-label">投资收益</div>
              <div class="asset-value" :class="investmentIncome >= 0 ? 'positive-value' : 'negative-value'">
                {{ investmentIncome >= 0 ? '+' : '' }}¥{{ formatNumber(investmentIncome) }}
              </div>
              <div class="asset-detail">
                回报率: {{ investmentROI }}%
              </div>
            </div>
          </div>
        </div>
        
        <!-- 资金总览 -->
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
        </div>
      </n-card>
      
      <!-- 股权与储蓄 -->
      <div class="equity-savings-section">
        <!-- 股权分布 -->
        <n-card class="equity-card card-hover">
        <div class="equity-header">
          <div>
            <h2 class="equity-title">👥 股权分布</h2>
            <p class="equity-subtitle">根据储蓄金额计算，{{ equity?.members?.length || 0 }} 位成员</p>
          </div>
        </div>
        <div class="equity-list">
          <div v-for="member in equity?.members" :key="member.user_id" class="equity-item">
            <div class="member-info">
              <UserAvatar :userId="member.user_id" :name="member.nickname" :avatarVersion="member.avatar_version" :size="28" />
              <span class="member-name">{{ member.nickname }}</span>
            </div>
            <div class="member-deposit">
              <span class="deposit-label">存入:</span>
              <span>¥{{ formatNumber(member.total_deposit || 0) }}</span>
            </div>
            <div class="member-equity">
              <n-progress 
                type="line"
                :percentage="member.equity_percentage || 0"
                :height="8"
                :border-radius="4"
                :show-indicator="false"
                :color="getProgressColor(member.equity_percentage || 0)"
              />
              <span class="equity-value">{{ (member.equity_percentage || 0).toFixed(2) }}%</span>
            </div>
          </div>
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
import { equityApi, familyApi, transactionApi, investmentApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { usePrivacyStore } from '@/stores/privacy'
import UserAvatar from '@/components/UserAvatar.vue'

const router = useRouter()
const userStore = useUserStore()
const privacyStore = usePrivacyStore()
const { privacyMode } = storeToRefs(privacyStore)

const equity = ref<any>(null)
const hasFamily = ref(false)
const balance = ref(0) // 当前余额
const investmentSummary = ref<any>(null) // 理财汇总
const showSavingsHelp = ref(false) // 储蓄说明展开状态

// 当前用户的成员信息
const currentMember = computed(() => {
  if (!equity.value?.members || !userStore.user?.id) return null
  return equity.value.members.find((m: any) => m.user_id === userStore.user?.id)
})

// 资金统计计算
const totalAssets = computed(() => {
  // 总资产 = 余额 + 理财本金
  const investmentPrincipal = investmentSummary.value?.total_principal || 0
  return balance.value + investmentPrincipal
})

const freeBalance = computed(() => {
  // 自由资金 = 当前余额
  return balance.value
})

const investmentTotal = computed(() => {
  // 理财总额（当前持仓本金）
  return investmentSummary.value?.total_principal || 0
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
  if (percentage >= 50) return '#10b981'
  if (percentage >= 30) return '#3b82f6'
  return '#f59e0b'
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

.privacy-toggle {
  background: none;
  border: 1px solid #e2e8f0;
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
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.privacy-toggle:active {
  transform: scale(0.95);
}

.privacy-icon {
  width: 20px;
  height: 20px;
  color: #64748b;
}

.privacy-toggle:hover .privacy-icon {
  color: #334155;
}

/* 个人信息区域 */
.profile-section {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 16px;
  margin-bottom: 24px;
  border: 1px solid #e2e8f0;
}

.profile-avatar {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
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
  color: #1e293b;
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
  color: #64748b;
}

/* 资金概览 */
.assets-overview {
  margin-bottom: 24px;
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border: 1px solid #10b981;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #10b981;
}

.overview-title {
  font-size: 20px;
  font-weight: 700;
  color: #065f46;
  margin: 0 0 4px 0;
}

.overview-subtitle {
  font-size: 13px;
  color: #059669;
  margin: 0;
  opacity: 0.8;
}

.overview-date {
  font-size: 13px;
  color: #065f46;
  opacity: 0.6;
}

.assets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.asset-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  border: 1px solid #a7f3d0;
  transition: all 0.3s;
}

.asset-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
}

.asset-card.primary-card {
  grid-column: span 3;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
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
  color: #78716c;
  margin-bottom: 4px;
}

.primary-card .asset-label {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
}

.asset-value {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 2px;
}

.primary-card .asset-value {
  font-size: 32px;
  color: white;
}

.asset-detail {
  font-size: 12px;
  color: #94a3b8;
}

.primary-card .asset-detail {
  color: rgba(255, 255, 255, 0.8);
}

/* 资金总览 */
.assets-summary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  border: 1px solid #a7f3d0;
  margin-top: 16px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.summary-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}

.summary-divider {
  font-size: 20px;
  color: #94a3b8;
  font-weight: 600;
}

/* 股权与储蓄区域 */
.equity-savings-section {
  margin-bottom: 24px;
}

.positive-value {
  color: #10b981 !important;
}

.negative-value {
  color: #ef4444 !important;
}

.asset-distribution {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed #fbbf24;
}

.distribution-bar {
  height: 32px;
  background: #f5f5f5;
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
  background: linear-gradient(135deg, #10b981, #059669);
}

.investment-segment {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
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
  color: #64748b;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.balance-dot {
  background: linear-gradient(135deg, #10b981, #059669);
}

.investment-dot {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
}

.target-card {
  background: linear-gradient(135deg, #fef3c7 0%, #fef9e7 100%);
  border: 1px solid #fbbf24;
}

.target-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.target-title {
  font-size: 18px;
  font-weight: 700;
  color: #92400e;
  margin: 0 0 8px 0;
}

.target-subtitle {
  font-size: 14px;
  color: #92400e;
  margin: 0;
  opacity: 0.8;
}

.target-stats {
  display: flex;
  gap: 20px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.stat-label-small {
  font-size: 12px;
  color: #92400e;
  opacity: 0.7;
  margin-bottom: 2px;
}

.stat-value-small {
  font-size: 16px;
  font-weight: 700;
  color: #92400e;
}

.target-amount {
  text-align: right;
}

.amount-label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
}

.amount-value {
  font-size: 28px;
  font-weight: 700;
}

.target-tips {
  margin-top: 16px;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  color: #92400e;
  font-size: 13px;
  border-left: 3px solid #fbbf24;
  display: flex;
  align-items: center;
  justify-content: space-between;
  line-height: 1.6;
}

.help-content {
  margin-top: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 8px;
  border: 1px dashed #fbbf24;
}

.help-content p {
  margin: 0 0 8px 0;
  color: #92400e;
  font-size: 13px;
}

.help-content ul {
  margin: 0;
  padding-left: 20px;
  color: #92400e;
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
  color: #1e293b;
}

.stat-label {
  font-size: 13px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 4px;
}

.growth-value {
  color: #10b981;
}

.help-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  font-size: 11px;
  font-weight: 600;
  background: #e2e8f0;
  color: #64748b;
  border-radius: 50%;
  cursor: help;
}

/* 股权分布卡片 */
.equity-card {
  background: linear-gradient(135deg, #ede9fe 0%, #f5f3ff 100%);
  border: 1px solid #a78bfa;
}

.equity-header {
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #a78bfa;
}

.equity-title {
  font-size: 18px;
  font-weight: 700;
  color: #5b21b6;
  margin: 0 0 4px 0;
}

.equity-subtitle {
  font-size: 13px;
  color: #7c3aed;
  margin: 0;
  opacity: 0.8;
}

.equity-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.equity-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.member-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
}

.member-name {
  font-weight: 500;
}

.member-deposit {
  font-size: 13px;
  color: #64748b;
  min-width: 150px;
}

.deposit-label {
  margin-right: 4px;
}

.member-equity {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  max-width: 200px;
}

.equity-value {
  font-weight: 600;
  color: #10b981;
  min-width: 60px;
  text-align: right;
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
  
  .asset-card.primary-card {
    grid-column: span 1;
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
    flex-direction: column;
    gap: 12px;
  }
  
  .target-title {
    font-size: 16px;
  }
  
  .target-amount {
    text-align: left;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .amount-label {
    display: inline;
    font-size: 14px;
  }
  
  .amount-value {
    font-size: 24px;
  }
  
  .target-tips {
    margin-top: 12px;
    padding: 10px 12px;
    font-size: 13px;
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
  
  /* 股权列表移动端 */
  .equity-item {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    padding: 12px 0;
    border-bottom: 1px solid #f0f0f0;
  }
  
  .equity-item:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }
  
  .member-info {
    min-width: unset;
    justify-content: space-between;
  }
  
  .member-deposit {
    min-width: unset;
    font-size: 14px;
    color: #1e293b;
  }
  
  .member-equity {
    max-width: unset;
    width: 100%;
  }
  
  .equity-value {
    min-width: 70px;
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
