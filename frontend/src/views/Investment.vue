<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">📈</span> 理财配置</h1>
    
    <n-card class="card-hover" style="margin-bottom: 24px">
      <n-form inline :model="formData">
        <n-form-item label="产品名称">
          <n-input v-model:value="formData.name" placeholder="如：货币基金" style="width: 150px" />
        </n-form-item>
        <n-form-item label="理财类型">
          <n-select v-model:value="formData.investment_type" :options="typeOptions" style="width: 120px" />
        </n-form-item>
        <n-form-item label="投资本金">
          <n-input-number v-model:value="formData.principal" :min="1" placeholder="金额" style="width: 120px">
            <template #prefix>¥</template>
          </n-input-number>
        </n-form-item>
        <n-form-item label="预期年化">
          <n-input-number v-model:value="formData.expected_rate" :min="0" :max="100" placeholder="%" style="width: 100px">
            <template #suffix>%</template>
          </n-input-number>
        </n-form-item>
        <n-form-item>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">添加</n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <n-card title="理财产品列表" class="card-hover">
      <n-data-table :columns="columns" :data="investments" :loading="loading" :bordered="false" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useMessage, NButton, NTag } from 'naive-ui'
import { investmentApi } from '@/api'
import dayjs from 'dayjs'

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const investments = ref<any[]>([])
const formData = ref({ 
  name: '', 
  investment_type: 'fund' as 'fund' | 'stock' | 'bond' | 'deposit' | 'other',
  principal: null as number | null, 
  expected_rate: null as number | null 
})

const typeOptions = [
  { label: '基金', value: 'fund' },
  { label: '股票', value: 'stock' },
  { label: '债券', value: 'bond' },
  { label: '存款', value: 'deposit' },
  { label: '其他', value: 'other' }
]

const typeLabels: Record<string, string> = {
  fund: '基金',
  stock: '股票',
  bond: '债券',
  deposit: '存款',
  other: '其他'
}

const columns = [
  { title: '产品名称', key: 'name' },
  { title: '类型', key: 'investment_type', render: (row: any) => typeLabels[row.investment_type] || row.investment_type },
  { title: '投资本金', key: 'principal', render: (row: any) => `¥${row.principal.toLocaleString()}` },
  { title: '预期年化', key: 'expected_rate', render: (row: any) => `${(row.expected_rate * 100).toFixed(2)}%` },
  { title: '累计收益', key: 'total_income', render: (row: any) => h('span', { style: { color: (row.total_income || 0) >= 0 ? '#10b981' : '#ef4444' } }, `¥${(row.total_income || 0).toLocaleString()}`) },
  { title: '状态', key: 'is_active', render: (row: any) => h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, { default: () => row.is_active ? '持有中' : '已结束' }) },
  { title: '开始日期', key: 'start_date', render: (row: any) => dayjs(row.start_date).format('YYYY-MM-DD') },
  { 
    title: '操作', 
    key: 'actions',
    render: (row: any) => h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => addIncome(row.id) }, { default: () => '登记收益' })
  }
]

async function loadData() {
  loading.value = true
  try {
    const res = await investmentApi.list()
    investments.value = res.data
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!formData.value.name || !formData.value.principal) { message.warning('请填写完整信息'); return }
  submitting.value = true
  try {
    await investmentApi.create({
      name: formData.value.name,
      investment_type: formData.value.investment_type,
      principal: formData.value.principal,
      expected_rate: (formData.value.expected_rate || 0) / 100,
      start_date: new Date().toISOString()
    })
    message.success('添加成功！📈')
    formData.value = { name: '', investment_type: 'fund', principal: null, expected_rate: null }
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function addIncome(id: number) {
  const amount = window.prompt('请输入本次收益金额（可为负数）')
  if (amount === null) return
  try {
    await investmentApi.addIncome(id, { 
      amount: parseFloat(amount),
      income_date: new Date().toISOString()
    })
    message.success('收益登记成功！')
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(loadData)
</script>