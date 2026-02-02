<template>
  <div class="page-container">
    <h1 class="page-title">
      <span class="icon">📊</span>
      仪表盘
    </h1>
    
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
            <div class="stat-value">¥{{ formatNumber(equity?.total_weighted || 0) }}</div>
            <div class="stat-label">加权总额</div>
          </div>
        </n-card>
        
        <n-card class="stat-card card-hover">
          <div class="stat-icon">💵</div>
          <div class="stat-content">
            <div class="stat-value">{{ ((equity?.equity_rate || 0.03) * 100).toFixed(1) }}%</div>
            <div class="stat-label">年化利率</div>
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { equityApi, familyApi } from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const equity = ref<any>(null)
const hasFamily = ref(false)

function formatNumber(num: number) {
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
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
</style>