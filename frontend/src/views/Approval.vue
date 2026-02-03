<template>
  <div class="approval-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>📋 审批中心</h1>
      <p class="subtitle">所有资金变动都需要全体家庭成员同意后才能执行</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card pending">
        <div class="stat-icon">⏳</div>
        <div class="stat-info">
          <div class="stat-value">{{ approvalList?.pending_count || 0 }}</div>
          <div class="stat-label">待处理</div>
        </div>
      </div>
      <div class="stat-card approved">
        <div class="stat-icon">✅</div>
        <div class="stat-info">
          <div class="stat-value">{{ approvalList?.approved_count || 0 }}</div>
          <div class="stat-label">已通过</div>
        </div>
      </div>
      <div class="stat-card rejected">
        <div class="stat-icon">❌</div>
        <div class="stat-info">
          <div class="stat-value">{{ approvalList?.rejected_count || 0 }}</div>
          <div class="stat-label">已拒绝</div>
        </div>
      </div>
      <div class="stat-card total">
        <div class="stat-icon">📊</div>
        <div class="stat-info">
          <div class="stat-value">{{ approvalList?.total || 0 }}</div>
          <div class="stat-label">全部申请</div>
        </div>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="action-bar">
      <div class="filters">
        <select v-model="filterType" @change="loadApprovals" class="filter-select">
          <option value="">全部类型</option>
          <option value="deposit">资金注入</option>
          <option value="expense">大额支出</option>
          <option value="investment_create">创建理财</option>
          <option value="investment_update">更新理财</option>
          <option value="investment_income">理财收益</option>
          <option value="member_join">成员加入</option>
          <option value="member_remove">成员剔除</option>
        </select>
        <select v-model="filterStatus" @change="loadApprovals" class="filter-select">
          <option value="">全部状态</option>
          <option value="pending">待处理</option>
          <option value="approved">已通过</option>
          <option value="rejected">已拒绝</option>
          <option value="cancelled">已取消</option>
        </select>
      </div>
      <div class="actions">
        <button @click="showCreateModal = true" class="btn-primary">
          ➕ 发起申请
        </button>
      </div>
    </div>

    <!-- 待我审批的申请（醒目提示） -->
    <div v-if="pendingApprovals.length > 0" class="pending-section">
      <h2>🔔 待我审批 ({{ pendingApprovals.length }})</h2>
      <div class="approval-cards">
        <div v-for="item in pendingApprovals" :key="item.id" class="approval-card pending-card">
          <div class="card-header">
            <span class="type-badge" :class="getTypeClass(item.request_type)">
              {{ getTypeLabel(item.request_type) }}
            </span>
            <span class="status-badge pending">待审批</span>
          </div>
          <div class="card-body">
            <h3>{{ item.title }}</h3>
            <p class="description">{{ item.description }}</p>
            <div class="meta">
              <span v-if="!isMemberRequest(item.request_type)">💰 ¥{{ formatAmount(item.amount) }}</span>
              <span>👤 {{ item.requester_nickname }}</span>
              <span>📅 {{ formatDate(item.created_at) }}</span>
            </div>
            <div class="progress-bar">
              <div class="progress" :style="{ width: getProgressWidth(item) }"></div>
              <span class="progress-text">{{ getProgressText(item) }}</span>
            </div>
          </div>
          <div class="card-actions">
            <button 
              @click="handleApprove(item.id, true)" 
              class="btn-approve"
              :disabled="processingApprovalId === item.id"
            >
              {{ processingApprovalId === item.id ? '⏳ 处理中...' : '✅ 同意' }}
            </button>
            <button 
              @click="handleApprove(item.id, false)" 
              class="btn-reject"
              :disabled="processingApprovalId === item.id"
            >
              {{ processingApprovalId === item.id ? '⏳ 处理中...' : '❌ 拒绝' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 所有申请列表 -->
    <div class="all-approvals">
      <h2>📋 所有申请</h2>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="approvalList?.items?.length === 0" class="empty">
        <p>暂无申请记录</p>
      </div>
      <div v-else class="approval-cards">
        <div v-for="item in approvalList?.items" :key="item.id" class="approval-card">
          <div class="card-header">
            <span class="type-badge" :class="getTypeClass(item.request_type)">
              {{ getTypeLabel(item.request_type) }}
            </span>
            <span class="status-badge" :class="item.status">
              {{ getStatusLabel(item.status) }}
            </span>
          </div>
          <div class="card-body">
            <h3>{{ item.title }}</h3>
            <p class="description">{{ item.description }}</p>
            <div class="meta">
              <span v-if="!isMemberRequest(item.request_type)">💰 ¥{{ formatAmount(item.amount) }}</span>
              <span>👤 {{ item.requester_nickname }}</span>
              <span>📅 {{ formatDate(item.created_at) }}</span>
            </div>
            <!-- 审批进度 -->
            <div v-if="item.status === 'pending'" class="progress-bar">
              <div class="progress" :style="{ width: getProgressWidth(item) }"></div>
              <span class="progress-text">{{ getProgressText(item) }}</span>
            </div>
            <!-- 审批记录 -->
            <div v-if="item.approvals?.length > 0" class="approval-records">
              <div v-for="record in item.approvals" :key="record.id" class="record">
                <span :class="record.is_approved ? 'approved' : 'rejected'">
                  {{ record.is_approved ? '✅' : '❌' }}
                </span>
                <span class="approver">{{ record.approver_nickname }}</span>
                <span v-if="record.comment" class="comment">: {{ record.comment }}</span>
              </div>
            </div>
          </div>
          <div class="card-actions" v-if="item.status === 'pending' && item.requester_id === currentUserId">
            <button @click="handleCancel(item.id)" class="btn-cancel">
              🚫 取消申请
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 发起申请弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>发起新申请</h2>
          <button @click="showCreateModal = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <!-- 申请类型选择 -->
          <div class="form-group">
            <label>申请类型</label>
            <div class="type-selector">
              <button 
                v-for="type in requestTypes" 
                :key="type.value"
                :class="{ active: createForm.type === type.value }"
                @click="createForm.type = type.value"
                class="type-btn"
              >
                {{ type.icon }} {{ type.label }}
              </button>
            </div>
          </div>

          <!-- 资金注入表单 -->
          <template v-if="createForm.type === 'deposit'">
            <div class="form-group">
              <label>注入金额 (元)</label>
              <input v-model.number="createForm.amount" type="number" min="0" step="0.01" placeholder="请输入金额">
            </div>
            <div class="form-group">
              <label>注入日期</label>
              <input v-model="createForm.deposit_date" type="date">
            </div>
            <div class="form-group">
              <label>备注 (可选)</label>
              <textarea v-model="createForm.note" placeholder="备注说明"></textarea>
            </div>
          </template>

          <!-- 创建理财产品表单 -->
          <template v-if="createForm.type === 'investment_create'">
            <div class="form-group">
              <label>产品名称</label>
              <input v-model="createForm.name" type="text" placeholder="请输入理财产品名称">
            </div>
            <div class="form-group">
              <label>产品类型</label>
              <select v-model="createForm.investment_type">
                <option value="deposit">银行存款</option>
                <option value="fund">基金</option>
                <option value="stock">股票</option>
                <option value="bond">债券</option>
                <option value="other">其他</option>
              </select>
            </div>
            <div class="form-group">
              <label>本金 (元)</label>
              <input v-model.number="createForm.principal" type="number" min="0" step="0.01" placeholder="请输入本金">
            </div>
            <div class="form-group">
              <label>预期年化收益率 (%)</label>
              <input v-model.number="createForm.expected_rate" type="number" min="0" max="100" step="0.01" placeholder="如: 3.5">
            </div>
            <div class="form-group">
              <label>开始日期</label>
              <input v-model="createForm.start_date" type="date">
            </div>
            <div class="form-group">
              <label>到期日期 (可选)</label>
              <input v-model="createForm.end_date" type="date">
            </div>
            <div class="form-group">
              <label>备注 (可选)</label>
              <textarea v-model="createForm.note" placeholder="备注说明"></textarea>
            </div>
          </template>

          <!-- 理财收益登记表单 -->
          <template v-if="createForm.type === 'investment_income'">
            <div class="form-group">
              <label>理财产品</label>
              <select v-model="createForm.investment_id">
                <option v-for="inv in investments" :key="inv.id" :value="inv.id">
                  {{ inv.name }} (本金: ¥{{ formatAmount(inv.principal) }})
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>收益金额 (元)</label>
              <input v-model.number="createForm.amount" type="number" step="0.01" placeholder="请输入收益金额">
            </div>
            <div class="form-group">
              <label>收益日期</label>
              <input v-model="createForm.income_date" type="date">
            </div>
            <div class="form-group">
              <label>备注 (可选)</label>
              <textarea v-model="createForm.note" placeholder="备注说明"></textarea>
            </div>
          </template>

          <!-- 大额支出表单 -->
          <template v-if="createForm.type === 'expense'">
            <div class="form-group">
              <label>支出标题</label>
              <input v-model="createForm.expense_title" type="text" placeholder="请输入支出标题，如：购买设备">
            </div>
            <div class="form-group">
              <label>支出金额 (元)</label>
              <input v-model.number="createForm.amount" type="number" min="0" step="0.01" placeholder="请输入支出金额">
            </div>
            <div class="form-group">
              <label>支出原因</label>
              <textarea v-model="createForm.expense_reason" placeholder="请详细说明支出原因"></textarea>
            </div>
            <div class="form-group">
              <label>各成员扣减比例 (%)</label>
              <div class="ratio-list">
                <div v-for="(item, index) in createForm.deduction_ratios" :key="item.user_id" class="ratio-item">
                  <span class="member-name">{{ getMemberNickname(item.user_id) }}</span>
                  <input 
                    :value="item.ratio"
                    @input="handleRatioChange(index, $event)"
                    type="number" 
                    min="0" 
                    max="100" 
                    step="1"
                    class="ratio-input"
                    :disabled="isSingleMember"
                  >
                  <span class="ratio-unit">%</span>
                </div>
              </div>
              <div class="ratio-summary" :class="{ valid: expenseTotalRatio === 100 }">
                合计: {{ expenseTotalRatio }}% ✓
              </div>
            </div>
          </template>
        </div>
        <div class="modal-footer">
          <button @click="showCreateModal = false" class="btn-secondary">取消</button>
          <button @click="submitCreate" class="btn-primary" :disabled="submitting">
            {{ submitting ? '提交中...' : '提交申请' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { approvalApi, investmentApi, familyApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { checkAndShowAchievements } from '@/utils/achievement'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)

const loading = ref(false)
const submitting = ref(false)
const showCreateModal = ref(false)
const filterType = ref('')
const filterStatus = ref('')
const processingApprovalId = ref<number | null>(null)  // 防重复点击：当前正在处理的审批ID

interface ApprovalRecord {
  id: number
  request_id: number
  approver_id: number
  approver_nickname: string
  is_approved: boolean
  comment?: string
  created_at: string
}

interface ApprovalItem {
  id: number
  family_id: number
  requester_id: number
  requester_nickname: string
  request_type: string
  title: string
  description: string
  amount: number
  request_data: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string
  executed_at?: string
  approvals: ApprovalRecord[]
  pending_approvers: number[]
  total_members: number
  approved_count: number
  rejected_count: number
}

interface ApprovalListResponse {
  total: number
  pending_count: number
  approved_count: number
  rejected_count: number
  items: ApprovalItem[]
}

interface Investment {
  id: number
  name: string
  principal: number
}

const approvalList = ref<ApprovalListResponse | null>(null)
const pendingApprovals = ref<ApprovalItem[]>([])
const investments = ref<Investment[]>([])

const requestTypes = [
  { value: 'deposit', label: '资金注入', icon: '💰' },
  { value: 'expense', label: '大额支出', icon: '💸' },
  { value: 'investment_create', label: '创建理财', icon: '📈' },
  { value: 'investment_income', label: '理财收益', icon: '💵' }
]

interface FamilyMember {
  user_id: number
  nickname: string
}

const familyMembers = ref<FamilyMember[]>([])

const createForm = ref({
  type: 'deposit',
  amount: 0,
  deposit_date: new Date().toISOString().split('T')[0],
  note: '',
  name: '',
  investment_type: 'fund',
  principal: 0,
  expected_rate: 0,
  start_date: new Date().toISOString().split('T')[0],
  end_date: '',
  investment_id: 0,
  income_date: new Date().toISOString().split('T')[0],
  // 支出申请字段
  expense_title: '',
  expense_reason: '',
  deduction_ratios: [] as Array<{ user_id: number; ratio: number }>
})

// 计算支出扣减比例总和
const expenseTotalRatio = computed(() => {
  return createForm.value.deduction_ratios.reduce((sum, r) => sum + r.ratio, 0)
})

// 判断是否只有单个成员
const isSingleMember = computed(() => {
  return createForm.value.deduction_ratios.length <= 1
})

// 处理比例变化 - 联动调整其他成员的比例
const handleRatioChange = (changedIndex: number, event: Event) => {
  const input = event.target as HTMLInputElement
  let newValue = parseInt(input.value) || 0
  
  // 限制范围 0-100
  newValue = Math.max(0, Math.min(100, newValue))
  
  const ratios = createForm.value.deduction_ratios
  const memberCount = ratios.length
  
  // 单成员时固定100%
  if (memberCount <= 1) {
    ratios[0].ratio = 100
    return
  }
  
  // 计算当前成员之外的其他成员总比例
  const otherIndices = ratios.map((_, i) => i).filter(i => i !== changedIndex)
  const oldOtherTotal = otherIndices.reduce((sum, i) => sum + ratios[i].ratio, 0)
  
  // 计算剩余需要分配给其他成员的比例
  const remainingForOthers = 100 - newValue
  
  // 设置当前成员的新值
  ratios[changedIndex].ratio = newValue
  
  if (remainingForOthers <= 0) {
    // 如果当前成员占了100%或更多，其他成员都设为0
    otherIndices.forEach(i => {
      ratios[i].ratio = 0
    })
  } else if (oldOtherTotal === 0) {
    // 如果其他成员原来总和为0，平均分配剩余比例
    const avgRatio = Math.floor(remainingForOthers / otherIndices.length)
    const remainder = remainingForOthers - avgRatio * otherIndices.length
    otherIndices.forEach((idx, i) => {
      ratios[idx].ratio = avgRatio + (i === 0 ? remainder : 0)
    })
  } else {
    // 按比例调整其他成员
    let distributed = 0
    otherIndices.forEach((idx, i) => {
      if (i === otherIndices.length - 1) {
        // 最后一个成员获得剩余的所有比例（避免四舍五入误差）
        ratios[idx].ratio = remainingForOthers - distributed
      } else {
        const proportion = ratios[idx].ratio / oldOtherTotal
        const newRatio = Math.round(remainingForOthers * proportion)
        ratios[idx].ratio = Math.max(0, Math.min(100, newRatio))
        distributed += ratios[idx].ratio
      }
    })
  }
  
  // 确保每个比例都在有效范围内
  ratios.forEach(r => {
    r.ratio = Math.max(0, Math.min(100, r.ratio))
  })
}

// 初始化支出扣减比例（平均分配）
const initDeductionRatios = () => {
  if (familyMembers.value.length > 0) {
    const avgRatio = Math.floor(100 / familyMembers.value.length)
    const remainder = 100 - avgRatio * familyMembers.value.length
    createForm.value.deduction_ratios = familyMembers.value.map((m, index) => ({
      user_id: m.user_id,
      ratio: avgRatio + (index === 0 ? remainder : 0)
    }))
  }
}

// 获取成员昵称
const getMemberNickname = (userId: number): string => {
  const member = familyMembers.value.find(m => m.user_id === userId)
  return member?.nickname || `用户${userId}`
}

const loadApprovals = async () => {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (filterType.value) params.request_type = filterType.value
    if (filterStatus.value) params.status = filterStatus.value
    
    const response = await approvalApi.list(params)
    approvalList.value = response.data
  } catch (error) {
    console.error('加载申请列表失败:', error)
  } finally {
    loading.value = false
  }
}

const loadPendingApprovals = async () => {
  try {
    const response = await approvalApi.getPending()
    pendingApprovals.value = response.data
  } catch (error) {
    console.error('加载待审批列表失败:', error)
  }
}

const loadInvestments = async () => {
  try {
    const response = await investmentApi.list()
    investments.value = response.data
  } catch (error) {
    console.error('加载理财产品列表失败:', error)
  }
}

const loadFamilyMembers = async () => {
  try {
    const response = await familyApi.getMy()
    // /family/my 返回的数据中包含 members 数组
    familyMembers.value = response.data.members || []
    // 初始化支出扣减比例
    initDeductionRatios()
  } catch (error) {
    console.error('加载家庭成员失败:', error)
  }
}

const handleApprove = async (id: number, isApproved: boolean) => {
  // 防重复点击：如果正在处理则返回
  if (processingApprovalId.value !== null) {
    return
  }
  
  // 设置当前处理中的审批ID
  processingApprovalId.value = id
  
  try {
    if (isApproved) {
      await approvalApi.approve(id)
    } else {
      const reason = prompt('请输入拒绝原因（可选）:') || ''
      await approvalApi.reject(id, reason)
    }
    alert(isApproved ? '已同意该申请' : '已拒绝该申请')
    loadApprovals()
    loadPendingApprovals()
    
    // 审批通过后检查成就
    if (isApproved) {
      setTimeout(() => checkAndShowAchievements(), 500)
    }
  } catch (error: unknown) {
    const errMsg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '审批失败'
    alert(errMsg)
  } finally {
    // 无论成功失败都要重置状态
    processingApprovalId.value = null
  }
}

const handleCancel = async (id: number) => {
  if (!confirm('确定要取消这个申请吗？')) return
  
  try {
    await approvalApi.cancel(id)
    alert('申请已取消')
    loadApprovals()
  } catch (error: unknown) {
    const errMsg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '取消失败'
    alert(errMsg)
  }
}

const submitCreate = async () => {
  submitting.value = true
  try {
    if (createForm.value.type === 'deposit') {
      await approvalApi.createDeposit({
        amount: createForm.value.amount,
        deposit_date: createForm.value.deposit_date,
        note: createForm.value.note || undefined
      })
    } else if (createForm.value.type === 'investment_create') {
      await approvalApi.createInvestment({
        name: createForm.value.name,
        investment_type: createForm.value.investment_type,
        principal: createForm.value.principal,
        expected_rate: createForm.value.expected_rate / 100,
        start_date: createForm.value.start_date,
        end_date: createForm.value.end_date || undefined,
        note: createForm.value.note || undefined
      })
    } else if (createForm.value.type === 'investment_income') {
      await approvalApi.createInvestmentIncome({
        investment_id: createForm.value.investment_id,
        amount: createForm.value.amount,
        income_date: createForm.value.income_date,
        note: createForm.value.note || undefined
      })
    } else if (createForm.value.type === 'expense') {
      // 验证扣减比例
      if (expenseTotalRatio.value !== 100) {
        alert('扣减比例合计必须等于100%')
        return
      }
      if (!createForm.value.expense_title.trim()) {
        alert('请输入支出标题')
        return
      }
      if (createForm.value.amount <= 0) {
        alert('请输入有效的支出金额')
        return
      }
      if (!createForm.value.expense_reason.trim()) {
        alert('请输入支出原因')
        return
      }
      
      // 转换 deduction_ratios 为数组格式 [{ user_id, ratio }]，比例转换为 0-1
      const deductionRatios = createForm.value.deduction_ratios.map(r => ({
        user_id: r.user_id,
        ratio: r.ratio / 100  // 百分比转换为 0-1 小数
      }))
      
      await approvalApi.createExpense({
        title: createForm.value.expense_title,
        amount: createForm.value.amount,
        reason: createForm.value.expense_reason,
        deduction_ratios: deductionRatios
      })
    }
    
    alert('申请已提交，等待家庭成员审批')
    showCreateModal.value = false
    resetForm()
    loadApprovals()
    loadPendingApprovals()
  } catch (error: unknown) {
    const errMsg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '提交失败'
    alert(errMsg)
  } finally {
    submitting.value = false
  }
}

const resetForm = () => {
  createForm.value = {
    type: 'deposit',
    amount: 0,
    deposit_date: new Date().toISOString().split('T')[0],
    note: '',
    name: '',
    investment_type: 'fund',
    principal: 0,
    expected_rate: 0,
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    investment_id: 0,
    income_date: new Date().toISOString().split('T')[0],
    expense_title: '',
    expense_reason: '',
    deduction_ratios: []
  }
  // 重新初始化支出扣减比例
  initDeductionRatios()
}

const formatAmount = (amount: number) => {
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    deposit: '资金注入',
    investment_create: '创建理财',
    investment_update: '更新理财',
    investment_income: '理财收益',
    expense: '大额支出',
    member_join: '成员加入',
    member_remove: '成员剔除'
  }
  return labels[type] || type
}

const getTypeClass = (type: string) => {
  const classes: Record<string, string> = {
    deposit: 'type-deposit',
    investment_create: 'type-investment',
    investment_update: 'type-investment',
    investment_income: 'type-income',
    expense: 'type-expense',
    member_join: 'type-member-join',
    member_remove: 'type-member-remove'
  }
  return classes[type] || ''
}

// 判断是否是成员相关的申请类型（不显示金额）
const isMemberRequest = (type: string) => {
  return ['member_join', 'member_remove'].includes(type)
}

// 获取审批进度的描述文本
const getProgressText = (item: ApprovalItem) => {
  if (item.request_type === 'member_join') {
    // 成员加入：任一成员同意即可
    return item.approved_count > 0 ? '已有成员同意' : '等待任一成员同意'
  } else if (item.request_type === 'member_remove') {
    // 成员剔除：需要管理员同意
    return item.approved_count > 0 ? '管理员已同意' : '等待管理员同意'
  } else {
    // 资金相关：全体成员同意
    return `${item.approved_count} / ${Math.max(item.total_members - 1, 1)} 已同意`
  }
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: '待审批',
    approved: '已通过',
    rejected: '已拒绝',
    cancelled: '已取消'
  }
  return labels[status] || status
}

const getProgressWidth = (item: ApprovalItem) => {
  const required = Math.max(item.total_members - 1, 1)
  return `${(item.approved_count / required) * 100}%`
}

onMounted(() => {
  loadApprovals()
  loadPendingApprovals()
  loadInvestments()
  loadFamilyMembers()
})
</script>

<style scoped>
.approval-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  margin: 0 0 8px 0;
}

.subtitle {
  color: #666;
  margin: 0;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.stat-icon {
  font-size: 32px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.stat-card.pending { border-left: 4px solid #f59e0b; }
.stat-card.approved { border-left: 4px solid #10b981; }
.stat-card.rejected { border-left: 4px solid #ef4444; }
.stat-card.total { border-left: 4px solid #3b82f6; }

/* 操作栏 */
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.filters {
  display: flex;
  gap: 12px;
}

.filter-select {
  padding: 10px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}

.btn-primary {
  padding: 12px 24px;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 待审批区域 */
.pending-section {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  padding: 24px;
  border-radius: 16px;
  margin-bottom: 32px;
}

.pending-section h2 {
  margin: 0 0 16px 0;
  font-size: 20px;
}

/* 申请卡片 */
.approval-cards {
  display: grid;
  gap: 16px;
}

.approval-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.pending-card {
  border: 2px solid #f59e0b;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.type-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.type-deposit { background: #dbeafe; color: #1d4ed8; }
.type-investment { background: #dcfce7; color: #16a34a; }
.type-income { background: #fef3c7; color: #d97706; }
.type-expense { background: #fee2e2; color: #dc2626; }
.type-member-join { background: #e0e7ff; color: #4f46e5; }
.type-member-remove { background: #fce7f3; color: #db2777; }

.status-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.pending { background: #fef3c7; color: #d97706; }
.status-badge.approved { background: #dcfce7; color: #16a34a; }
.status-badge.rejected { background: #fee2e2; color: #dc2626; }
.status-badge.cancelled { background: #f3f4f6; color: #6b7280; }

.card-body h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
}

.description {
  color: #666;
  margin: 0 0 12px 0;
  font-size: 14px;
}

.meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #888;
  margin-bottom: 12px;
}

.progress-bar {
  position: relative;
  height: 24px;
  background: #f3f4f6;
  border-radius: 12px;
  overflow: hidden;
  margin-top: 12px;
}

.progress {
  height: 100%;
  background: linear-gradient(135deg, #10b981, #34d399);
  transition: width 0.3s ease;
}

.progress-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.approval-records {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e5e7eb;
}

.record {
  font-size: 13px;
  margin-bottom: 4px;
}

.record .approved { color: #16a34a; }
.record .rejected { color: #dc2626; }
.record .approver { font-weight: 600; margin-left: 4px; }
.record .comment { color: #666; }

.card-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
}

.btn-approve {
  flex: 1;
  padding: 12px;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-approve:hover:not(:disabled) { background: #059669; }

.btn-approve:disabled,
.btn-reject:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-reject {
  flex: 1;
  padding: 12px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-reject:hover { background: #dc2626; }

.btn-cancel {
  padding: 10px 20px;
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-cancel:hover { background: #e5e7eb; }

/* 区块标题 */
.all-approvals h2 {
  margin: 0 0 16px 0;
  font-size: 20px;
}

.loading, .empty {
  text-align: center;
  padding: 48px;
  color: #888;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 16px;
  width: 90%;
  max-width: 520px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #f3f4f6;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: #f3f4f6;
  border-radius: 50%;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  font-size: 14px;
  color: #374151;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group textarea {
  min-height: 80px;
  resize: vertical;
}

.type-selector {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.type-btn {
  padding: 10px 16px;
  border: 2px solid #e5e7eb;
  background: white;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.type-btn.active {
  border-color: #f59e0b;
  background: #fef3c7;
  color: #d97706;
}

.type-btn:hover {
  border-color: #f59e0b;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid #f3f4f6;
}

.btn-secondary {
  padding: 12px 24px;
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-secondary:hover { background: #e5e7eb; }

/* 支出比例列表 */
.ratio-list {
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px;
}

.ratio-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #e5e7eb;
}

.ratio-item:last-child {
  border-bottom: none;
}

.member-name {
  flex: 1;
  font-weight: 500;
  color: #374151;
}

.ratio-input {
  width: 80px !important;
  padding: 8px 12px !important;
  text-align: center;
}

.ratio-unit {
  color: #666;
  font-size: 14px;
}

.ratio-summary {
  margin-top: 12px;
  padding: 10px;
  background: #dcfce7;
  border-radius: 8px;
  text-align: center;
  font-weight: 600;
  color: #16a34a;
}

.ratio-summary.error {
  background: #fee2e2;
  color: #dc2626;
}

/* 响应式 */
@media (max-width: 640px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .action-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filters {
    flex-direction: column;
  }
  
  .meta {
    flex-wrap: wrap;
  }
}
</style>
