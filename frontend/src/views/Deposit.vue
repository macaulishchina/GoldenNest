<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">💰</span> 资金注入</h1>
    
    <n-card class="card-hover" style="margin-bottom: 24px">
      <n-form inline :model="formData" @submit.prevent="handleSubmit">
        <n-form-item label="存入金额">
          <n-input-number v-model:value="formData.amount" :min="1" placeholder="金额" style="width: 150px">
            <template #prefix>¥</template>
          </n-input-number>
        </n-form-item>
        <n-form-item label="存入日期">
          <n-date-picker v-model:value="formData.deposit_date" type="datetime" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="formData.note" placeholder="可选" style="width: 200px" />
        </n-form-item>
        <n-form-item>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">存入</n-button>
        </n-form-item>
      </n-form>
    </n-card>
    
    <n-card title="存款记录" class="card-hover">
      <n-data-table :columns="columns" :data="deposits" :loading="loading" :bordered="false" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { depositApi } from '@/api'
import dayjs from 'dayjs'

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const deposits = ref<any[]>([])
const formData = ref({ amount: null as number | null, deposit_date: Date.now(), note: '' })

const columns = [
  { title: '存入人', key: 'user_nickname' },
  { title: '金额', key: 'amount', render: (row: any) => `¥${row.amount.toLocaleString()}` },
  { title: '存入日期', key: 'deposit_date', render: (row: any) => dayjs(row.deposit_date).format('YYYY-MM-DD HH:mm') },
  { title: '备注', key: 'note', render: (row: any) => row.note || '-' }
]

async function loadData() {
  loading.value = true
  try {
    const res = await depositApi.list()
    deposits.value = res.data
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!formData.value.amount) { message.warning('请输入金额'); return }
  submitting.value = true
  try {
    await depositApi.create({
      amount: formData.value.amount,
      deposit_date: new Date(formData.value.deposit_date).toISOString(),
      note: formData.value.note
    })
    message.success('存入成功！💰')
    formData.value = { amount: null, deposit_date: Date.now(), note: '' }
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>
