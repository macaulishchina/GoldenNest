<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">📝</span> 资金流水</h1>
    
    <n-card class="card-hover">
      <n-data-table :columns="columns" :data="transactions" :loading="loading" :bordered="false" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NTag } from 'naive-ui'
import { transactionApi } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const transactions = ref<any[]>([])

const typeMap: Record<string, { color: string, label: string }> = {
  deposit: { color: '#10b981', label: '存入' },
  withdrawal: { color: '#ef4444', label: '支出' },
  investment_return: { color: '#3b82f6', label: '理财收益' },
  dividend: { color: '#8b5cf6', label: '分红' }
}

const columns = [
  { title: '日期', key: 'created_at', render: (row: any) => dayjs(row.created_at).format('YYYY-MM-DD HH:mm') },
  { title: '类型', key: 'type', render: (row: any) => h(NTag, { size: 'small', bordered: false, style: { backgroundColor: typeMap[row.type]?.color + '20', color: typeMap[row.type]?.color } }, { default: () => typeMap[row.type]?.label || row.type }) },
  { title: '金额', key: 'amount', render: (row: any) => {
    const isPositive = row.amount > 0
    return h('span', { style: { color: isPositive ? '#10b981' : '#ef4444', fontWeight: 600 } }, `${isPositive ? '+' : ''}¥${row.amount.toLocaleString()}`)
  }},
  { title: '操作人', key: 'user_nickname' },
  { title: '说明', key: 'description', render: (row: any) => row.description || '-' }
]

async function loadData() {
  loading.value = true
  try {
    const res = await transactionApi.list()
    transactions.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
