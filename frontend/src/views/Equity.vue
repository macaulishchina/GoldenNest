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
            <span class="label">加权总额</span>
            <span class="value">¥{{ formatNumber(equity.total_weighted) }}</span>
          </div>
          <div class="summary-item">
            <span class="label">时间加权利率</span>
            <span class="value">{{ ((equity.time_value_rate || 0) * 100).toFixed(1) }}%</span>
          </div>
        </div>
      </n-card>
      
      <n-card title="成员股权详情" class="card-hover" style="margin-top: 24px">
        <n-data-table :columns="columns" :data="equity?.members || []" :bordered="false" />
      </n-card>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NProgress, NAvatar } from 'naive-ui'
import { equityApi } from '@/api'

const loading = ref(false)
const equity = ref<any>(null)

const formatNumber = (num: number) => num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const columns = [
  { 
    title: '成员', 
    key: 'nickname',
    render: (row: any) => h('div', { style: 'display:flex;align-items:center;gap:8px' }, [
      h(NAvatar, { round: true, size: 'small' }, { default: () => row.nickname[0] }),
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
.equity-summary { display: flex; gap: 48px; }
.summary-item { display: flex; flex-direction: column; }
.summary-item .label { font-size: 13px; color: #64748b; }
.summary-item .value { font-size: 24px; font-weight: 600; color: #1e293b; }
</style>
