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
      <!-- 储蓄目标进度 -->
      <n-card class="target-card card-hover">
        <div class="target-header">
          <div>
            <h2 class="target-title">储蓄目标进度</h2>
            <p class="target-subtitle">目标: ¥{{ formatNumber(equity?.savings_target || 2000000) }}</p>
          </div>
          <div class="target-amount">
            <span class="amount-label">当前储蓄</span>
            <span class="amount-value gradient-text">¥{{ formatNumber(equity?.total_savings || 0) }}</span>
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
          🎯 再存 <strong>¥{{ formatNumber(Math.max(0, (equity?.savings_target || 2000000) - (equity?.total_savings || 0))) }}</strong> 就达成目标啦！
        </div>
      </n-card>
      
      <!-- 数据卡片 -->
      <div class="stats-grid">
        <n-card class="stat-card card-hover">
          <div class="stat-icon">💰</div>
          <div class="stat-content">
            <div class="stat-value">¥{{ formatNumber(equity?.total_savings || 0) }}</div>
            <div class="stat-label">总储蓄</div>
          </div>
        </n-card>
        
        <n-card class="stat-card card-hover">
          <div class="stat-icon">📈</div>
          <div class="stat-content">
            <div class="stat-value growth-value">+¥{{ formatNumber(equity?.daily_weighted_growth || 0) }}</div>
            <div class="stat-label">
              今日加权增长
              <n-tooltip trigger="hover">
                <template #trigger>
                  <span class="help-icon">?</span>
                </template>
                <div style="max-width: 220px;">
                  每日因时间流逝产生的股权加权增值。<br/>
                  公式：加权总额 × 年化利率 ÷ 365<br/>
                  存得越久，每日增长越多！
                </div>
              </n-tooltip>
            </div>
          </div>
        </n-card>
        
        <n-card class="stat-card card-hover">
          <div class="stat-icon">⏳</div>
          <div class="stat-content">
            <div class="stat-value">{{ ((equity?.time_value_rate || 0.03) * 100).toFixed(1) }}%</div>
            <div class="stat-label">时间价值系数</div>
          </div>
        </n-card>
        
        <n-card class="stat-card card-hover">
          <div class="stat-icon">👥</div>
          <div class="stat-content">
            <div class="stat-value">{{ equity?.members?.length || 0 }}</div>
            <div class="stat-label">家庭成员</div>
          </div>
        </n-card>
      </div>
      
      <!-- 股权分布 -->
      <n-card title="股权分布" class="card-hover">
        <div class="equity-list">
          <div v-for="member in equity?.members" :key="member.user_id" class="equity-item">
            <div class="member-info">
              <n-avatar round size="small">{{ member.nickname?.[0] || '?' }}</n-avatar>
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
import { equityApi, familyApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { usePrivacyStore } from '@/stores/privacy'

const router = useRouter()
const userStore = useUserStore()
const privacyStore = usePrivacyStore()
const { privacyMode } = storeToRefs(privacyStore)

const equity = ref<any>(null)
const hasFamily = ref(false)

// 当前用户的成员信息
const currentMember = computed(() => {
  if (!equity.value?.members || !userStore.user?.id) return null
  return equity.value.members.find((m: any) => m.user_id === userStore.user?.id)
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
    // 检查是否有家庭
    if (!userStore.user?.family_id) {
      hasFamily.value = false
      return
    }
    hasFamily.value = true
    
    // 加载股权数据
    const equityRes = await equityApi.getSummary()
    equity.value = equityRes.data
  } catch {
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

.target-card {
  margin-bottom: 24px;
}

.target-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.target-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 4px;
}

.target-subtitle {
  color: #64748b;
  margin: 0;
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
  background: #f0fdf4;
  border-radius: 8px;
  color: #059669;
  font-size: 14px;
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
  width: 14px;
  height: 14px;
  font-size: 10px;
  font-weight: 600;
  background: #e2e8f0;
  color: #64748b;
  border-radius: 50%;
  cursor: help;
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
</style>
