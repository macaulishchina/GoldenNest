<template>
  <div class="page-container">
    <div class="page-header-row">
      <h1 class="page-title"><span class="icon">📝</span> 资金流水</h1>
      <n-button
        secondary
        type="info"
        size="small"
        @click="showAIInsights"
        :loading="aiLoading"
      >
        <template #icon>
          <span style="font-size: 16px">🤖</span>
        </template>
        AI 分析
      </n-button>
    </div>
    
    <!-- 时间范围选择器 -->
    <TimeRangeSelector v-model="timeRange" @change="loadData" />
    
    <!-- AI Insights Card -->
    <n-card v-if="aiInsights" class="card-hover ai-insights-card" style="margin-bottom: 16px">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between">
          <span>🤖 AI 消费洞察</span>
          <n-button text size="small" @click="aiInsights = null">
            关闭
          </n-button>
        </div>
      </template>
      <n-space vertical size="medium">
        <div>
          <n-text depth="3" style="font-size: 13px; display: block; margin-bottom: 8px">
            💡 分析结果
          </n-text>
          <n-text>{{ aiInsights.insight }}</n-text>
        </div>
        
        <div v-if="aiInsights.spending_tips.length > 0">
          <n-text depth="3" style="font-size: 13px; display: block; margin-bottom: 8px">
            💰 消费建议
          </n-text>
          <n-space vertical size="small">
            <n-tag
              v-for="(tip, index) in aiInsights.spending_tips"
              :key="index"
              type="warning"
              size="small"
              :bordered="false"
            >
              {{ tip }}
            </n-tag>
          </n-space>
        </div>
        
        <div v-if="aiInsights.saving_suggestions.length > 0">
          <n-text depth="3" style="font-size: 13px; display: block; margin-bottom: 8px">
            📈 储蓄策略
          </n-text>
          <n-space vertical size="small">
            <n-tag
              v-for="(suggestion, index) in aiInsights.saving_suggestions"
              :key="index"
              type="success"
              size="small"
              :bordered="false"
            >
              {{ suggestion }}
            </n-tag>
          </n-space>
        </div>
      </n-space>
    </n-card>
    
    <n-card class="card-hover">
      <!-- 桌面端：表格 -->
      <n-data-table class="desktop-only" :columns="columns" :data="transactions" :loading="loading" :bordered="false" />
      <!-- 移动端：卡片 -->
      <div class="mobile-only">
        <n-spin :show="loading">
          <div class="record-cards" v-if="transactions.length > 0">
            <div v-for="item in transactions" :key="item.id" class="record-card" :class="getCardClass(item.transaction_type)">
              <div class="record-card-header">
                <n-tag :type="getTagType(item.transaction_type)" size="small" :bordered="false">
                  {{ typeMap[item.transaction_type]?.label || item.transaction_type }}
                </n-tag>
                <span class="record-time">{{ formatShortDateTime(item.created_at) }}</span>
              </div>
              <div class="record-card-body">
                <div class="record-amount" :class="getAmountClass(item)">
                  {{ formatAmount(item.amount) }}
                </div>
                <div class="record-desc">{{ item.description || '无描述' }}</div>
              </div>
              <div class="record-card-footer">
                <span class="record-user">{{ item.user_nickname }}</span>
              </div>
            </div>
          </div>
          <n-empty v-else description="暂无交易记录" />
        </n-spin>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, computed } from 'vue'
import { NTag, useMessage } from 'naive-ui'
import { storeToRefs } from 'pinia'
import { transactionApi, transactionAiApi } from '@/api'
import { formatShortDateTime } from '@/utils/date'
import { usePrivacyStore } from '@/stores/privacy'
import TimeRangeSelector from '@/components/TimeRangeSelector.vue'

const message = useMessage()
const privacyStore = usePrivacyStore()
const { privacyMode } = storeToRefs(privacyStore)

const loading = ref(false)
const transactions = ref<any[]>([])
const timeRange = ref('month')
const aiLoading = ref(false)
const aiInsights = ref<any>(null)

// 格式化金额，支持隐私模式
const formatAmount = (amount: number) => {
  if (privacyMode.value) {
    return (amount > 0 ? '+' : '') + '¥****'
  }
  return (amount > 0 ? '+' : '') + '¥' + amount.toLocaleString()
}

const typeMap: Record<string, { color: string, label: string }> = {
  deposit: { color: 'var(--theme-success)', label: '存入' },
  withdraw: { color: 'var(--theme-error)', label: '支出' },
  income: { color: 'var(--theme-info)', label: '理财收益' },
  dividend: { color: 'var(--theme-purple)', label: '分红' },
  investment_buy: { color: 'var(--theme-warning)', label: '投资买入' },
  investment_redeem: { color: 'var(--theme-success)', label: '投资赎回' },
  freeze: { color: 'var(--theme-border)', label: '冻结' },
  unfreeze: { color: 'var(--theme-border)', label: '解冻' }
}

const columns = computed(() => [
  { title: '日期', key: 'created_at', render: (row: any) => formatShortDateTime(row.created_at) },
  { title: '类型', key: 'transaction_type', render: (row: any) => h(NTag, { size: 'small', bordered: false, style: { backgroundColor: typeMap[row.transaction_type]?.color + '20', color: typeMap[row.transaction_type]?.color } }, { default: () => typeMap[row.transaction_type]?.label || row.transaction_type }) },
  { title: '金额', key: 'amount', render: (row: any) => {
    // 投资买入使用中性色，其他根据正负判断
    let color = 'var(--theme-text-primary)'
    if (row.transaction_type === 'investment_buy') {
      color = 'var(--theme-warning)'
    } else {
      color = row.amount > 0 ? 'var(--theme-success)' : 'var(--theme-error)'
    }
    return h('span', { style: { color: color, fontWeight: 600 } }, formatAmount(row.amount))
  }},
  { title: '操作人', key: 'user_nickname' },
  { title: '说明', key: 'description', render: (row: any) => row.description || '-' }
])

// 获取卡片类名
function getCardClass(type: string) {
  const classMap: Record<string, string> = {
    deposit: 'deposit-card',
    withdraw: 'withdraw-card',
    income: 'income-card',
    dividend: 'dividend-card',
    investment_buy: 'investment-card',
    investment_redeem: 'deposit-card'
  }
  return classMap[type] || ''
}

// 获取金额样式类
function getAmountClass(item: any) {
  // 投资买入使用中性色，不算作支出
  if (item.transaction_type === 'investment_buy') {
    return 'neutral'
  }
  return item.amount > 0 ? 'positive' : 'negative'
}

// 获取标签类型
function getTagType(type: string) {
  const tagMap: Record<string, 'success' | 'error' | 'info' | 'warning'> = {
    deposit: 'success',
    withdraw: 'error',
    income: 'info',
    dividend: 'warning',
    investment_buy: 'warning',
    investment_redeem: 'success',
    freeze: 'default',
    unfreeze: 'default'
  }
  return tagMap[type] || 'default'
}

async function loadData() {
  loading.value = true
  try {
    const res = await transactionApi.list({ time_range: timeRange.value })
    transactions.value = res.data
  } finally {
    loading.value = false
  }
}

async function showAIInsights() {
  aiLoading.value = true
  try {
    const res = await transactionAiApi.analyze({ time_range: timeRange.value })
    aiInsights.value = res.data
    message.success('AI 分析完成')
  } catch (error: any) {
    message.error(error.response?.data?.detail || 'AI 分析失败')
  } finally {
    aiLoading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
/* Page Header */
.page-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header-row .page-title {
  margin-bottom: 0;
}

/* AI Insights Card */
.ai-insights-card :deep(.n-card-header) {
  padding: 14px 18px;
  font-weight: 600;
}

.ai-insights-card :deep(.n-card__content) {
  padding: 16px 18px;
}

/* 桌面/移动端显示控制 */
.desktop-only {
  display: block;
}
.mobile-only {
  display: none;
}

/* ===== 移动端卡片样式 ===== */
@media (max-width: 767px) {
  .desktop-only {
    display: none !important;
  }
  .mobile-only {
    display: block !important;
  }
  
  .page-container {
    padding: 12px;
  }
  
  .page-header-row {
    flex-direction: row;
    gap: 12px;
  }
  
  .page-header-row .page-title {
    font-size: 20px;
  }
  
  :deep(.n-card-header) {
    padding: 12px 14px !important;
  }
  
  :deep(.n-card__content) {
    padding: 12px 14px !important;
  }
}

.record-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.record-card {
  background: var(--theme-bg-card);
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 2px 8px var(--theme-shadow-sm);
  border: 1px solid var(--theme-border-light);
}

/* 各类型卡片颜色 */
.record-card.deposit-card {
  background: var(--theme-success-bg);
  border-color: var(--theme-success-light);
}

.record-card.withdraw-card {
  background: var(--theme-error-bg);
  border-color: var(--theme-error-light);
}

.record-card.income-card {
  background: var(--theme-info-bg);
  border-color: var(--theme-info-light);
}

.record-card.dividend-card {
  background: var(--theme-info-bg);
  border-color: var(--theme-purple-light);
}

.record-card.investment-card {
  background: var(--theme-warning-bg);
  border-color: var(--theme-warning-light);
}

.record-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.record-time {
  font-size: 11px;
  color: var(--theme-text-tertiary);
}

.record-card-body {
  margin-bottom: 8px;
}

.record-amount {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 2px;
}

.record-amount.positive {
  color: var(--theme-success);
}

.record-amount.negative {
  color: var(--theme-error);
}

.record-amount.neutral {
  color: var(--theme-warning);
}

.record-desc {
  font-size: 12px;
  color: var(--theme-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.record-card-footer {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid var(--theme-border-light);
}

.record-user {
  font-size: 12px;
  color: var(--theme-text-secondary);
}
</style>