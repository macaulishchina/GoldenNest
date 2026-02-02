<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">💸</span> 支出申请</h1>
    
    <n-card class="card-hover" style="margin-bottom: 24px">
      <n-form :model="formData" label-placement="left" label-width="100px">
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="支出标题">
              <n-input v-model:value="formData.title" placeholder="如：购买家电" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="支出金额">
              <n-input-number v-model:value="formData.amount" :min="1" style="width: 100%">
                <template #prefix>¥</template>
              </n-input-number>
            </n-form-item>
          </n-gi>
        </n-grid>
        <n-form-item label="支出原因">
          <n-input v-model:value="formData.reason" type="textarea" placeholder="请详细说明支出原因" :rows="2" />
        </n-form-item>
        <n-form-item label="股权扣减分配">
          <div style="width: 100%">
            <n-alert type="info" style="margin-bottom: 12px">
              设置各成员承担的比例（总和必须为100%）
            </n-alert>
            <n-space vertical>
              <div v-for="ratio in formData.deduction_ratios" :key="ratio.user_id" style="display: flex; align-items: center; gap: 12px">
                <span style="min-width: 80px">{{ getMemberNickname(ratio.user_id) }}</span>
                <n-slider v-model:value="ratio.ratio" :min="0" :max="100" :step="1" style="flex: 1" />
                <span style="min-width: 50px">{{ ratio.ratio }}%</span>
              </div>
            </n-space>
            <n-text :type="totalRatio === 100 ? 'success' : 'error'" style="display: block; margin-top: 8px">
              当前总比例：{{ totalRatio }}% {{ totalRatio === 100 ? '✓' : '(需等于100%)' }}
            </n-text>
          </div>
        </n-form-item>
        <n-form-item>
          <n-button type="primary" :loading="submitting" :disabled="totalRatio !== 100" @click="handleSubmit">提交申请</n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <n-card title="申请记录" class="card-hover">
      <n-data-table :columns="columns" :data="expenses" :loading="loading" :bordered="false" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h, watch } from 'vue'
import { useMessage, NButton, NTag, NSpace } from 'naive-ui'
import { expenseApi, familyApi } from '@/api'
import { useUserStore } from '@/stores/user'
import dayjs from 'dayjs'

const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const expenses = ref<any[]>([])
const familyMembers = ref<any[]>([])

const formData = ref({
  title: '',
  amount: null as number | null,
  reason: '',
  deduction_ratios: [] as Array<{ user_id: number; ratio: number }>
})

const totalRatio = computed(() => {
  return formData.value.deduction_ratios.reduce((sum, r) => sum + r.ratio, 0)
})

function getMemberNickname(userId: number): string {
  const member = familyMembers.value.find(m => m.user_id === userId)
  return member?.nickname || `用户${userId}`
}

const statusMap: Record<string, { type: 'success' | 'warning' | 'error' | 'default', label: string }> = {
  pending: { type: 'warning', label: '审批中' },
  approved: { type: 'success', label: '已通过' },
  rejected: { type: 'error', label: '已拒绝' }
}

const columns = [
  { title: '申请人', key: 'requester_nickname' },
  { title: '标题', key: 'title' },
  { title: '金额', key: 'amount', render: (row: any) => `¥${row.amount.toLocaleString()}` },
  { title: '原因', key: 'reason', ellipsis: { tooltip: true } },
  { title: '状态', key: 'status', render: (row: any) => h(NTag, { type: statusMap[row.status]?.type || 'default', size: 'small' }, { default: () => statusMap[row.status]?.label || row.status }) },
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

async function loadFamilyMembers() {
  try {
    const res = await familyApi.getMy()
    familyMembers.value = res.data.members || []
    // 初始化扣减比例 - 平均分配
    if (familyMembers.value.length > 0) {
      const avgRatio = Math.floor(100 / familyMembers.value.length)
      const remainder = 100 - avgRatio * familyMembers.value.length
      formData.value.deduction_ratios = familyMembers.value.map((m, index) => ({
        user_id: m.user_id,
        ratio: avgRatio + (index === 0 ? remainder : 0) // 余数给第一个人
      }))
    }
  } catch (e) {
    console.error(e)
  }
}

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
  if (!formData.value.title || !formData.value.amount || !formData.value.reason) { 
    message.warning('请填写完整信息')
    return 
  }
  if (totalRatio.value !== 100) {
    message.warning('股权扣减比例总和必须为100%')
    return
  }
  submitting.value = true
  try {
    await expenseApi.create({
      title: formData.value.title,
      amount: formData.value.amount,
      reason: formData.value.reason,
      deduction_ratios: formData.value.deduction_ratios.map(r => ({
        user_id: r.user_id,
        ratio: r.ratio / 100 // 转换为0-1的小数
      }))
    })
    message.success('申请已提交！')
    formData.value.title = ''
    formData.value.amount = null
    formData.value.reason = ''
    await loadFamilyMembers() // 重新初始化比例
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

onMounted(async () => {
  await loadFamilyMembers()
  loadData()
})
</script>