<template>
  <div class="page-container">
    <h1 class="page-title"><span class="icon">📈</span> 理财配置</h1>
    
    <!-- 家庭自由资金卡片 -->
    <n-card class="card-hover" style="margin-bottom: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
      <n-statistic label="家庭自由资金" :value="currentBalance">
        <template #prefix>¥</template>
      </n-statistic>
      <template #footer>
        <n-text style="color: rgba(255,255,255,0.8); font-size: 12px">
          💰 共享资金池 | <strong>外部资金</strong>=计入股权 | <strong>从自由资金扣除</strong>=不计股权
        </n-text>
      </template>
    </n-card>
    
    <n-card class="card-hover investment-form-card" style="margin-bottom: 24px">
      <template #header>
        <n-space align="center">
          <span>发起理财产品登记申请</span>
          <n-tag type="info" size="small">需全员通过</n-tag>
        </n-space>
      </template>
      <!-- 桌面端表单 -->
      <n-form inline :model="formData" class="desktop-only">
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
        <n-form-item label="资金来源">
          <n-radio-group v-model:value="formData.deduct_from_cash" size="small">
            <n-radio :value="false">外部资金</n-radio>
            <n-radio :value="true">从自由资金扣除</n-radio>
          </n-radio-group>
        </n-form-item>
        <n-form-item>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">
            <template #icon><n-icon><SendOutline /></n-icon></template>
            发起申请
          </n-button>
        </n-form-item>
      </n-form>
      <!-- 移动端紧凑表单 -->
      <div class="mobile-only mobile-investment-form">
        <!-- 第一行：产品名称 + 理财类型 -->
        <div class="form-row">
          <div class="form-col name-col">
            <label>产品名称</label>
            <n-input v-model:value="formData.name" placeholder="货币基金" size="small" />
          </div>
          <div class="form-col type-col">
            <label>类型</label>
            <n-select v-model:value="formData.investment_type" :options="typeOptions" size="small" />
          </div>
        </div>
        <!-- 第二行：投资本金 + 预期年化 + 提交按钮 -->
        <div class="form-row">
          <div class="form-col principal-col">
            <label>本金</label>
            <n-input-number v-model:value="formData.principal" :min="1" placeholder="0" size="small">
              <template #prefix>¥</template>
            </n-input-number>
          </div>
          <div class="form-col rate-col">
            <label>年化</label>
            <n-input-number v-model:value="formData.expected_rate" :min="0" :max="100" placeholder="0" size="small">
              <template #suffix>%</template>
            </n-input-number>
          </div>
          <div class="form-col btn-col">
            <label>&nbsp;</label>
            <n-button type="primary" :loading="submitting" @click="handleSubmit" size="small" class="submit-btn">
              申请
            </n-button>
          </div>
        </div>
        <!-- 第三行：资金来源 -->
        <div class="form-row" style="margin-top: 8px">
          <div class="form-col" style="flex: 1">
            <label>资金来源</label>
            <n-radio-group v-model:value="formData.deduct_from_cash" size="small">
              <n-radio :value="false">外部资金</n-radio>
              <n-radio :value="true">从自由资金扣除</n-radio>
            </n-radio-group>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 待审批的理财申请 -->
    <n-card title="待审批申请" class="card-hover" style="margin-bottom: 24px" v-if="pendingApprovals.length > 0">
      <!-- 桌面端：表格 -->
      <n-data-table class="desktop-only" :columns="approvalColumns" :data="pendingApprovals" :bordered="false" />
      <!-- 移动端：卡片列表 -->
      <div class="mobile-only approval-cards">
        <div v-for="item in pendingApprovals" :key="item.id" class="approval-card">
          <div class="approval-card-header">
            <n-tag size="small" type="info">{{ requestTypeLabels[item.request_type] || item.request_type }}</n-tag>
            <span class="approval-time">{{ formatShortDateTime(item.created_at) }}</span>
          </div>
          <div class="approval-card-body">
            <div class="approval-requester">{{ item.requester_nickname }} 发起</div>
            <div class="approval-detail">{{ formatApprovalDetail(item) }}</div>
          </div>
          <div class="approval-card-footer">
            <span class="approval-progress">审批进度: {{ item.approved_count || 0 }}/{{ item.required_count || 0 }}</span>
            <div class="approval-actions" v-if="item.requester_id !== userStore.user?.id && !item.has_voted">
              <n-button size="small" type="success" @click="handleApprove(item.id, true)">同意</n-button>
              <n-button size="small" type="error" @click="handleApprove(item.id, false)">拒绝</n-button>
            </div>
            <span v-else class="approval-wait">{{ item.has_voted ? '已投票' : '等待他人' }}</span>
          </div>
        </div>
      </div>
    </n-card>

    <n-card title="理财产品列表" class="card-hover">
      <!-- 桌面端：表格 -->
      <n-data-table class="desktop-only" :columns="columns" :data="investments" :loading="loading" :bordered="false" />
      <!-- 移动端：卡片列表 -->
      <div class="mobile-only">
        <n-spin :show="loading">
          <div class="investment-cards" v-if="investments.length > 0">
            <div v-for="item in investments" :key="item.id" class="investment-card" :class="{ 'deleted': item.is_deleted }">
              <div class="card-header">
                <span class="product-name">{{ item.name }}</span>
                <n-tag :type="item.is_deleted ? 'error' : (item.is_active ? 'success' : 'default')" size="small">
                  {{ item.is_deleted ? '已删除' : (item.is_active ? '持有中' : '已结束') }}
                </n-tag>
              </div>
              <div class="card-type">
                <n-tag size="small" :bordered="false">{{ typeLabels[item.investment_type] || item.investment_type }}</n-tag>
              </div>
              <div class="card-stats">
                <div class="stat-item">
                  <span class="stat-label">初始本金</span>
                  <span class="stat-value">¥{{ formatMoney(item.principal) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">当前持仓</span>
                  <span class="stat-value">¥{{ formatMoney(item.current_principal || item.principal) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">总收益</span>
                  <span class="stat-value" :class="(item.total_return || 0) >= 0 ? 'profit' : 'loss'">
                    ¥{{ formatMoney(item.total_return || 0) }}
                  </span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">ROI</span>
                  <span class="stat-value" :class="(item.roi || 0) >= 0 ? 'profit' : 'loss'">
                    {{ (item.roi || 0).toFixed(2) }}%
                  </span>
                </div>
              </div>
              <div class="card-footer" v-if="!item.is_deleted">
                <span class="start-date">{{ formatLocalDate(item.start_date) }} 起</span>
                <n-space size="small">
                  <n-button size="small" type="primary" text @click="openIncomeModal(item)">更新价值</n-button>
                  <n-button size="small" type="info" text @click="openIncreaseModal(item)">增持</n-button>
                  <n-button size="small" type="warning" text @click="openDecreaseModal(item)">减持</n-button>
                  <n-button size="small" type="error" text @click="handleDelete(item)">删除</n-button>
                </n-space>
              </div>
              <div class="card-footer" v-else>
                <span class="deleted-text">{{ item.deleted_at ? formatLocalDate(item.deleted_at) + ' 删除' : '已删除' }}</span>
              </div>
            </div>
          </div>
          <n-empty v-else description="暂无理财产品" />
        </n-spin>
      </div>
    </n-card>

    <!-- 登记收益弹窗（改为更新价值） -->
    <n-modal v-model:show="showIncomeModal" preset="dialog" title="更新投资价值" positive-text="提交申请" negative-text="取消" @positive-click="submitIncome">
      <n-form :model="incomeForm" label-placement="left" label-width="90px">
        <n-form-item label="理财产品">
          <n-text>{{ selectedInvestment?.name }}</n-text>
        </n-form-item>
        <n-form-item label="当前持仓">
          <n-text type="info">¥{{ formatMoney(selectedInvestment?.current_principal || selectedInvestment?.principal || 0) }}</n-text>
        </n-form-item>
        <n-form-item label="当前总价值">
          <n-input-number v-model:value="incomeForm.current_value" style="width: 100%" :min="0">
            <template #prefix>¥</template>
          </n-input-number>
          <n-text depth="3" style="font-size: 12px; margin-top: 4px; display: block">
            输入投资产品的当前市场价值，系统将自动计算收益
          </n-text>
        </n-form-item>
        <n-form-item label="计算收益" v-if="incomeForm.current_value">
          <n-text :type="calculatedIncome >= 0 ? 'success' : 'error'" strong>
            ¥{{ formatMoney(calculatedIncome) }}
          </n-text>
        </n-form-item>
        <n-form-item label="更新日期">
          <n-date-picker v-model:value="incomeForm.income_date" type="date" style="width: 100%" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="incomeForm.note" placeholder="可选" />
        </n-form-item>
      </n-form>
    </n-modal>

    <!-- 增持模态框 -->
    <n-modal v-model:show="showIncreaseModal" preset="dialog" title="投资增持" positive-text="提交申请" negative-text="取消" @positive-click="submitIncrease">
      <n-form :model="increaseForm" label-placement="left" label-width="90px">
        <n-form-item label="理财产品">
          <n-text>{{ selectedInvestment?.name }}</n-text>
        </n-form-item>
        <n-form-item label="当前持仓">
          <n-text type="info">¥{{ formatMoney(selectedInvestment?.current_principal || 0) }}</n-text>
        </n-form-item>
        <n-form-item label="可用余额">
          <n-text type="warning">¥{{ formatMoney(currentBalance) }}</n-text>
        </n-form-item>
        <n-form-item label="增持金额">
          <n-input-number v-model:value="increaseForm.amount" style="width: 100%" :min="1" :max="currentBalance">
            <template #prefix>¥</template>
          </n-input-number>
        </n-form-item>
        <n-form-item label="增持日期">
          <n-date-picker v-model:value="increaseForm.operation_date" type="date" style="width: 100%" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="increaseForm.note" placeholder="可选" />
        </n-form-item>
      </n-form>
    </n-modal>

    <!-- 减持模态框 -->
    <n-modal v-model:show="showDecreaseModal" preset="dialog" title="投资减持" positive-text="提交申请" negative-text="取消" @positive-click="submitDecrease">
      <n-form :model="decreaseForm" label-placement="left" label-width="90px">
        <n-form-item label="理财产品">
          <n-text>{{ selectedInvestment?.name }}</n-text>
        </n-form-item>
        <n-form-item label="当前持仓">
          <n-text type="info">¥{{ formatMoney(selectedInvestment?.current_principal || 0) }}</n-text>
        </n-form-item>
        <n-form-item label="减持金额">
          <n-input-number v-model:value="decreaseForm.amount" style="width: 100%" 
            :min="1" :max="selectedInvestment?.current_principal || 0">
            <template #prefix>¥</template>
          </n-input-number>
          <n-text depth="3" style="font-size: 12px; margin-top: 4px; display: block">
            最多可减持 ¥{{ formatMoney(selectedInvestment?.current_principal || 0) }}
          </n-text>
        </n-form-item>
        <n-form-item label="减持日期">
          <n-date-picker v-model:value="decreaseForm.operation_date" type="date" style="width: 100%" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="decreaseForm.note" placeholder="可选" />
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, computed } from 'vue'
import { useMessage, useDialog, NButton, NTag, NSpace, NInput, NRadio, NRadioGroup } from 'naive-ui'
import { storeToRefs } from 'pinia'
import { investmentApi, approvalApi, transactionApi, assetApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { usePrivacyStore } from '@/stores/privacy'
import { SendOutline } from '@vicons/ionicons5'
import { formatShortDateTime, formatLocalDate } from '@/utils/date'
import { checkAndShowAchievements } from '@/utils/achievement'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()
const userStore = useUserStore()
const privacyStore = usePrivacyStore()
const { privacyMode } = storeToRefs(privacyStore)
const loading = ref(false)

// 隐私模式格式化金额
const formatMoney = (num: number) => privacyStore.formatMoney(num)
const submitting = ref(false)
const investments = ref<any[]>([])
const pendingApprovals = ref<any[]>([])
const formData = ref({ 
  name: '', 
  investment_type: 'fund' as 'fund' | 'stock' | 'bond' | 'other',
  principal: null as number | null, 
  expected_rate: null as number | null,
  deduct_from_cash: false
})

// 收益登记相关
const showIncomeModal = ref(false)
const selectedInvestment = ref<any>(null)
const incomeForm = ref({
  current_value: null as number | null,
  income_date: Date.now(),
  note: ''
})

// 增持/减持相关
const showIncreaseModal = ref(false)
const showDecreaseModal = ref(false)
const increaseForm = ref({
  amount: null as number | null,
  operation_date: Date.now(),
  note: ''
})
const decreaseForm = ref({
  amount: null as number | null,
  operation_date: Date.now(),
  note: ''
})

// 当前余额（从transactions获取）
const currentBalance = ref(0)

// 计算收益（实时预览）
const calculatedIncome = computed(() => {
  if (!incomeForm.value.current_value || !selectedInvestment.value) return 0
  const currentPrincipal = selectedInvestment.value.current_principal || selectedInvestment.value.principal || 0
  const historicalIncome = selectedInvestment.value.total_return || 0
  return incomeForm.value.current_value - currentPrincipal - historicalIncome
})

const typeOptions = [
  { label: '基金', value: 'fund' },
  { label: '股票', value: 'stock' },
  { label: '债券', value: 'bond' },
  { label: '其他', value: 'other' }
]

const typeLabels: Record<string, string> = {
  fund: '基金',
  stock: '股票',
  bond: '债券',
  time_deposit: '定期存款',
  other: '其他'
}

const requestTypeLabels: Record<string, string> = {
  asset_create: '资产登记',
  investment_create: '登记产品',
  investment_update: '更新产品',
  investment_income: '登记收益',
  investment_increase: '投资增持',
  investment_decrease: '投资减持',
  investment_delete: '删除产品'
}

const columns = computed(() => [
  { title: '产品名称', key: 'name' },
  { title: '类型', key: 'investment_type', render: (row: any) => typeLabels[row.investment_type] || row.investment_type },
  { title: '初始本金', key: 'principal', render: (row: any) => `¥${formatMoney(row.principal)}` },
  { title: '当前持仓', key: 'current_principal', render: (row: any) => `¥${formatMoney(row.current_principal || row.principal)}` },
  { title: '总收益', key: 'total_return', render: (row: any) => h('span', { style: { color: (row.total_return || 0) >= 0 ? '#10b981' : '#ef4444' } }, `¥${formatMoney(row.total_return || 0)}`) },
  { title: 'ROI', key: 'roi', render: (row: any) => {
    const roi = row.roi || 0
    return h('span', { style: { color: roi >= 0 ? '#10b981' : '#ef4444' } }, `${roi.toFixed(2)}%`)
  }},
  { title: '状态', key: 'is_active', render: (row: any) => {
    if (row.is_deleted) return h(NTag, { type: 'error', size: 'small' }, { default: () => '已删除' })
    return h(NTag, { type: row.is_active ? 'success' : 'default', size: 'small' }, { default: () => row.is_active ? '持有中' : '已结束' })
  }},
  { title: '开始日期', key: 'start_date', render: (row: any) => formatLocalDate(row.start_date) },
  { 
    title: '操作', 
    key: 'actions',
    render: (row: any) => {
      if (row.is_deleted) return h('span', { style: { color: '#999' } }, '已删除')
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', text: true, type: 'primary', onClick: () => openIncomeModal(row) }, { default: () => '更新价值' }),
          h(NButton, { size: 'small', text: true, type: 'info', onClick: () => openIncreaseModal(row) }, { default: () => '增持' }),
          h(NButton, { size: 'small', text: true, type: 'warning', onClick: () => openDecreaseModal(row) }, { default: () => '减持' }),
          h(NButton, { size: 'small', text: true, type: 'error', onClick: () => handleDelete(row) }, { default: () => '删除' })
        ]
      })
    }
  }
])

const approvalColumns = computed(() => [
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
        return `${data.name} - ¥${formatMoney(data.principal || 0)}`
      } else if (row.request_type === 'investment_income') {
        return `收益: ¥${formatMoney(data.amount || 0)}`
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
])

async function loadData() {
  loading.value = true
  try {
    const [investmentsRes, approvalsRes, cashBalanceRes] = await Promise.all([
      investmentApi.list(),
      approvalApi.list({ status: 'pending' }),
      assetApi.getCashBalance()  // 获取家庭自由资金余额
    ])
    investments.value = investmentsRes.data
    // 显示所有理财相关的待审批申请（包括新的 asset_create 类型）
    const investmentTypes = ['asset_create', 'investment_create', 'investment_update', 'investment_income', 'investment_increase', 'investment_decrease', 'investment_delete']
    pendingApprovals.value = (approvalsRes.data.items || []).filter((item: any) => investmentTypes.includes(item.request_type))
    // 从API获取家庭自由资金余额
    currentBalance.value = cashBalanceRes.data.balance || 0
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!formData.value.name || !formData.value.principal) { message.warning('请填写完整信息'); return }
  
  // 检查是否需要从自由资金扣除，如果是则检查余额
  if (formData.value.deduct_from_cash) {
    try {
      const { data } = await assetApi.getCashBalance()
      const cashBalance = data.balance || 0
      if (cashBalance < formData.value.principal) {
        message.error(`家庭自由资金不足：需要¥${formData.value.principal}，当前仅有¥${cashBalance.toFixed(2)}`)
        return
      }
    } catch (error) {
      console.error('Failed to check cash balance:', error)
      message.error('无法获取家庭自由资金余额，请稍后重试')
      return
    }
  }
  
  submitting.value = true
  try {
    await approvalApi.createAsset({
      user_id: userStore.user?.id || 0,
      name: formData.value.name,
      asset_type: formData.value.investment_type as any,
      currency: 'CNY',
      amount: formData.value.principal,
      expected_rate: (formData.value.expected_rate || 0) / 100,
      start_date: new Date().toISOString(),
      deduct_from_cash: formData.value.deduct_from_cash
    })
    message.success('申请已提交，等待审批！📈')
    formData.value = { name: '', investment_type: 'fund', principal: null, expected_rate: null, deduct_from_cash: false }
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
    current_value: null,
    income_date: Date.now(),
    note: ''
  }
  showIncomeModal.value = true
}

async function submitIncome() {
  if (incomeForm.value.current_value === null || incomeForm.value.current_value <= 0) { 
    message.warning('请输入有效的当前总价值')
    return false
  }
  try {
    await approvalApi.createInvestmentIncome({
      investment_id: selectedInvestment.value.id,
      amount: null,
      current_value: incomeForm.value.current_value,
      income_date: new Date(incomeForm.value.income_date).toISOString(),
      note: incomeForm.value.note || null
    })
    message.success('价值更新申请已提交！')
    showIncomeModal.value = false
    loadData()
    return true
  } catch (e: any) {
    console.error('Income submission error:', e.response?.data)
    message.error(e.response?.data?.detail || '操作失败')
    return false
  }
}

function openIncreaseModal(investment: any) {
  selectedInvestment.value = investment
  increaseForm.value = {
    amount: null,
    operation_date: Date.now(),
    note: ''
  }
  showIncreaseModal.value = true
}

async function submitIncrease() {
  if (increaseForm.value.amount === null) { 
    message.warning('请输入增持金额')
    return false
  }
  if (increaseForm.value.amount > currentBalance.value) {
    message.warning('余额不足')
    return false
  }
  try {
    await approvalApi.increaseInvestment({
      investment_id: selectedInvestment.value.id,
      amount: increaseForm.value.amount,
      operation_date: new Date(increaseForm.value.operation_date).toISOString(),
      note: increaseForm.value.note
    })
    message.success('增持申请已提交！')
    showIncreaseModal.value = false
    loadData()
    return true
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
    return false
  }
}

function openDecreaseModal(investment: any) {
  selectedInvestment.value = investment
  decreaseForm.value = {
    amount: null,
    operation_date: Date.now(),
    note: ''
  }
  showDecreaseModal.value = true
}

async function submitDecrease() {
  if (decreaseForm.value.amount === null) { 
    message.warning('请输入减持金额')
    return false
  }
  const maxDecrease = selectedInvestment.value.current_principal || 0
  if (decreaseForm.value.amount > maxDecrease) {
    message.warning(`减持金额不能超过当前持仓 ￥${maxDecrease}`)
    return false
  }
  try {
    await approvalApi.decreaseInvestment({
      investment_id: selectedInvestment.value.id,
      amount: decreaseForm.value.amount,
      operation_date: new Date(decreaseForm.value.operation_date).toISOString(),
      note: decreaseForm.value.note
    })
    message.success('减持申请已提交！')
    showDecreaseModal.value = false
    loadData()
    return true
  } catch (e: any) {
    message.error(e.response?.data?.detail || '操作失败')
    return false
  }
}

function handleDelete(investment: any) {
  dialog.warning({
    title: '确认删除',
    content: `确认删除投资产品「${investment.name}」？此操作为软删除，历史数据将保留。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await approvalApi.deleteInvestment({
          investment_id: investment.id,
          reason: '用户请求删除'
        })
        message.success('删除申请已提交！')
        loadData()
      } catch (e: any) {
        message.error(e.response?.data?.detail || '操作失败')
      }
    }
  })
}

async function doApprove(id: number, approved: boolean, reason?: string) {
  try {
    if (approved) {
      await approvalApi.approve(id)
    } else {
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

// 格式化审批详情（移动端卡片用）
function formatApprovalDetail(item: any): string {
  const data = JSON.parse(item.request_data)
  if (item.request_type === 'investment_create') {
    return `${data.name} - ¥${formatMoney(data.principal || 0)}`
  } else if (item.request_type === 'investment_income') {
    return `收益: ¥${formatMoney(data.amount || 0)}`
  }
  return '-'
}

function handleApprove(id: number, approved: boolean) {
  if (approved) {
    doApprove(id, true)
  } else {
    dialog.create({
      title: '拒绝原因',
      content: () => h(NInput, {
        id: 'reject-reason-input',
        placeholder: '请输入拒绝原因（可选）',
        style: { width: '100%' }
      }),
      positiveText: '确认拒绝',
      negativeText: '取消',
      onPositiveClick: () => {
        const reason = (document.getElementById('reject-reason-input') as HTMLInputElement)?.value || ''
        doApprove(id, false, reason)
      }
    })
  }
}

onMounted(loadData)
</script>

<style scoped>
/* 家庭自由资金卡片样式 */
:deep(.n-statistic) {
  color: white;
}

:deep(.n-statistic .n-statistic-value__prefix),
:deep(.n-statistic .n-statistic-value__content) {
  color: white !important;
}

/* 桌面/移动端显示控制 */
.desktop-only {
  display: block;
}
.mobile-only {
  display: none;
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
    padding: 16px;
  }
  
  /* 表单垂直布局 */
  :deep(.n-form--inline) {
    display: flex;
    flex-direction: column;
    gap: 0;
  }
  
  :deep(.n-form--inline .n-form-item) {
    display: flex;
    flex-direction: column;
    margin-bottom: 16px;
    margin-right: 0;
  }
  
  :deep(.n-form--inline .n-form-item-label) {
    display: block;
    text-align: left;
    padding-bottom: 8px;
    width: auto;
  }
  
  :deep(.n-form--inline .n-form-item-blank) {
    min-height: auto;
  }
  
  :deep(.n-form--inline .n-input),
  :deep(.n-form--inline .n-input-number),
  :deep(.n-form--inline .n-select) {
    width: 100% !important;
    font-size: 16px; /* 防止 iOS 放大 */
  }
  
  /* 修复 n-input-number 在移动端的布局 */
  :deep(.n-input-number) {
    flex-direction: row !important;
  }
  
  :deep(.n-input-number .n-input) {
    flex: 1 !important;
  }
  
  :deep(.n-input-number .n-input-wrapper) {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
  }
  
  :deep(.n-input-number .n-input__input-el) {
    text-align: left !important;
  }
  
  :deep(.n-input-number .n-input__suffix) {
    margin-left: auto !important;
  }
  
  :deep(.n-input-number-button-group) {
    display: flex !important;
    flex-direction: row !important;
  }
  
  /* 提交按钮 */
  :deep(.n-form--inline .n-button) {
    width: 100%;
    height: 48px;
    font-size: 15px;
  }
  
  /* 表格优化 */
  :deep(.n-data-table) {
    font-size: 13px;
  }
  
  :deep(.n-data-table-th),
  :deep(.n-data-table-td) {
    padding: 10px 8px !important;
  }
  
  /* 弹窗全屏 */
  :deep(.n-modal-mask .n-dialog) {
    width: 100% !important;
    max-width: calc(100vw - 32px);
    margin: 16px;
  }
  
  :deep(.n-dialog .n-form-item) {
    display: flex;
    flex-direction: column;
    margin-bottom: 16px;
  }
  
  :deep(.n-dialog .n-form-item-label) {
    display: block;
    text-align: left;
    padding-bottom: 8px;
    width: auto !important;
  }
  
  /* 卡片间距 */
  :deep(.n-card) {
    margin-bottom: 16px !important;
  }

  /* ===== 理财产品卡片样式 ===== */
  .investment-cards {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .investment-card {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border-radius: 12px;
    padding: 14px;
    border: 1px solid #e2e8f0;
  }

  .investment-card .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .investment-card .product-name {
    font-size: 16px;
    font-weight: 600;
    color: #1e293b;
  }

  .investment-card .card-type {
    margin-bottom: 12px;
  }

  .investment-card .card-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
    background: white;
    border-radius: 8px;
    padding: 10px;
  }

  .investment-card .stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .investment-card .stat-label {
    font-size: 11px;
    color: #64748b;
    margin-bottom: 4px;
  }

  .investment-card .stat-value {
    font-size: 14px;
    font-weight: 600;
    color: #334155;
  }

  .investment-card .stat-value.profit {
    color: #10b981;
  }

  .investment-card .stat-value.loss {
    color: #ef4444;
  }

  .investment-card .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 10px;
    border-top: 1px solid #e2e8f0;
  }

  .investment-card .start-date {
    font-size: 12px;
    color: #94a3b8;
  }

  /* ===== 待审批卡片样式 ===== */
  .approval-cards {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .approval-card {
    background: #fffbeb;
    border-radius: 10px;
    padding: 12px;
    border: 1px solid #fde68a;
  }

  .approval-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .approval-time {
    font-size: 11px;
    color: #94a3b8;
  }

  .approval-card-body {
    margin-bottom: 10px;
  }

  .approval-requester {
    font-size: 14px;
    font-weight: 500;
    color: #1e293b;
    margin-bottom: 4px;
  }

  .approval-detail {
    font-size: 13px;
    color: #64748b;
  }

  .approval-card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 10px;
    border-top: 1px solid #fde68a;
  }

  .approval-progress {
    font-size: 12px;
    color: #64748b;
  }

  .approval-actions {
    display: flex;
    gap: 8px;
  }

  .approval-wait {
    font-size: 12px;
    color: #94a3b8;
  }

  /* ===== 移动端紧凑表单样式 ===== */
  .investment-form-card :deep(.n-card__content) {
    padding: 12px !important;
  }
  
  .mobile-investment-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  
  .mobile-investment-form .form-row {
    display: flex;
    gap: 10px;
    align-items: flex-end;
  }
  
  .mobile-investment-form .form-col {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  
  .mobile-investment-form .form-col.name-col {
    flex: 1.2;
    min-width: 0;
  }
  
  .mobile-investment-form .form-col.type-col {
    flex: 0.8;
    min-width: 0;
  }
  
  .mobile-investment-form .form-col.principal-col {
    flex: 1;
    min-width: 0;
  }
  
  .mobile-investment-form .form-col.rate-col {
    flex: 0.8;
    min-width: 0;
  }
  
  .mobile-investment-form .form-col.btn-col {
    flex-shrink: 0;
  }
  
  .mobile-investment-form label {
    font-size: 12px;
    color: #6b7280;
    font-weight: 500;
  }
  
  /* 统一输入框高度 32px */
  .mobile-investment-form :deep(.n-input),
  .mobile-investment-form :deep(.n-input-number),
  .mobile-investment-form :deep(.n-select) {
    font-size: 14px !important;
    width: 100% !important;
  }
  
  .mobile-investment-form :deep(.n-input--small .n-input__input-el),
  .mobile-investment-form :deep(.n-input-number--small .n-input__input-el) {
    height: 32px !important;
    line-height: 32px !important;
  }
  
  .mobile-investment-form :deep(.n-base-selection--small) {
    height: 32px !important;
  }
  
  .mobile-investment-form :deep(.n-input-number--small) {
    display: flex !important;
    flex-direction: row !important;
  }
  
  .mobile-investment-form :deep(.n-input-number--small .n-input) {
    flex: 1 !important;
    min-width: 0 !important;
  }
  
  .mobile-investment-form :deep(.n-input-number--small .n-input-number-button-group) {
    display: flex !important;
    flex-shrink: 0 !important;
    height: 32px !important;
  }
  
  .mobile-investment-form :deep(.n-input-number--small .n-input-number-button) {
    height: 16px !important;
  }
  
  /* 提交按钮样式 */
  .mobile-investment-form .submit-btn {
    height: 32px !important;
    padding: 0 16px !important;
    font-size: 14px !important;
    width: auto !important;
  }
}
</style>
