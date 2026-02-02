<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">📈</span> 理财配置</h1>
    
    <n-card class="card-hover" style="margin-bottom: 24px">
      <n-form inline :model="formData">
        <n-form-item label="产品名称">
          <n-input v-model:value="formData.name" placeholder="如：货币基金" style="width: 150px" />
        </n-form-item>
        <n-form-item label="投资金额">
          <n-input-number v-model:value="formData.amount" :min="1" placeholder="金额" style="width: 120px">
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
const formData = ref({ name: '', amount: null as number | null, expected_rate: null as number | null })

const columns = [
  { title: '产品名称', key: 'name' },
  { title: '投资金额', key: 'amount', render: (row: any) => `¥${row.amount.toLocaleString()}` },
  { title: '预期年化', key: 'expected_rate', render: (row: any) => `${(row.expected_rate * 100).toFixed(2)}%` },
  { title: '实际收益', key: 'actual_return', render: (row: any) => h('span', { style: { color: row.actual_return >= 0 ? '#10b981' : '#ef4444' } }, `¥${row.actual_return.toLocaleString()}`) },
  { title: '状态', key: 'status', render: (row: any) => h(NTag, { type: row.status === 'active' ? 'success' : 'default', size: 'small' }, { default: () => row.status === 'active' ? '持有中' : '已结束' }) },
  { title: '开始日期', key: 'start_date', render: (row: any) => dayjs(row.start_date).format('YYYY-MM-DD') },
  { 
    title: '操作', 
    key: 'actions',
    render: (row: any) => h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => registerReturn(row.id) }, { default: () => '登记收益' })
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
  if (!formData.value.name || !formData.value.amount) { message.warning('请填写完整信息'); return }
  submitting.value = true
  try {
    await investmentApi.create({
      name: formData.value.name,
      amount: formData.value.amount,
      expected_rate: (formData.value.expected_rate || 0) / 100,
      start_date: new Date().toISOString()
    })
    message.success('添加成功！📈')
    formData.value = { name: '', amount: null, expected_rate: null }
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function registerReturn(id: number) {
  const amount = window.prompt('请输入本次收益金额（可为负数）')
  if (amount === null) return
  try {
    await investmentApi.registerReturn(id, parseFloat(amount))
    message.success('收益登记成功！')
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(loadData)
</script>
