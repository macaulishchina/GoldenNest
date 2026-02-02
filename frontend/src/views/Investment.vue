<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">📈</span> 理财配置</h1>
    
    <n-card class="card-hover" style="margin-bottom: 24px">
      <template #header>
        <n-space align="center">
          <span>发起理财产品登记申请</span>
          <n-tag type="info" size="small">需全员通过</n-tag>
        </n-space>
      </template>
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
          <n-button type="primary" :loading="submitting" @click="handleSubmit">
            <template #icon><n-icon><SendOutline /></n-icon></template>
            发起申请
          </n-button>
        </n-form-item>
      </n-form>
    </n-card>

    <!-- 待审批的理财申请 -->
    <n-card title="待审批申请" class="card-hover" style="margin-bottom: 24px" v-if="pendingApprovals.length > 0">
      <n-data-table :columns="approvalColumns" :data="pendingApprovals" :bordered="false" />
    </n-card>

    <n-card title="理财产品列表" class="card-hover">
      <n-data-table :columns="columns" :data="investments" :loading="loading" :bordered="false" />
    </n-card>

    <!-- 登记收益弹窗 -->
    <n-modal v-model:show="showIncomeModal" preset="dialog" title="登记收益" positive-text="提交申请" negative-text="取消" @positive-click="submitIncome">
      <n-form :model="incomeForm" label-placement="left" label-width="80px">
        <n-form-item label="理财产品">
          <n-text>{{ selectedInvestment?.name }}</n-text>
        </n-form-item>
        <n-form-item label="收益金额">
          <n-input-number v-model:value="incomeForm.amount" style="width: 100%">
            <template #prefix>¥</template>
          </n-input-number>
          <n-text depth="3" style="font-size: 12px; margin-top: 4px; display: block">
            可为负数（表示亏损）
          </n-text>
        </n-form-item>
        <n-form-item label="收益日期">
          <n-date-picker v-model:value="incomeForm.income_date" type="date" style="width: 100%" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="incomeForm.note" placeholder="可选" />
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useMessage, NButton, NTag, NSpace } from 'naive-ui'
import { investmentApi, approvalApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { SendOutline } from '@vicons/ionicons5'
import { formatShortDateTime, formatLocalDate } from '@/utils/date'
import { checkAndShowAchievements } from '@/utils/achievement'
import dayjs from 'dayjs'

const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const submitting = ref(false)
const investments = ref<any[]>([])
const pendingApprovals = ref<any[]>([])
const formData = ref({ 
  name: '', 
  investment_type: 'fund' as 'fund' | 'stock' | 'bond' | 'deposit' | 'other',
  principal: null as number | null, 
  expected_rate: null as number | null 
})

// 收益登记相关
const showIncomeModal = ref(false)
const selectedInvestment = ref<any>(null)
const incomeForm = ref({
  amount: null as number | null,
  income_date: Date.now(),
  note: ''
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

const requestTypeLabels: Record<string, string> = {
  investment_create: '登记产品',
  investment_update: '更新产品',
  investment_income: '登记收益'
}

const columns = [
  { title: '产品名称', key: 'name' },
  { title: '类型', key: 'investment_type', render: (row: any) => typeLabels[row.investment_type] || row.investment_type },
  { title: '投资本金', key: 'principal', render: (row: any) => `¥${row.principal.toLocaleString()}` },
  { title: '预期年化', key: 'expected_rate', render: (row: any) => `${(row.expected_rate * 100).toFixed(2)}%` },
  { title: '累计收益', key: 'total_income', render: (row: any) => h('span', { style: { color: (row.total_income || 0) >= 0 ? '#10b981' : '#ef4444' } }, `¥${(row.total_income || 0).toLocaleString()}`) },
  { title: '状态', key: 'is_active', render: (row: any) => h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, { default: () => row.is_active ? '持有中' : '已结束' }) },
  { title: '开始日期', key: 'start_date', render: (row: any) => formatLocalDate(row.start_date) },
  { 
    title: '操作', 
    key: 'actions',
    render: (row: any) => h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => openIncomeModal(row) }, { default: () => '登记收益' })
  }
]

const approvalColumns = [
  { title: '申请人', key: 'requester_nickname' },
  { 
    title: '类型', 
    key: 'request_type',
    render: (row: any) => h(NTag, { size: 'small', type: 'info' }, { default: () => requestTypeLabels[row.request_type] || row.request_type })
  },
  { 
    title: '详情', 
    key: 'details', 
    render: (row: any) => {
      const data = JSON.parse(row.request_data)
      if (row.request_type === 'investment_create') {
        return `${data.name} - ¥${data.principal?.toLocaleString()}`
      } else if (row.request_type === 'investment_income') {
        return `收益: ¥${data.amount?.toLocaleString()}`
      }
      return '-'
    }
  },
  { title: '申请时间', key: 'created_at', render: (row: any) => dayjs(row.created_at).format('YYYY-MM-DD HH:mm') },
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
    const [investmentsRes, approvalsRes] = await Promise.all([
      investmentApi.list(),
      approvalApi.list({ status: 'pending' })
    ])
    investments.value = investmentsRes.data
    // 只显示理财相关的待审批申请
    const investmentTypes = ['investment_create', 'investment_update', 'investment_income']
    pendingApprovals.value = approvalsRes.data.filter((item: any) => investmentTypes.includes(item.request_type))
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!formData.value.name || !formData.value.principal) { message.warning('请填写完整信息'); return }
  submitting.value = true
  try {
    await approvalApi.createInvestment({
      name: formData.value.name,
      investment_type: formData.value.investment_type,
      principal: formData.value.principal,
      expected_rate: (formData.value.expected_rate || 0) / 100,
      start_date: new Date().toISOString()
    })
    message.success('申请已提交，等待审批！📈')
    formData.value = { name: '', investment_type: 'fund', principal: null, expected_rate: null }
    loadData()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

function openIncomeModal(investment: any) {
  selectedInvestment.value = investment
  incomeForm.value = {
    amount: null,
    income_date: Date.now(),
    note: ''
  }
  showIncomeModal.value = true
}

async function submitIncome() {
  if (incomeForm.value.amount === null) { 
    message.warning('请输入收益金额')
    return false
  }
  try {
    await approvalApi.createInvestmentIncome({
      investment_id: selectedInvestment.value.id,
      amount: incomeForm.value.amount,
      income_date: new Date(incomeForm.value.income_date).toISOString(),
      note: incomeForm.value.note
    })
    message.success('收益登记申请已提交！')
    showIncomeModal.value = false
    loadData()
    return true
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
    return false
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
    
    // 审批通过后检查成就
    if (approved) {
      setTimeout(() => checkAndShowAchievements(), 500)
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(loadData)
</script>