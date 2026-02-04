<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">📊</span> 股权结构</h1>
    <n-spin :show="loading">
      <n-card v-if="equity" class="card-hover">
        <div class="equity-summary">
          <div class="summary-item">
            <span class="label">总储蓄</span>
            <span class="value">¥{{ formatNumber(equity.total_savings) }}</span>
          </div>
          <div class="summary-item">
            <span class="label">
              今日增长
              <n-tooltip trigger="hover">
                <template #trigger>
                  <span class="help-icon">?</span>
                </template>
                <div style="max-width: 200px;">
                  每日因时间流逝产生的股权增值<br/>
                  公式：加权总额 × 利率 ÷ 365
                </div>
              </n-tooltip>
            </span>
            <span class="value growth">+¥{{ formatNumber(equity.daily_weighted_growth || 0) }}</span>
          </div>
          <div class="summary-item">
            <span class="label">时间加权利率</span>
            <span class="value">{{ ((equity.time_value_rate || 0) * 100).toFixed(1) }}%</span>
          </div>
        </div>
      </n-card>
      
      <n-card title="成员股权详情" class="card-hover" style="margin-top: 24px">
        <!-- 桌面端：表格 -->
        <n-data-table class="desktop-only" :columns="columns" :data="equity?.members || []" :bordered="false" />
        <!-- 移动端：卡片 -->
        <div class="mobile-only">
          <div class="member-cards" v-if="equity?.members?.length > 0">
            <div v-for="member in equity.members" :key="member.user_id" class="member-card">
              <div class="member-card-header">
                <div class="member-info">
                  <UserAvatar :userId="member.user_id" :name="member.nickname" :avatarVersion="member.avatar_version" :size="36" />
                  <span class="member-name">{{ member.nickname }}</span>
                </div>
                <div class="member-percentage">
                  <span class="percentage-value">{{ member.equity_percentage.toFixed(2) }}%</span>
                </div>
              </div>
              <div class="member-card-body">
                <div class="member-progress">
                  <n-progress type="line" :percentage="member.equity_percentage" :height="8" :border-radius="4" :show-indicator="false" color="#10b981" />
                </div>
                <div class="member-stats">
                  <div class="stat-item">
                    <span class="stat-label">原始存入</span>
                    <span class="stat-value">¥{{ formatNumber(member.total_deposit) }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">加权金额</span>
                    <span class="stat-value">¥{{ formatNumber(member.weighted_deposit) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <n-empty v-else description="暂无成员数据" />
        </div>
      </n-card>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, computed } from 'vue'
import { NProgress } from 'naive-ui'
import { storeToRefs } from 'pinia'
import { equityApi } from '@/api'
import { usePrivacyStore } from '@/stores/privacy'
import UserAvatar from '@/components/UserAvatar.vue'
import { getAvatarColor } from '@/utils/avatar'

const privacyStore = usePrivacyStore()
const { privacyMode } = storeToRefs(privacyStore)

const loading = ref(false)
const equity = ref<any>(null)

const formatNumber = (num: number) => privacyStore.formatMoney(num)

const columns = [
  { 
    title: '成员', 
    key: 'nickname',
    render: (row: any) => h('div', { style: 'display:flex;align-items:center;gap:8px' }, [
      h(UserAvatar, { userId: row.user_id, name: row.nickname, avatarVersion: row.avatar_version, size: 28 }),
      row.nickname
    ])
  },
  { title: '原始存入', key: 'total_deposit', render: (row: any) => `¥${formatNumber(row.total_deposit)}` },
  { title: '加权金额', key: 'weighted_deposit', render: (row: any) => `¥${formatNumber(row.weighted_deposit)}` },
  { 
    title: '股权占比', 
    key: 'equity_percentage',
    render: (row: any) => h('div', { style: 'display:flex;align-items:center;gap:12px;width:150px' }, [
      h(NProgress, { type: 'line', percentage: row.equity_percentage, height: 8, borderRadius: 4, showIndicator: false, color: '#10b981' }),
      h('span', { style: 'font-weight:600;color:#10b981' }, `${row.equity_percentage.toFixed(2)}%`)
    ])
  }
]

async function loadData() {
  loading.value = true
  try {
    const res = await equityApi.getSummary()
    equity.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
/* 桌面/移动端显示控制 */
.desktop-only {
  display: block;
}
.mobile-only {
  display: none;
}

.equity-summary { display: flex; gap: 48px; }
.summary-item { display: flex; flex-direction: column; }
.summary-item .label { font-size: 13px; color: #64748b; display: flex; align-items: center; gap: 4px; }
.summary-item .value { font-size: 24px; font-weight: 600; color: #1e293b; }
.summary-item .value.growth { color: #10b981; }

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

/* 移动端响应式 */
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
  
  :deep(.n-card-header) {
    padding: 12px 14px !important;
  }
  
  :deep(.n-card__content) {
    padding: 12px 14px !important;
  }
  
  /* 股权概览 2列布局 */
  .equity-summary {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .summary-item {
    background: #f8fafc;
    padding: 12px;
    border-radius: 10px;
  }
  
  .summary-item .label {
    font-size: 12px;
    margin-bottom: 4px;
  }
  
  .summary-item .value {
    font-size: 18px;
  }
  
  /* 让第三个项目占满一行 */
  .summary-item:last-child {
    grid-column: 1 / -1;
  }
  
  /* 卡片间距 */
  :deep(.n-card) {
    margin-top: 12px !important;
  }
}

/* ===== 成员卡片样式 ===== */
.member-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.member-card {
  background: linear-gradient(135deg, rgba(240,253,244,0.9), rgba(236,252,244,0.7));
  border-radius: 12px;
  padding: 14px;
  border: 1px solid rgba(16,185,129,0.15);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.member-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.member-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.member-name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.member-percentage .percentage-value {
  font-size: 20px;
  font-weight: 700;
  color: #059669;
}

.member-card-body {
  /* body container */
}

.member-progress {
  margin-bottom: 12px;
}

.member-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  background: rgba(255,255,255,0.7);
  border-radius: 8px;
  padding: 10px;
}

.member-stats .stat-item {
  display: flex;
  flex-direction: column;
}

.member-stats .stat-label {
  font-size: 11px;
  color: #64748b;
  margin-bottom: 2px;
}

.member-stats .stat-value {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}
</style>