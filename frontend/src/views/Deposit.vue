<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">💰</span> 资金注入</h1>
    
    <n-card class="card-hover" style="margin-bottom: 24px">
      <template #header>
        <n-space align="center">
          <span>发起资金注入申请</span>
          <n-tag type="info" size="small">需全员通过</n-tag>
        </n-space>
      </template>
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
          <n-button type="primary" :loading="submitting" @click="handleSubmit">
            <template #icon><n-icon><SendOutline /></n-icon></template>
            发起申请
          </n-button>
        </n-form-item>
      </n-form>
    </n-card>
    
    <!-- 待审批的资金注入申请 -->
    <n-card title="待审批申请" class="card-hover" style="margin-bottom: 24px" v-if="pendingApprovals.length > 0">
      <n-data-table :columns="approvalColumns" :data="pendingApprovals" :bordered="false" />
    </n-card>
    
    <n-card title="存款记录" class="card-hover">
      <n-data-table :columns="columns" :data="deposits" :loading="loading" :bordered="false" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useMessage, NButton, NTag, NSpace } from 'naive-ui'
import { depositApi, approvalApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { SendOutline } from '@vicons/ionicons5'
import { formatShortDateTime } from '@/utils/date'
import { checkAndShowAchievements } from '@/utils/achievement'

const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const deposits = ref<any[]>([])
const pendingApprovals = ref<any[]>([])
const formData = ref({ amount: null as number | null, deposit_date: Date.now(), note: '' })

const columns = [
  { title: '存入人', key: 'user_nickname' },
  { title: '金额', key: 'amount', render: (row: any) => `¥${row.amount.toLocaleString()}` },
  { title: '存入日期', key: 'deposit_date', render: (row: any) => formatShortDateTime(row.deposit_date) },
  { title: '备注', key: 'note', render: (row: any) => row.note || '-' }
]

const approvalColumns = [
  { title: '申请人', key: 'requester_nickname' },
  { 
    title: '金额', 
    key: 'amount', 
    render: (row: any) => {
      const data = JSON.parse(row.request_data)
      return `¥${data.amount?.toLocaleString() || '-'}`
    }
  },
  { 
    title: '备注', 
    key: 'note', 
    render: (row: any) => {
      const data = JSON.parse(row.request_data)
      return data.note || '-'
    }
  },
  { title: '申请时间', key: 'created_at', render: (row: any) => formatShortDateTime(row.created_at) },
  { 
    title: '审批进度', 
    key: 'progress',
    render: (row: any) => `${row.approved_count || 0}/${row.required_count || 0}`
  },
  { 
    title: '操作', 
    key: 'actions',
    render: (row: any) => {
      const canApprove = row.requester_id !== userStore.user?.id && !row.has_voted
      if (!canApprove) return h('span', { style: 'color:#94a3b8' }, row.has_voted ? '已投票' : '等待他人')
      return h(NSpace, { size: 'small' }, { default: () => [
        h(NButton, { size: 'small', type: 'success', onClick: () => handleApprove(row.id, true) }, { default: () => '同意' }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleApprove(row.id, false) }, { default: () => '拒绝' })
      ]})
    }
  }
]

async function loadData() {
  loading.value = true
  try {
    const [depositsRes, approvalsRes] = await Promise.all([
      depositApi.list(),
      approvalApi.list({ status: 'pending', request_type: 'deposit' })
    ])
    deposits.value = depositsRes.data
    pendingApprovals.value = approvalsRes.data
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!formData.value.amount) { message.warning('请输入金额'); return }
  submitting.value = true
  try {
    await approvalApi.createDeposit({
      amount: formData.value.amount,
      deposit_date: new Date(formData.value.deposit_date).toISOString(),
      note: formData.value.note
    })
    message.success('申请已提交，等待审批！💰')
    formData.value = { amount: null, deposit_date: Date.now(), note: '' }
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleApprove(id: number, approved: boolean) {
  try {
    if (approved) {
      await approvalApi.approve(id)
    } else {
      const reason = window.prompt('请输入拒绝原因')
      if (reason === null) return
      await approvalApi.reject(id, reason || '未说明原因')
    }
    message.success(approved ? '已同意' : '已拒绝')
    loadData()
    
    // 审批后检查成就
    if (approved) {
      setTimeout(() => checkAndShowAchievements(), 500)
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(loadData)
</script>