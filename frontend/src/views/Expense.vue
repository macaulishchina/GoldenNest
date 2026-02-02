<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">💸</span> 支出申请</h1>
    
    <n-card class="card-hover" style="margin-bottom: 24px">
      <n-form inline :model="formData">
        <n-form-item label="支出金额">
          <n-input-number v-model:value="formData.amount" :min="1" style="width: 120px">
            <template #prefix>¥</template>
          </n-input-number>
        </n-form-item>
        <n-form-item label="用途说明">
          <n-input v-model:value="formData.purpose" placeholder="请说明用途" style="width: 200px" />
        </n-form-item>
        <n-form-item label="股权扣减比例">
          <n-input-number v-model:value="formData.equity_deduction_ratio" :min="0" :max="100" style="width: 100px">
            <template #suffix>%</template>
          </n-input-number>
        </n-form-item>
        <n-form-item>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">提交申请</n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <n-card title="申请记录" class="card-hover">
      <n-data-table :columns="columns" :data="expenses" :loading="loading" :bordered="false" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useMessage, NButton, NTag, NSpace } from 'naive-ui'
import { expenseApi } from '@/api'
import { useUserStore } from '@/stores/user'
import dayjs from 'dayjs'

const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const expenses = ref<any[]>([])
const formData = ref({ amount: null as number | null, purpose: '', equity_deduction_ratio: 100 })

const statusMap: Record<string, { type: 'success' | 'warning' | 'error' | 'default', label: string }> = {
  pending: { type: 'warning', label: '审批中' },
  approved: { type: 'success', label: '已通过' },
  rejected: { type: 'error', label: '已拒绝' }
}

const columns = [
  { title: '申请人', key: 'requester_nickname' },
  { title: '金额', key: 'amount', render: (row: any) => `¥${row.amount.toLocaleString()}` },
  { title: '用途', key: 'purpose' },
  { title: '股权扣减', key: 'equity_deduction_ratio', render: (row: any) => `${(row.equity_deduction_ratio * 100).toFixed(0)}%` },
  { title: '状态', key: 'status', render: (row: any) => h(NTag, { type: statusMap[row.status].type, size: 'small' }, { default: () => statusMap[row.status].label }) },
  { title: '申请时间', key: 'created_at', render: (row: any) => dayjs(row.created_at).format('YYYY-MM-DD HH:mm') },
  { 
    title: '操作', 
    key: 'actions',
    render: (row: any) => {
      if (row.status !== 'pending') return '-'
      const canApprove = row.requester_id !== userStore.user?.id
      if (!canApprove) return h('span', { style: 'color:#94a3b8' }, '等待他人审批')
      return h(NSpace, {}, { default: () => [
        h(NButton, { size: 'small', type: 'success', onClick: () => handleApprove(row.id, true) }, { default: () => '同意' }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleApprove(row.id, false) }, { default: () => '拒绝' })
      ]})
    }
  }
]

async function loadData() {
  loading.value = true
  try {
    const res = await expenseApi.list()
    expenses.value = res.data
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!formData.value.amount || !formData.value.purpose) { message.warning('请填写完整信息'); return }
  submitting.value = true
  try {
    await expenseApi.create({
      amount: formData.value.amount,
      purpose: formData.value.purpose,
      equity_deduction_ratio: formData.value.equity_deduction_ratio / 100
    })
    message.success('申请已提交！')
    formData.value = { amount: null, purpose: '', equity_deduction_ratio: 100 }
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleApprove(id: number, approved: boolean) {
  try {
    await expenseApi.approve(id, approved)
    message.success(approved ? '已同意' : '已拒绝')
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(loadData)
</script>
