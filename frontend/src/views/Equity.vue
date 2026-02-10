<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">📊</span> 股权结构</h1>
    <n-spin :show="loading">
      <!-- 概览卡片 -->
      <n-card v-if="equity" class="card-hover equity-overview-card">
        <div class="equity-summary">
          <div class="summary-item">
            <span class="label">总储蓄</span>
            <span class="value">¥{{ formatNumber(equity.total_savings) }}</span>
          </div>
          <div class="summary-item">
            <span class="label">成员人数</span>
            <span class="value">{{ equity.members?.length || 0 }}人</span>
          </div>
        </div>
      </n-card>
      
      <!-- 饼图可视化 -->
      <n-card v-if="equity?.members?.length" class="card-hover equity-chart-card" style="margin-top: 24px">
        <h3 class="card-subtitle">📊 股权占比分布</h3>
        <div class="chart-wrapper">
          <v-chart :option="equityChartOption" :autoresize="true" style="height: 320px;" />
        </div>
      </n-card>
      
      <!-- 成员详情 -->
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
                  <span class="percentage-value">{{ member.equity_percentage.toFixed(1) }}%</span>
                </div>
              </div>
              <div class="member-card-body">
                <div class="member-progress">
                  <n-progress 
                    type="line" 
                    :percentage="member.equity_percentage" 
                    :height="12" 
                    :border-radius="6" 
                    :show-indicator="false" 
                    color="var(--theme-success)"
                    rail-color="var(--theme-border-light)"
                  />
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
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, PieChart, TitleComponent, TooltipComponent, LegendComponent])

const privacyStore = usePrivacyStore()
const { privacyMode } = storeToRefs(privacyStore)

const loading = ref(false)
const equity = ref<any>(null)

const formatNumber = (num: number) => privacyStore.formatMoney(num)

// 饼图配置
const equityChartOption = computed(() => {
  if (!equity.value?.members) return {}
  
  const colors = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899']
  
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}% ({d}%)',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: 'transparent',
      textStyle: { color: '#fff' }
    },
    legend: {
      orient: 'horizontal',
      bottom: '5%',
      textStyle: {
        color: 'var(--theme-text-primary)',
        fontSize: 13
      }
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 10,
          borderColor: 'var(--theme-bg-card)',
          borderWidth: 3
        },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}\n{d}%',
          fontSize: 13,
          color: 'var(--theme-text-primary)',
          fontWeight: 600
        },
        labelLine: {
          show: true,
          length: 15,
          length2: 10,
          smooth: true
        },
        data: equity.value.members.map((member: any, index: number) => ({
          value: member.equity_percentage.toFixed(2),
          name: member.nickname,
          itemStyle: {
            color: colors[index % colors.length]
          }
        }))
      }
    ]
  }
})

const columns = [
  { 
    title: '成员', 
    key: 'nickname',
    render: (row: any) => h('div', { style: 'display:flex;align-items:center;gap:10px' }, [
      h(UserAvatar, { userId: row.user_id, name: row.nickname, avatarVersion: row.avatar_version, size: 32 }),
      h('span', { style: 'font-weight:600;font-size:14px' }, row.nickname)
    ])
  },
  { 
    title: '原始存入', 
    key: 'total_deposit', 
    render: (row: any) => h('span', { style: 'font-weight:600' }, `¥${formatNumber(row.total_deposit)}`) 
  },
  { 
    title: '加权金额', 
    key: 'weighted_deposit', 
    render: (row: any) => h('span', { style: 'font-weight:600' }, `¥${formatNumber(row.weighted_deposit)}`) 
  },
  { 
    title: '股权占比', 
    key: 'equity_percentage',
    render: (row: any) => h('div', { style: 'display:flex;align-items:center;gap:14px;min-width:180px' }, [
      h(NProgress, { 
        type: 'line', 
        percentage: row.equity_percentage, 
        height: 12, 
        borderRadius: 6, 
        showIndicator: false, 
        color: 'var(--theme-success)',
        railColor: 'var(--theme-border-light)'
      }),
      h('span', { style: 'font-weight:700;font-size:16px;color:var(--theme-success);min-width:55px;text-align:right' }, `${row.equity_percentage.toFixed(1)}%`)
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

.equity-summary {
  display: flex;
  gap: 48px;
  justify-content: center;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-item .label {
  font-size: 13px;
  color: var(--theme-text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.summary-item .value {
  font-size: 24px;
  font-weight: 700;
  color: var(--theme-text-primary);
}

.summary-item .value.growth {
  color: var(--theme-success);
}

.help-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  font-size: 10px;
  font-weight: 600;
  background: var(--theme-border);
  color: var(--theme-text-secondary);
  border-radius: 50%;
  cursor: help;
  transition: all 0.2s;
}

.help-icon:hover {
  background: var(--theme-primary);
  color: white;
}

.card-subtitle {
  font-size: 16px;
  font-weight: 700;
  color: var(--theme-text-primary);
  margin: 0 0 16px 0;
}

.chart-wrapper {
  width: 100%;
  min-height: 320px;
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
  
  /* 股权概览布局 */
  .equity-summary {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
  
  .summary-item {
    background: var(--theme-bg-secondary);
    padding: 16px;
    border-radius: 12px;
    border: 1px solid var(--theme-border-light);
  }
  
  .summary-item .label {
    font-size: 13px;
    margin-bottom: 6px;
  }
  
  .summary-item .value {
    font-size: 22px;
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
  gap: 14px;
}

.member-card {
  background: var(--theme-bg-card);
  border-radius: 14px;
  padding: 16px;
  border: 1px solid var(--theme-border);
  box-shadow: 0 2px 12px var(--theme-shadow-sm);
  transition: all 0.3s ease;
}

.member-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px var(--theme-shadow);
  border-color: var(--theme-success);
}

.member-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.member-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.member-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--theme-text-primary);
}

.member-percentage .percentage-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--theme-success);
}

.member-card-body {
  /* body container */
}

.member-progress {
  margin-bottom: 14px;
}

.member-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  background: var(--theme-bg-secondary);
  border-radius: 10px;
  padding: 12px;
  border: 1px solid var(--theme-border-light);
}

.member-stats .stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.member-stats .stat-label {
  font-size: 12px;
  color: var(--theme-text-secondary);
  font-weight: 500;
}

.member-stats .stat-value {
  font-size: 15px;
  font-weight: 700;
  color: var(--theme-text-primary);
}
</style>